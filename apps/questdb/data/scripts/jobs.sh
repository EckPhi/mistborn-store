#!/bin/sh
# QuestDB maintenance sidecar (runtipi app: questdb).
#
# Jobs, all driven by environment variables set from the runtipi form:
#   1. Multi-stage downsampling: one incremental materialized view
#      (SAMPLE BY) per stage, TTLs on the views and the base table
#      according to RETENTION_STAGES.
#   2. Archiving: when ARCHIVE_ENABLED=true, raw partitions older than the
#      first stage are detached and stored as compressed tarballs in
#      /archive instead of being deleted by a TTL.
#   3. Backups: periodic full CHECKPOINT backups, compressed and rotated
#      in /backups.
#
# RETENTION_STAGES syntax: "<age>:<resolution>;...;<age>:drop"
#   e.g. "30d:1h;2y:1d;10y:drop"
#   Units for <age>: h (hours), d (days), w (weeks), M (months), y (years).
#   <resolution> is a QuestDB SAMPLE BY unit, e.g. 15m, 1h, 1d.
#
# For every managed table <t> and stage resolution <r>, a materialized view
# "<t>_<r>" is created with avg/min/max aggregates of all numeric columns.
# The view's TTL is the age of the *next* stage, so each granularity is kept
# until the next one takes over. The raw table is kept until the first stage
# age (TTL, or detach+compress when archiving is enabled).

QDB_URL="${QUESTDB_URL:-http://questdb:9000}"
TABLES="${RETENTION_TABLES:-}"
STAGES="${RETENTION_STAGES:-}"
ARCHIVE="${ARCHIVE_ENABLED:-false}"
BACKUP_HOURS="${BACKUP_INTERVAL_HOURS:-24}"
BACKUP_KEEP="${BACKUP_KEEP:-7}"

DATA_DIR="/questdb-data"
ARCHIVE_DIR="/archive"
BACKUP_DIR="/backups"
STATE_DIR="/state"

log() { echo "[questdb-jobs] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }

# Execute a SQL statement via the REST API. Fails (returns 1) on SQL errors.
sql() {
  _resp=$(curl -sS -G "$QDB_URL/exec" --data-urlencode "query=$1" 2>&1)
  case "$_resp" in
  *'"error"'*)
    log "SQL error for [$1]: $_resp"
    return 1
    ;;
  esac
  return 0
}

# Run a query and print its result as CSV without the header row.
csv() {
  curl -sS -G "$QDB_URL/exp" --data-urlencode "query=$1" 2>/dev/null | tail -n +2
}

# "30d" -> "30" / "d"
age_num() { printf '%s' "$1" | sed 's/[a-zA-Z]*$//'; }
age_unit() { printf '%s' "$1" | sed 's/^[0-9]*//'; }

# TTL unit word for an age unit character.
unit_word() {
  case "$1" in
  h) echo "HOURS" ;;
  d) echo "DAYS" ;;
  w) echo "WEEKS" ;;
  M) echo "MONTHS" ;;
  y) echo "YEARS" ;;
  *) echo "" ;;
  esac
}

# i-th stage (1-based) from RETENTION_STAGES, empty when out of range.
stage() {
  printf '%s\n' "$STAGES" | tr ';' '\n' | sed -n "${1}p" | tr -d ' '
}

stage_count() {
  printf '%s\n' "$STAGES" | tr ';' '\n' | grep -c .
}

# Designated timestamp column of a table, empty if the table is missing.
ts_col() {
  csv "select designatedTimestamp from tables() where table_name = '$1'" | tr -d '"'
}

# Create/refresh materialized views + TTLs for one table.
ensure_table_stages() {
  t="$1"
  ts=$(ts_col "$t")
  if [ -z "$ts" ]; then
    log "skip '$t': table not found (or no designated timestamp yet)"
    return 0
  fi

  aggs=""
  pairs=$(csv "SHOW COLUMNS FROM '$t'" | awk -F',' '{gsub(/"/,"",$1); gsub(/"/,"",$2); print $1":"$2}')
  for pair in $pairs; do
    c=${pair%%:*}
    ty=$(printf '%s' "${pair##*:}" | tr '[:lower:]' '[:upper:]')
    [ "$c" = "$ts" ] && continue
    case "$ty" in
    BYTE | SHORT | INT | LONG | FLOAT | DOUBLE)
      aggs="$aggs, avg($c) ${c}_avg, min($c) ${c}_min, max($c) ${c}_max"
      ;;
    esac
  done
  aggs=${aggs#, }
  if [ -z "$aggs" ]; then
    log "skip '$t': no numeric columns to downsample"
    return 0
  fi

  n=$(stage_count)
  i=1
  while [ "$i" -le "$n" ]; do
    st=$(stage "$i")
    age=${st%%:*}
    res=${st##*:}
    if [ "$res" != "drop" ] && [ -n "$res" ]; then
      v="${t}_${res}"
      sql "CREATE MATERIALIZED VIEW IF NOT EXISTS '$v' AS (SELECT $ts, $aggs FROM '$t' SAMPLE BY $res)" ||
        log "could not create view $v"
      next=$(stage $((i + 1)))
      nage=${next%%:*}
      if [ -n "$nage" ]; then
        u=$(unit_word "$(age_unit "$nage")")
        if [ -n "$u" ]; then
          sql "ALTER MATERIALIZED VIEW '$v' SET TTL $(age_num "$nage") $u" ||
            log "could not set TTL on view $v"
        fi
      fi
    fi
    i=$((i + 1))
  done

  # Raw-data boundary: first stage age. With archiving enabled the detach
  # job handles removal; otherwise a plain TTL drops old raw partitions.
  first=$(stage 1)
  fage=${first%%:*}
  u=$(unit_word "$(age_unit "$fage")")
  if [ "$ARCHIVE" != "true" ] && [ -n "$u" ]; then
    sql "ALTER TABLE '$t' SET TTL $(age_num "$fage") $u" ||
      log "could not set TTL on table $t"
  fi
}

# Detach raw partitions older than the first stage and compress them.
archive_job() {
  [ "$ARCHIVE" = "true" ] || return 0
  first=$(stage 1)
  fage=${first%%:*}
  fnum=$(age_num "$fage")
  funit=$(age_unit "$fage")
  [ -n "$fnum" ] && [ -n "$funit" ] || return 0

  for t in $(printf '%s' "$TABLES" | tr ',' ' '); do
    ts=$(ts_col "$t")
    [ -n "$ts" ] || continue
    # Errors here are expected when there is nothing old enough to detach.
    sql "ALTER TABLE '$t' DETACH PARTITION WHERE $ts < dateadd('$funit', -$fnum, now())" >/dev/null 2>&1
  done

  for d in "$DATA_DIR"/db/*/*.detached; do
    [ -e "$d" ] || continue
    tdir=$(basename "$(dirname "$d")")
    p=$(basename "$d" .detached)
    out="$ARCHIVE_DIR/${tdir}__${p}_$(date -u +%Y%m%d%H%M%S).tar.gz"
    if tar -czf "$out" -C "$(dirname "$d")" "$(basename "$d")"; then
      rm -rf "$d"
      log "archived partition $tdir/$p -> $out"
    else
      rm -f "$out"
      log "failed to archive $d, leaving partition detached"
    fi
  done
}

backup_job() {
  [ "$BACKUP_HOURS" -gt 0 ] 2>/dev/null || return 0
  last=$(cat "$STATE_DIR/last_backup" 2>/dev/null || echo 0)
  now=$(date +%s)
  [ $((now - last)) -ge $((BACKUP_HOURS * 3600)) ] || return 0

  if ! sql "CHECKPOINT CREATE"; then
    # A stale checkpoint from a crashed run blocks new ones — release and retry.
    sql "CHECKPOINT RELEASE" >/dev/null 2>&1
    sql "CHECKPOINT CREATE" || {
      log "backup skipped: cannot create checkpoint"
      return 1
    }
  fi
  out="$BACKUP_DIR/questdb_$(date -u +%Y%m%d_%H%M%S).tar.gz"
  if tar -czf "$out" -C "$DATA_DIR" .; then
    log "backup written: $out"
    echo "$now" >"$STATE_DIR/last_backup"
  else
    rm -f "$out"
    log "backup failed"
  fi
  sql "CHECKPOINT RELEASE" || log "warning: could not release checkpoint"

  ls -1t "$BACKUP_DIR"/questdb_*.tar.gz 2>/dev/null | tail -n +$((BACKUP_KEEP + 1)) | while read -r old; do
    rm -f "$old"
    log "pruned old backup $old"
  done
}

mkdir -p "$ARCHIVE_DIR" "$BACKUP_DIR" "$STATE_DIR"

log "starting; url=$QDB_URL tables=[$TABLES] stages=[$STAGES] archive=$ARCHIVE backup_every=${BACKUP_HOURS}h keep=$BACKUP_KEEP"
until sql "select 1" >/dev/null 2>&1; do
  log "waiting for QuestDB..."
  sleep 5
done
log "QuestDB is up"

while true; do
  now=$(date +%s)
  last_maint=$(cat "$STATE_DIR/last_maint" 2>/dev/null || echo 0)
  if [ $((now - last_maint)) -ge 3600 ]; then
    if [ -n "$TABLES" ] && [ -n "$STAGES" ]; then
      for t in $(printf '%s' "$TABLES" | tr ',' ' '); do
        ensure_table_stages "$t"
      done
      archive_job
    fi
    echo "$now" >"$STATE_DIR/last_maint"
  fi
  backup_job
  sleep 300
done
