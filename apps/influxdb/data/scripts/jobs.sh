#!/usr/bin/env bash
# InfluxDB 2.x maintenance sidecar (runtipi app: influxdb).
#
# Jobs, driven by environment variables set from the runtipi form:
#   1. Multi-stage downsampling: provisions one bucket + one Flux task per
#      stage from RETENTION_STAGES. The tasks run inside InfluxDB's own task
#      engine; this sidecar only creates them (idempotently) and keeps the
#      bucket retention periods in sync.
#   2. Backups: periodic `influx backup`, compressed and rotated in /backups.
#
# RETENTION_STAGES syntax: "<age>:<resolution>;...;<age>:drop"
#   e.g. "30d:1h;2y:1d;10y:drop"
#   Units for <age>: h (hours), d (days), w (weeks), M (months), y (years).
#   <resolution> is a Flux duration, e.g. 15m, 1h, 1d.
#
# Resulting layout for base bucket "default" and the example above:
#   default      retention 30d   (raw data)
#   default_1h   retention 2y    (mean per 1h, task ds_default_to_default_1h)
#   default_1d   retention 10y   (mean per 1d, task ds_default_1h_to_default_1d)
#
# The influx CLI picks up INFLUX_HOST / INFLUX_TOKEN / INFLUX_ORG from the
# environment.

set -u

BUCKET="${INFLUX_BUCKET:-}"
STAGES="${RETENTION_STAGES:-}"
BACKUP_HOURS="${BACKUP_INTERVAL_HOURS:-24}"
BACKUP_KEEP="${BACKUP_KEEP:-7}"
BACKUP_DIR="/backups"

log() { echo "[influxdb-jobs] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }

# "30d" -> hours. Months ~ 30 days, years ~ 365 days.
age_hours() {
  local num unit
  num="${1//[a-zA-Z]/}"
  unit="${1//[0-9]/}"
  case "$unit" in
  h) echo "$num" ;;
  d) echo $((num * 24)) ;;
  w) echo $((num * 168)) ;;
  M) echo $((num * 720)) ;;
  y) echo $((num * 8760)) ;;
  *) echo "" ;;
  esac
}

bucket_id() {
  influx bucket list -n "$1" --hide-headers 2>/dev/null | awk '{print $1}' | head -n1
}

# ensure_bucket <name> <retention, e.g. 720h or 0>
ensure_bucket() {
  local id
  id=$(bucket_id "$1")
  if [ -z "$id" ]; then
    influx bucket create -n "$1" -r "$2" >/dev/null && log "created bucket $1 (retention $2)"
  else
    influx bucket update -i "$id" -r "$2" >/dev/null || log "could not update retention of bucket $1"
  fi
}

# ensure_task <name> <src> <dst> <resolution>
ensure_task() {
  local name="$1" src="$2" dst="$3" res="$4" num lookback flux
  if influx task list --hide-headers 2>/dev/null | grep -qF "$name"; then
    return 0
  fi
  # Look back two windows so late-arriving data is (re)aggregated; to() writes
  # by timestamp, so overlapping runs are idempotent.
  num="${res//[a-zA-Z]/}"
  lookback="$((num * 2))${res//[0-9]/}"
  flux=$(
    cat <<EOF
option task = {name: "$name", every: $res}

from(bucket: "$src")
    |> range(start: -$lookback)
    |> aggregateWindow(every: $res, fn: mean, createEmpty: false)
    |> to(bucket: "$dst", org: "$INFLUX_ORG")
EOF
  )
  if influx task create --org "$INFLUX_ORG" "$flux" >/dev/null; then
    log "created task $name ($src -> $dst @ $res)"
  else
    log "could not create task $name"
  fi
}

ensure_pipeline() {
  [ -n "$STAGES" ] && [ -n "$BUCKET" ] || return 0

  local -a ages=() ress=()
  local st
  for st in ${STAGES//;/ }; do
    ages+=("${st%%:*}")
    ress+=("${st##*:}")
  done

  # Raw bucket keeps data until the first stage age.
  local h
  h=$(age_hours "${ages[0]}")
  [ -n "$h" ] && ensure_bucket "$BUCKET" "${h}h"

  local src="$BUCKET" i dst ret
  for i in "${!ress[@]}"; do
    [ "${ress[$i]}" = "drop" ] && continue
    dst="${BUCKET}_${ress[$i]}"
    # This stage's bucket keeps data until the next stage takes over,
    # or forever when it is the last stage.
    ret="0"
    if [ $((i + 1)) -lt ${#ages[@]} ]; then
      h=$(age_hours "${ages[$((i + 1))]}")
      [ -n "$h" ] && ret="${h}h"
    fi
    ensure_bucket "$dst" "$ret"
    ensure_task "ds_${src}_to_${dst}" "$src" "$dst" "${ress[$i]}"
    src="$dst"
  done
}

backup_job() {
  [ "$BACKUP_HOURS" -gt 0 ] 2>/dev/null || return 0
  local last now tmp out
  last=$(cat "$BACKUP_DIR/.last_backup" 2>/dev/null || echo 0)
  now=$(date +%s)
  [ $((now - last)) -ge $((BACKUP_HOURS * 3600)) ] || return 0

  tmp=$(mktemp -d)
  out="$BACKUP_DIR/influxdb_$(date -u +%Y%m%d_%H%M%S).tar.gz"
  if influx backup "$tmp" >/dev/null && tar -czf "$out" -C "$tmp" .; then
    log "backup written: $out"
    echo "$now" >"$BACKUP_DIR/.last_backup"
  else
    rm -f "$out"
    log "backup failed"
  fi
  rm -rf "$tmp"

  ls -1t "$BACKUP_DIR"/influxdb_*.tar.gz 2>/dev/null | tail -n +$((BACKUP_KEEP + 1)) | while read -r old; do
    rm -f "$old"
    log "pruned old backup $old"
  done
}

mkdir -p "$BACKUP_DIR"
log "starting; host=${INFLUX_HOST:-} org=${INFLUX_ORG:-} bucket=[$BUCKET] stages=[$STAGES] backup_every=${BACKUP_HOURS}h keep=$BACKUP_KEEP"

until influx ping >/dev/null 2>&1; do
  log "waiting for InfluxDB..."
  sleep 5
done
log "InfluxDB is up"

if [ -z "${INFLUX_TOKEN:-}" ]; then
  log "no admin token configured — retention pipeline and backups disabled. Set the 'Admin API token' app setting."
  # Keep the container alive so the app does not appear crashed.
  while true; do sleep 3600; done
fi

while true; do
  now=$(date +%s)
  last_maint=$(cat "$BACKUP_DIR/.last_maint" 2>/dev/null || echo 0)
  if [ $((now - last_maint)) -ge 3600 ]; then
    ensure_pipeline
    echo "$now" >"$BACKUP_DIR/.last_maint"
  fi
  backup_job
  sleep 300
done
