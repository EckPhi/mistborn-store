#!/bin/sh
set -eu
# Root is used only to repair bind-directory/socket permissions before su.
[ -S /var/run/docker.sock ] || { echo 'Host Docker socket is missing or is not a Unix socket.' >&2; exit 1; }
gid=$(stat -c '%g' /var/run/docker.sock)
group=$(awk -F: -v gid="$gid" '$3 == gid {print $1; exit}' /etc/group)
if [ -z "$group" ]; then
  group=coder-docker-$gid
  addgroup -g "$gid" "$group"
fi
if ! id -G coder | tr ' ' '\n' | grep -qx "$gid"; then
  addgroup coder "$group"
fi
mkdir -p /home/coder /runtime/bin
chown 1000:1000 /home/coder
cp /opt/coder /runtime/bin/coder
chmod 755 /runtime/bin/coder
export CODER_ACCESS_URL="${CODER_DEV_ACCESS_URL_OVERRIDE:-$CODER_ACCESS_URL}"
case "$CODER_ACCESS_URL" in
  http://localhost*|https://localhost*|http://127.*|https://127.*|http://\[::1\]*|https://\[::1\]*)
    echo 'Coder access URL must be reachable from workspace agents. Set the URL override in RunTipi.' >&2; exit 1 ;;
  http://?*|https://?*) ;;
  *) echo 'Coder requires an HTTP(S) access URL.' >&2; exit 1 ;;
esac
# The host may publish its RunTipi domain on a Tailscale address that Docker
# bridge containers cannot reach. Resolve only coderd's own HTTPS self-checks
# through the Traefik service on the shared Docker network. Workspace agents
# keep resolving the public URL normally from their separate containers.
if [ -z "${CODER_DEV_ACCESS_URL_OVERRIDE:-}" ]; then
  case "$CODER_ACCESS_URL" in
    https://*)
      public_host=${CODER_ACCESS_URL#https://}
      public_host=${public_host%%/*}
      case "$public_host" in
        *:*) ;;
        *)
          proxy_ip=$(getent ahostsv4 runtipi-reverse-proxy | awk 'NR == 1 {print $1}')
          if [ -n "$proxy_ip" ] && curl -fsS --resolve "$public_host:443:$proxy_ip" \
            --connect-timeout 3 --max-time 5 "${CODER_ACCESS_URL%/}/healthz" >/dev/null 2>&1; then
            printf '%s %s\n' "$proxy_ip" "$public_host" >> /etc/hosts
          fi
          ;;
      esac
      ;;
  esac
fi
unset CODER_DEV_ACCESS_URL_OVERRIDE
exec su -p -s /bin/bash coder -c 'exec /opt/coder server'
