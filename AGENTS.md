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
- For `type: random`: `min` sets the generated string length (default 32); `encoding` is `"base64"` or `"hex"`.
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

## Adding an app — checklist

1. Create `apps/<app-id>/` with the four files.
2. Set `categories` from the valid enum; `id` == folder name.
3. Pin every `image` to an immutable tag (verify it exists in the registry) and mirror it in `config.json` `version`. See Image pinning.
3. Pick a unique host `port`. Mark one service `isMain: true` with its `internalPort`; do **not** republish that port in `addPorts`. Host-network apps → `exposable: false`. See Reverse proxy.
4. Map persistent data to `volumes` using `${APP_DATA_DIR}/...` host paths. Add `schemaVersion: 2` + `$schema` at the compose top level.
5. Keep secrets out of the repo — expose them as `form_fields` / env with empty defaults.
6. Add a logo at `metadata/logo.jpg` and a real `metadata/description.md`.
7. Add a row to the Apps table in `README.md`.
8. Run `bun install && bun run test` until green.

## Updating an app

Bump `version`, increment `tipi_version`, refresh `updated_at`. The helper script does this:

```bash
bun ./scripts/update-config.ts apps/<app-id>/config.json <newVersion>
```

`tipi_version` is the runtipi update counter — it compares the installed value against the store's to offer updates. **Increment it on _any_ change to an already-published app** (compose, volumes, `form_fields`, env, image tag), not only on upstream version upgrades. Otherwise existing installs never see the fix. `updated_at` must stay `< Date.now()`.
