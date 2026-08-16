# agentgateway

[agentgateway](https://agentgateway.dev) is an agentic proxy for AI agents. It fronts any number of MCP servers — remote HTTPS endpoints, or the sidecars bundled here — and presents all of their tools to a client as **one** streamable-HTTP endpoint.

- **MCP endpoint:** `http://<tipi-host>:4000/mcp`
- **Management UI:** `http://<tipi-host>:4000/ui`

Point any MCP client (Claude Code, Claude Desktop, Cursor, …) at the `/mcp` URL and it sees every configured server at once, with tools namespaced per target (`grafana_*`, `tailscale_*`, …).

## How it is configured

Two places, split by what the value is:

- **The install form** holds secrets and sidecar settings — tokens, API keys, and the on/off switch for each bundled sidecar. Nothing else.
- **`app-data/agentgateway/config/config.yaml`** holds the targets. It is seeded on first start, then it is yours. The raw-config editor in the UI writes the same file and the gateway watches it, so edits apply without a restart.

Secrets never go into `config.yaml` as literals. A form field's variable is referenced instead, e.g. `key: $GRIST_API_KEY`, and the gateway expands it from the app environment at load time.

## Bundled sidecars

| Target | Source | Needs |
|---|---|---|
| `grafana` | [grafana/mcp-grafana](https://github.com/grafana/mcp-grafana) | Grafana URL + service account token |
| `tailscale` | [tailscale-mcp](https://github.com/HexSleeves/tailscale-mcp) | Tailscale API key + tailnet |
| `cloudflare-docs` | `docs.mcp.cloudflare.com` | nothing — public |

Both sidecars run inside the gateway's own network namespace and listen on **loopback only**. They are never published to the host or reachable from other containers; the gateway authenticates to each with a bearer token generated at install time.

Each has an enable switch. Turning one **on** adds its target to `config.yaml` on the next start if it isn't there already — so enabling a sidecar later works, and the append never duplicates. Turning one **off** idles the container; its target block stays in `config.yaml` and should be deleted by hand, otherwise the gateway keeps trying to reach a server that isn't listening.

`failureMode` is `failOpen`, so a target that is unconfigured or down is skipped with a warning instead of taking the whole gateway with it. A Tailscale sidecar left enabled without an API key exits on start and restarts in a loop — expected until the field is filled in, and harmless to the other targets.

## Adding your own targets

```yaml
  - name: my-server
    mcp:
      host: https://mcp.example.com/mcp
    policies:
      backendAuth:
        key: $MY_SERVER_TOKEN
      requestHeaderModifier:
        remove:
        - origin
```

Three things worth knowing, each of which has already cost a debugging round:

- **The upstream `Host` header comes from the target URL's hostname, and cannot be overridden.** `requestHeaderModifier` has a `set` for it, but the gateway ignores it — whatever name is in the URL is what the upstream server sees. This decides how you address everything else.
- **The client's `Origin` header is forwarded**, and several MCP servers reject a request carrying one — Grist answers `403 Credentials not supported for cross-origin requests`. Hence `remove: [origin]` on every target.
- **Reaching another Runtipi app has two shapes**, depending on whether it routes on `Host`. If it doesn't, use its service alias on `runtipi_tipi_main_network` — the app id, e.g. `http://grist:8484` — never the full container name, whose underscores the resolver rejects (`backends required DNS resolution which failed`). If it does route on `Host` (Grist answers 404 to a name it doesn't serve), use its **public** URL and set **Extra host mapping** to `<that-domain>:host-gateway`, which resolves the name to this host and sends the request back in through the reverse proxy with the right name and certificate. Without that mapping the public name resolves outward and usually times out, stalling every request on the gateway's 10s connect timeout.
- **Variable references expand everywhere in the file, comments included.** A stray `$` in a comment makes the gateway refuse to start with `error looking key '…' up: environment variable not found`. Anything referenced must exist as a form field.

Keep `targets` the last key in the file — that is where enabled sidecar targets get appended.

## Notes

- The Cloudflare **API** server (`mcp.cloudflare.com`) is deliberately absent: it requires an interactive OAuth consent flow and cannot be fronted by a gateway holding an API token. Only the public docs server is included.
- Grafana tools are read/write according to the service account's role — a Viewer token keeps the agent read-only.
- Tailscale tools are gated by risk level (`read` / `write` / `admin`); the default `read` cannot change your tailnet.
- State (the gateway's SQLite database, plus your config) lives in `app-data/agentgateway/config`. Back that directory up.
