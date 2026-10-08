# RClone Manager validation

## Release and startup contract

The app uses `ghcr.io/zarestia-dev/rclone-manager:sha-6d43c77`, the image built from
stable release v0.3.3, commit `6d43c77af621b15bf16eeeebe0843ebf2369d953`.
GHCR verified the tag and Linux amd64/arm64 manifests. The image starts as root
with `/usr/local/bin/entrypoint.sh`, fixes data ownership and then drops to UID/GID
1000. The app retains that entrypoint after its first-start wrapper.

The released source and its rcman 0.2.3 dependency establish that
`RCLONE_MANAGER_DATA_DIR=/data` puts the single-file connection store at
`/data/connections.json`. The store is a flat object with `_active` identifying a
named backend. Bootstrap restores this selection before starting the engine.
The seeded connection uses `is_local: false`, host `rclone-host-bridge` and port
5572, with no password or config path. Existing connection files are preserved.

The bridge supplies host Basic Auth credentials from installation fields and
forwards root HTTP routes to `/run/rclone/rc.sock`. It has no published port or
membership in `tipi_main_network`. Only Manager receives Runtipi routing.

## Checks performed

- The Runtipi 4.10.1 Compose builder, pinned at
  `5734817389df55aafb9afd571e42e12ab7e647e0`, generated direct-port, domain and
  local-domain deployments, with only import paths adapted in a temporary harness.
  Docker Compose accepted all three. The generated bridge stayed on the private
  app network and had no published port.
- An isolated Linux arm64 Docker project ran the actual pinned Manager and Nginx
  images against rclone v1.75.1 serving an authenticated, group-restricted Unix
  socket in a test volume. No existing host service or app was changed.
- On fresh storage, Manager's API reported `Host rclone` as the active connection,
  reported the fixture's host config path and rclone version, and returned the
  host's `fixture` remote from its own remote cache. Its process list contained
  Manager, Xvfb and dbus, with no local rclone daemon.
- A 3 MiB browser-API upload passed through Manager and the bridge into the
  fixture filesystem. Source and destination SHA-256 checksums matched.
- A Manager restart preserved the selected host backend and remote list.
- Manager's API returned HTTP 401 without UI authentication. Deliberately wrong
  host credentials produced HTTP 401 through the bridge and failed its exact
  healthcheck. Correct host credentials containing a dollar sign, colon, pipe and
  quote succeeded.
- Runtime testing caught the Nginx image's `user  nginx;` spacing. The new bridge's
  worker-group replacement accepts this spacing; workers can access the socket.
- Repository tests cover first-start selection, omission of host secrets/config
  overrides, restrictive seed-file permissions, preservation of user changes,
  and network/privilege boundaries. The complete store suite passes.

The fixture substitutes a named socket volume for the production host bind and
publishes the test UI on loopback only. Actual Linux host FUSE mounts, OAuth
browser callbacks, scheduled operations and live Traefik routing were not
exercised. Host mount visibility still depends on the existing service's FUSE
permissions and mount namespace, as documented by the Rclone app.

## Source references

- [Release v0.3.3](https://github.com/Zarestia-Dev/rclone-manager/releases/tag/v0.3.3)
- [Connection storage registration](https://github.com/Zarestia-Dev/rclone-manager/blob/6d43c77af621b15bf16eeeebe0843ebf2369d953/src-tauri/src/core/settings/manager.rs)
- [Backend restoration](https://github.com/Zarestia-Dev/rclone-manager/blob/6d43c77af621b15bf16eeeebe0843ebf2369d953/src-tauri/src/rclone/backend/manager.rs)
- [Bootstrap order](https://github.com/Zarestia-Dev/rclone-manager/blob/6d43c77af621b15bf16eeeebe0843ebf2369d953/src-tauri/src/core/initialization/bootstrap.rs)
- [Upstream entrypoint](https://github.com/Zarestia-Dev/rclone-manager/blob/6d43c77af621b15bf16eeeebe0843ebf2369d953/entrypoint.sh)
- [Supported Runtipi generator](https://github.com/runtipi/runtipi/blob/5734817389df55aafb9afd571e42e12ab7e647e0/packages/backend/src/modules/docker/builders/compose.builder.ts)
