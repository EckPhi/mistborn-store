#!/bin/bash
# Run on an amd64 Docker host, after the local image build. Synthetic data only.
set -euo pipefail
state=$(mktemp -d)
name="se-smoke-$$"
cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; rm -rf "$state"; }
trap cleanup EXIT
start() {
 docker run -d --name "$name" --platform linux/amd64 --shm-size=1g \
  -e CUSTOM_USER=smoke -e PASSWORD=synthetic-test-password -e PUID="$(id -u)" -e PGID="$(id -g)" \
  -v "$state/config:/config" -v "$state/projects:/projects" \
  -p 127.0.0.1::3001 solid-edge-webtop:0.1.0 >/dev/null
}
start
port=$(docker port "$name" 3001/tcp | cut -d: -f2)
ready=false
for n in $(seq 1 90); do
 if curl -ksf -u smoke:synthetic-test-password "https://127.0.0.1:$port/" > "$state/page"; then ready=true; break; fi
 sleep 2
done
[ "$ready" = true ]
[ "$(curl -ks -o /dev/null -w '%{http_code}' "https://127.0.0.1:$port/")" = 401 ]
docker exec "$name" wine --version
docker exec -u abc -e DISPLAY=:1 "$name" wineboot -u
docker exec -u abc "$name" sh -c 'printf synthetic > /projects/persistence-marker; printf synthetic > /config/wine/solid-edge/persistence-marker'
docker rm -f "$name" >/dev/null
start
docker exec "$name" test -f /projects/persistence-marker
docker exec "$name" test -f /config/wine/solid-edge/persistence-marker
echo 'HTTP auth, Wine initialization, and persistent mounts passed. Manually verify desktop stream and Wine GUI.'
