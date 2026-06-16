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

Useful optional fields: `website`, `supported_architectures` (`["amd64","arm64"]`), `dynamic_config: true`, `form_fields`, `https`, `no_gui`, `url_suffix`, `force_expose`, `created_at`, `updated_at`.

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

## docker-compose.json

Top-level shape: `{ "services": [ ... ] }` (optional `overrides`).

Each service object supports (subset most used):

- `name` (required) — service name
- `image` (required) — pin a real tag, avoid bare `latest` where possible
- `internalPort` — port the container listens on
- `isMain` — mark the primary web UI service
- `environment` — **object** map `{ "KEY": "value" }` (not an array)
- `addPorts` — array of `{ containerPort, hostPort, udp?, tcp?, interface? }`. **Only for _extra_ ports.** Do **not** republish the main `internalPort` here — see Reverse proxy below
- `volumes` — array of `{ hostPath, containerPath, readOnly?, shared?, private? }`. Use `./<name>/...` relative host paths (resolved under the app data dir)
- `dependsOn` — `{ "<service>": { "condition": "service_started" | "service_healthy" | "service_completed_successfully" } }`
- `command`, `entrypoint`, `user`, `hostname`, `networkMode`, `privileged`, `capAdd`, `devices`, `healthCheck`, `restart` via `deploy`, etc.

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

## Adding an app — checklist

1. Create `apps/<app-id>/` with the four files.
2. Set `categories` from the valid enum; `id` == folder name.
3. Pick a unique host `port`. Mark one service `isMain: true` with its `internalPort`; do **not** republish that port in `addPorts`. Host-network apps → `exposable: false`. See Reverse proxy.
4. Map persistent data to `volumes`.
5. Keep secrets out of the repo — expose them as `form_fields` / env with empty defaults.
6. Add a logo at `metadata/logo.jpg` and a real `metadata/description.md`.
7. Add a row to the Apps table in `README.md`.
8. Run `bun install && bun run test` until green.

## Updating an app

Bump `version`, increment `tipi_version`, refresh `updated_at`. The helper script does this:

```bash
bun ./scripts/update-config.ts apps/<app-id>/config.json <newVersion>
```
