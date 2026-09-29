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
unset CODER_DEV_ACCESS_URL_OVERRIDE
exec su -p -s /bin/bash coder -c 'exec /opt/coder server'
