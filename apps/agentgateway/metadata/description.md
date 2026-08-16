# agentgateway

[agentgateway](https://agentgateway.dev) is an agentic proxy for AI agents. It fronts any number of MCP servers — local processes, remote HTTPS endpoints, or the sidecars bundled here — and presents all of their tools to a client as **one** streamable-HTTP endpoint.

- **MCP endpoint:** `http://<tipi-host>:4000/mcp`
- **Management UI:** `http://<tipi-host>:4000/ui`

Point any MCP client (Claude Code, Claude Desktop, Cursor, …) at the `/mcp` URL and it sees every configured server at once, with tools namespaced per target (`grafana_*`, `tailscale_*`, …).

## What's bundled

| Target | Source | Needs |
|---|---|---|
| `grafana` | [grafana/mcp-grafana](https://github.com/grafana/mcp-grafana) sidecar | Grafana URL + service account token |
| `tailscale` | [tailscale-mcp](https://github.com/HexSleeves/tailscale-mcp) sidecar | Tailscale API key + tailnet |
| `cloudflare-docs` | `docs.mcp.cloudflare.com` | nothing — public |
| `grist` | your Grist instance | endpoint URL + API key (optional) |

Both sidecars run inside the gateway's own network namespace and listen on **loopback only**. They are never published to the host or reachable from other containers; the gateway authenticates to each with a bearer token generated at install time.

`failureMode` is `failOpen`, so a target that is unconfigured or down is skipped with a warning instead of taking the whole gateway with it. A Tailscale sidecar without an API key exits on start and restarts in a loop — that is expected until you fill the field in, and it does not affect the other targets.

## Configuration

The install form covers the common case. Everything else lives in `app-data/agentgateway/config/config.yaml`, which is **seeded on first start only** — later edits to that file survive app updates, and the app never overwrites it. Restart the app to apply changes, or use the UI.

Adding a remote MCP server by hand looks like this:

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

Two things worth knowing before you write your own targets:

- **Variable references expand everywhere in the file, comments included.** A stray `$` in a comment makes the gateway refuse to start with `error looking key '…' up: environment variable not found`. Variables must exist in the app environment, so anything you reference has to come from a form field.
- **The gateway forwards the client's `Origin` and `Host` headers upstream.** Several MCP servers reject those: Grist answers `403 Credentials not supported for cross-origin requests` when an `Origin` is present, and the bundled sidecars validate `Host`. Hence `remove: [origin]` on every target here, and `set: {host: …}` on the two loopback ones.

## Notes

- The Cloudflare **API** server (`mcp.cloudflare.com`) is deliberately absent: it requires an interactive OAuth consent flow and cannot be fronted by a gateway with an API token. Only the public docs server is included.
- Grafana tools are read/write according to the service account's role — a Viewer token keeps the agent read-only.
- Tailscale tools are gated by risk level (`read` / `write` / `admin`); the default `read` cannot change your tailnet.
- State (the gateway's own SQLite database, plus your config) lives in `app-data/agentgateway/config`. Back that directory up.
