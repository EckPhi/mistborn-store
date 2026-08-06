# AGENTS.md

Guide for humans and AI agents adding/maintaining apps in this Runtipi app store.

## Reference docs

- Custom app store: https://runtipi.io/docs/guides/create-your-own-app-store
- `config.json` reference: https://runtipi.io/docs/reference/config-json
- Dynamic compose guide: https://runtipi.io/docs/guides/dynamic-compose-guide
- Creating apps: https://runtipi.io/docs/developers/creating-apps

The authoritative schemas are the Zod schemas in `@runtipi/common` (`appInfoSchema`, `dynamicComposeSchema`). The CI test in `__tests__/apps.test.ts` validates every app against them — that test is the source of truth, not the prose docs.

## Per-app file layout

Every app lives in `apps/<app-id>/`. `<app-id>` is kebab-case and **must equal** `config.json`'s `id` field.

```
apps/<app-id>/
  config.json            # required — app metadata
  docker-compose.json    # required — service definitions
  metadata/
    description.md        # required — long markdown description
    logo.jpg             # required — must be a .jpg
```

All four files are required; CI fails if any is missing.

## config.json

Required fields:

| Field | Notes |
|---|---|
| `name` | Display name |
| `id` | Must match the folder name |
| `available` | `true` to show in the store |
| `short_desc` | One-line summary |
| `author` | Upstream project / maintainer |
| `port` | Host port the web UI is exposed on. Pick a free, non-conflicting port |
| `categories` | Array, see enum below |
| `description` | Longer description |
| `tipi_version` | Integer. `1` for a new app; increment on every change |
| `version` | Upstream app version string (e.g. `v1.2.3`) |
| `source` | Source repo URL |
| `exposable` | `true` if it can be exposed on a domain |

Useful optional fields: `website`, `supported_architectures` (`["amd64","arm64"]`), `dynamic_config: true`, `form_fields`, `https`, `no_gui`, `url_suffix`, `force_expose`, `force_pull`, `generate_vapid_keys`, `deprecated`, `min_tipi_version`, `uid`/`gid` (metadata, currently unused), `created_at`, `updated_at`.

Notes:

- `created_at` / `updated_at` are epoch **milliseconds** and are validated `< Date.now()` — a future/today-midnight value fails CI. Reuse an existing past timestamp.
- `no_gui: true` for headless apps (no web UI) — hides the "Open" button. Pair with `exposable: false` if there is nothing to proxy (e.g. a WebSocket/API-only backend).
- `version` should mirror the pinned `image` tag (see Image pinning). `force_pull` is generally unnecessary once images are pinned.

**Valid `categories`** (any other value fails CI):

```
network, media, development, automation, social, utilities,
photography, security, featured, books, data, music, finance,
gaming, ai
```

(There is no `productivity` category — a common mistake.)

### form_fields

Each field: `type`, `label`, `env_variable`, `required` (all required) plus optional `hint`, `placeholder`, `default`, `regex`, `pattern_error`, `min`, `max`, `options`, `encoding`.

Field `type` is one of: `text, password, email, number, fqdn, ip, fqdnip, random, boolean`.

- `default` only allowed when `required: false`.
- `options` (for dropdowns): array of `{ "label": "<shown>", "value": "<env value>" }`.
- For `type: random`: `min` sets the generated string length (default 32); `encoding` is `"base64"` or `"hex"`. CI enforces `required: false` on every `random` field.
- The `env_variable` is what you reference as `${VAR}` in `docker-compose.json`. Prefix app-specific vars to avoid collisions with upstream image vars (e.g. form `EUFY_USERNAME` → compose `"USERNAME": "${EUFY_USERNAME}"`).

## docker-compose.json

Top-level shape:

```json
{
  "schemaVersion": 2,
  "$schema": "https://schemas.runtipi.io/v2/dynamic-compose.json",
  "services": [ ... ],
  "overrides": [ ... ]   // optional, per-architecture
}
```

`schemaVersion` and `$schema` are stripped by the validator but included for parity with the official store and for editor schema support — add them.

Each service object supports (subset most used):

- `name` (required) — service name
- `image` (required) — **always pin an explicit immutable tag, never `latest`** (and never a floating major like `:2`). See Image pinning below
- `internalPort` — port the container listens on
- `isMain` — mark the primary web UI service
- `environment` — **array** of `{ "key": "...", "value": "..." }` objects. ⚠️ CI validates against the vendored `apps/dynamic-compose-schema.json`, which requires the array form — the `@runtipi/common` Zod schema uses an object record (`z.record(...)`) but is **not** what CI checks. All apps in this repo use the array form; match them.
- `addPorts` — array of `{ containerPort, hostPort, udp?, tcp?, interface? }`. **Only for _extra_ ports.** Do **not** republish the main `internalPort` here — see Reverse proxy below
- `volumes` — array of `{ hostPath, containerPath, readOnly?, shared?, private? }`. Write `hostPath` with the **`${APP_DATA_DIR}/...`** variable (e.g. `"${APP_DATA_DIR}/data"`), not a bare `./...` relative path. `./` passes CI (schema only checks it's a string) but is not the documented/official convention and resolution is not guaranteed.
- `dependsOn` — `{ "<service>": { "condition": "service_started" | "service_healthy" | "service_completed_successfully" } }`
- `command`, `entrypoint`, `user`, `hostname`, `networkMode`, `privileged`, `capAdd`, `capDrop`, `securityOpt`, `devices`, `sysctls`, `healthCheck`, `extraLabels`, `deploy` (resource limits), etc.

Other runtipi variables usable as `${...}`: `${APP_DATA_DIR}`, `${APP_PORT}`, `${TZ}`, `${UID}`, plus any `env_variable` from `form_fields`.

## Reverse proxy / networking

Runtipi **auto-generates** the reverse proxy. For the service marked `isMain: true` with an `internalPort`, it:

1. adds traefik routing labels,
2. joins the container to `tipi_main_network`,
3. maps `${APP_PORT}` (= `config.json` `port`) → `internalPort` on the host.

You do **not** write traefik labels or publish the main port yourself. Official store apps (e.g. grafana) carry only `isMain` + `internalPort` and nothing else — match that.

**Rules learned the hard way:**

- **Every app needs exactly one `isMain: true` service.** Without it there is no proxy, no `tipi_main_network` join, no `${APP_PORT}` mapping — the app is unreachable. (This bit invoice-collector.)
- **Never put the main port in `addPorts`.** Runtipi already publishes `config.port → internalPort`; adding `internalPort:internalPort` in `addPorts` double-binds the host port → docker `port is already allocated` and bypasses traefik. Use `addPorts` only for *additional* ports (e.g. a raw TCP/UDP ingestion port). Direct `http://<host-ip>:<port>` access still works without `addPorts` via the auto `${APP_PORT}` map.
- **Backing services (db, cache, etc.) get no `internalPort` and no `addPorts`.** They are reached over the app's compose network by service name (e.g. `mongodb://mongodb:27017`). Don't expose them to the host. Only set `addToMainNetwork: true` on a non-main service if it genuinely must be proxied.
- **`networkMode: host` cannot be reverse-proxied.** A host-network container is not on `tipi_main_network`, so traefik can't route to it → set `config.json` `exposable: false`. Such apps (LAN device discovery, mDNS, Thread/Zigbee, multi-room audio) are reached directly at `http://<host-ip>:<port>`; document that in `description.md`.

The main service's direct-access host port = `config.json`'s `port`.

## Image pinning

Always pin every `image` to an explicit, immutable tag and mirror it in `config.json` `version`.

Why: reproducible installs, no surprise breakage when upstream re-pushes, and **`renovate.json` only bumps pinned tags**. Renovate's custom regex manager matches `"image": "<dep>:<currentValue>"` against the docker datasource — `latest` (or a floating `:2`) gives it nothing to compare, so it silently never updates. A real version unlocks auto bump PRs (which also run `scripts/update-config.ts` to sync `config.json`).

Finding the current tag:

- Docker Hub: `https://hub.docker.com/v2/repositories/<owner>/<image>/tags?page_size=100&ordering=last_updated` (official images use `library/<image>`).
- GHCR: get a pull token from `https://ghcr.io/token?scope=repository:<owner>/<image>:pull`, then `GET https://ghcr.io/v2/<owner>/<image>/tags/list` with `Authorization: Bearer <token>`.

Pick the newest **immutable** tag, preferring clean semver. Some upstreams only publish rolling tags — pin the current immutable one anyway (still better than `latest`):

- build numbers (e.g. diyhue `1057`),
- pre-release/RC (e.g. homey `12.10.0-rc.7`, music-assistant `2.0.0b63`) for beta-only projects,
- commit-sha tags (e.g. openthread-border-router `sha-b868799`) when nothing else exists.

Gotcha: don't assume `latest` exists — some repos (e.g. invoice-collector) publish `0.1`/`master` and **no** `latest` tag at all, so `:latest` would fail to pull. Always verify the tag is in the registry listing.

Note: `renovate.json` disables bumps for the DB images `mariadb`, `mysql`, `mongo`, `postgres`, `redis` (bumped manually). `matchPackageNames` must match the actual image/dep name — e.g. the image is `mongo`, not `mongodb`.

### Inspecting an image before packaging it

The image config blob tells you the real `Entrypoint`, `Cmd`, `User`, `ExposedPorts`, `WorkingDir` and declared `Volumes` — worth reading before guessing at `internalPort`, an entrypoint override or whether a chown init container is needed:

```bash
REPO=owner/image; TAG=1.2.3
T=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:$REPO:pull" | sed -E 's/.*"token":"([^"]*)".*/\1/')
A='application/vnd.oci.image.index.v1+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.docker.distribution.manifest.v2+json'
curl -s -H "Authorization: Bearer $T" -H "Accept: $A" "https://registry-1.docker.io/v2/$REPO/manifests/$TAG"   # → per-arch digest
curl -s -H "Authorization: Bearer $T" -H "Accept: $A" "https://registry-1.docker.io/v2/$REPO/manifests/<amd64-digest>"  # → config digest
curl -sL -H "Authorization: Bearer $T" "https://registry-1.docker.io/v2/$REPO/blobs/<config-digest>" | tr ',' '\n' | grep -iE '"Entrypoint"|"Cmd"|"User"|WorkingDir|ExposedPorts|"Volumes"' -A3
```

`curl -L` is required for blobs (they redirect to a CDN). Architecture support is quicker to check via `https://hub.docker.com/v2/repositories/<repo>/tags/<tag>` — mirror the result in `supported_architectures`.

## Runtime gotchas

Hard-won, each one cost a debugging round.

### A bind mount over an application directory shadows the image's files

Docker seeds an **empty named volume** from the image, but **never** a bind mount. Upstream compose files that mount a named volume over the app's own code directory (akaunting's `/var/www/html`, and anything Laravel/PHP shaped) therefore work upstream and break here, because runtipi mounts host paths.

Two ways out:

- **Mount only the runtime subdirectories** (`storage/`, `data/`, `Modules/`) and leave the code in the image. Preferred when the app recreates those dirs at boot — invoiceshelf's entrypoint does exactly that.
- **Seed the host path from the image with an init container** when the whole directory must persist (it holds `.env`, uploads and installed plugins). Use the *same image* as the main service, mount the host path somewhere neutral, copy only if empty:

  ```json
  { "name": "<app>-seed", "image": "<same image as main>",
    "entrypoint": ["/bin/bash", "-c", "if [ ! -f /seed/artisan ]; then cp -a /var/www/html/. /seed/; fi; chown -R www-data:root /seed"],
    "volumes": [{ "hostPath": "${APP_DATA_DIR}/html", "containerPath": "/seed" }] }
  ```

  Main service then mounts the same host path at the real location with `dependsOn: { "<app>-seed": { "condition": "service_completed_successfully" } }`. Consequence to document in `description.md`: an image bump no longer replaces the app code of an existing install (same as upstream's named-volume behaviour) — updates go through the app's own updater.

### Non-root images need a chown init container

Runtipi creates bind-mount host dirs as root. An image that runs as a non-root uid then cannot write them and dies at boot (invoiceshelf prints a `Cannot write to /var/www/html/storage` banner and exits 1). Add a busybox init container:

```json
{ "name": "<app>-permissions", "image": "busybox:1.38.0",
  "command": ["sh", "-c", "mkdir -p /mnt/data && chown -R 1000:1000 /mnt/data"],
  "volumes": [{ "hostPath": "${APP_DATA_DIR}/data", "containerPath": "/mnt/data" }] }
```

Known uids: invoiceshelf `82`, wealthfolio `1000`, youtrack `13001`. Read `User` from the image config (above) instead of guessing.

### `$` in a form-field value can be eaten before the container sees it

Values flow through Docker Compose interpolation, so a secret containing `$` — argon2id PHC hashes (`$argon2id$v=19$...`) above all — can arrive mangled or empty. When an app demands such a value:

1. keep the form field for convenience, **and**
2. let the entrypoint prefer a file under `${APP_DATA_DIR}` that the user writes by hand, documenting it in `description.md` as the reliable path.

In entrypoint overrides use backticks, not `$(...)`: command substitution written with `$(` is itself at risk of being read as interpolation.

```json
"entrypoint": ["/bin/sh", "-c", "if [ -s /data/password.hash ]; then WF_AUTH_PASSWORD_HASH=`cat /data/password.hash`; export WF_AUTH_PASSWORD_HASH; fi; exec /usr/local/bin/wealthfolio-server"]
```

### Prefer an entrypoint state check over a "run the installer" toggle

Apps whose installer is triggered by an env flag (akaunting's `AKAUNTING_SETUP=true`) usually warn that a second run destroys data, and their install command has no guard of its own. Don't push that on the user as a boolean they must switch off — detect the installed state and clear the flag yourself:

```
if grep -qs '^APP_INSTALLED=true' /var/www/html/.env; then export AKAUNTING_SETUP=false; fi; exec /usr/local/bin/akaunting.sh --start
```

Install then runs exactly once, and retries by itself if it failed halfway.

### Persist app secrets in `form_fields`, not in the container layer

Laravel-style apps generate `APP_KEY` into a `.env` that lives in the container's writable layer, so every recreate rotates it and orphans encrypted settings. If the app accepts the key from the environment (invoiceshelf's `inject.sh` does), generate it once as a `random` field and pass it in (`"value": "base64:${INVOICESHELF_APP_KEY}"`). Same for keys that encrypt stored credentials (`WF_SECRET_KEY`, receipt-wrangler's `ENCRYPTION_KEY`) — tell users in `description.md` to back the key up with `app-data`, and say plainly which ones cannot be rotated.

### Backing service snippets

MariaDB and Redis with healthchecks the main service can gate on:

```json
{ "healthCheck": { "test": "healthcheck.sh --connect --innodb_initialized || exit 1",
                   "interval": "10s", "timeout": "5s", "startPeriod": "30s", "retries": 10 } }
{ "healthCheck": { "test": "redis-cli ping || exit 1",
                   "interval": "10s", "timeout": "5s", "startPeriod": "10s", "retries": 5 } }
```

`MYSQL_RANDOM_ROOT_PASSWORD: yes` plus a `random` form field for `MYSQL_PASSWORD`. The DB user is created on first boot only — say so in the field hint, because changing the password later just locks the app out.

### URL settings

Apps that build links, CORS origins or session cookies from a configured URL (`APP_URL`, `WF_CORS_ALLOW_ORIGINS`, `SESSION_DOMAIN`, `SANCTUM_STATEFUL_DOMAINS`) need it to match what the browser shows, down to scheme and port. Expose them as fields with a sane `http://localhost:<port>` default and spell out the LAN vs domain values in `description.md` — a mismatch shows up as broken assets, redirect loops or a `419` after login, none of which point at the real cause.

## Adding an app — checklist

1. Create `apps/<app-id>/` with the four files.
2. Set `categories` from the valid enum; `id` == folder name.
3. Pin every `image` to an immutable tag (verify it exists in the registry) and mirror it in `config.json` `version`. See Image pinning.
4. Pick a host `port` no other app uses — check with `grep -h '"port"' apps/*/config.json | sort -n | uniq -d`. Mark one service `isMain: true` with its `internalPort`; do **not** republish that port in `addPorts`. Host-network apps → `exposable: false`. See Reverse proxy.
5. Map persistent data to `volumes` using `${APP_DATA_DIR}/...` host paths. Add `schemaVersion: 2` + `$schema` at the compose top level. Check the mounts against Runtime gotchas — shadowed app directories and root-owned bind mounts are the two failures you will not notice until the app is installed.
6. Keep secrets out of the repo — expose them as `form_fields` / env with empty defaults.
7. Add a logo at `metadata/logo.jpg` and a real `metadata/description.md`.
8. Regenerate the Apps table — **do not hand-edit it**, it is generated between the `APPS:START`/`APPS:END` markers from every `config.json`:

   ```bash
   bun .github/scripts/readme-generator.ts
   ```

9. Run `bun install && bun run test` until green.

### Logos

`metadata/logo.jpg` must really be a JPEG (CI only checks the filename, runtipi renders the bytes). Existing apps use 460x460. Take the upstream project's own asset — site logo, apple-touch-icon, app icon in the repo, or the GitHub org avatar (`https://avatars.githubusercontent.com/u/<id>?s=460`) — and convert it with the tools present on macOS:

```bash
sips -z 460 460 logo.png --out logo460.png
sips -s format jpeg -s formatOptions 92 logo460.png --out logo.jpg
```

`sips` cannot read SVG, so prefer a PNG source. Transparent PNGs flatten onto white. Look at the result before committing it.

## Updating an app

Bump `version`, increment `tipi_version`, refresh `updated_at`. The helper script does this:

```bash
bun ./scripts/update-config.ts apps/<app-id>/config.json <newVersion>
```

`tipi_version` is the runtipi update counter — it compares the installed value against the store's to offer updates. **Increment it on _any_ change to an already-published app** (compose, volumes, `form_fields`, env, image tag), not only on upstream version upgrades. Otherwise existing installs never see the fix. `updated_at` must stay `< Date.now()`.
