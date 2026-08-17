# Grist

Grist is a modern relational spreadsheet — spreadsheet flexibility on top of a real database, with formulas in Python, access rules, forms, custom widgets and a full REST API.

This packaging exists for one reason: the official Runtipi Grist app only exposes `GRIST_SANDBOX_FLAVOR`, so the **built-in MCP server** and Grist's **OAuth/OIDC server** cannot be turned on. Here they are form fields.

## MCP server

With MCP enabled, AI assistants (Claude, ChatGPT, Claude Code, …) can list and search tables, read and query rows, add or update rows and create documents — as your Grist user, limited by your access rules and by the scopes you approve on the consent screen.

Endpoint:

```
https://<your-grist-host>/api/mcp
```

Requirements:

1. **Full edition must be activated.** `GRIST_MCP_ENABLED`, `GRIST_ENABLE_OIDC_SERVER`, `GRIST_ENABLE_OIDC_DCR` and `GRIST_OIDC_CIMD_ALLOWED_HOSTS` are full-edition feature flags — the flags do nothing on plain `grist-core`. Activate the full edition in the Admin Panel (30-day trial; free activation key for individuals and orgs under US $1M annual funding), or paste a key into the *Activation key* field.
2. **Expose the app on a real HTTPS domain.** MCP clients like Claude.ai fetch the OAuth discovery document over the public internet and redirect back to it. `APP_HOME_URL` is derived from the domain you expose the app on in Runtipi, so an unexposed LAN-only install cannot be connected to Claude.ai.
3. **Enable the OIDC server** (`GRIST_ENABLE_OIDC_SERVER=true`) for interactive sign-in. API-key clients need only `GRIST_MCP_ENABLED`.
4. **Redis** — bundled as a sidecar and wired up via `REDIS_URL`, nothing to configure. Grist keeps issued OAuth tokens in it; without it the log says

   ```
   OIDC server enabled but REDIS_URL is unset: OAuth bearer-token validation is disabled.
   ```

   and `/api/mcp` rejects every token. Redis also backs sessions, webhooks and notifications, so existing installs are logged out once when it appears.
5. **Allow the client host for CIMD.** `GRIST_OIDC_CIMD_ALLOWED_HOSTS=claude.ai,chatgpt.com` (the default here) lets those clients register themselves from their metadata document instead of being pre-provisioned. Clients that do not support CIMD either need `GRIST_ENABLE_OIDC_DCR=true` or a manually registered OAuth app. Do not set `*` unless you also configure `GRIST_PROXY_FOR_UNTRUSTED_URLS`.

Connecting Claude: *Settings → Connectors → Add custom connector*, URL `https://<your-grist-host>/api/mcp`. For Claude Code:

```bash
claude mcp add --transport http grist https://<your-grist-host>/api/mcp
```

Access can be narrowed per connection on Grist's consent screen and revoked later in account settings.

## Settings worth knowing

- **Sandbox flavor** — `gvisor` is the safe default; switch to `unsandboxed` only if formulas fail to run on your hardware.
- **Session secret** — generated once and stored in the app config so logins survive container recreates. Back it up together with the app data.
- **Default email** — single-user convenience mode: anonymous visitors become that user. Leave it empty if you want real accounts; MCP clients sign in as a real account.
- **Force login** — blocks all anonymous access, including publicly shared documents.

## Data

Everything (SQLite documents, home database, config) lives in `app-data/grist/data/grist-data`, mounted at `/persist`. The Redis sidecar persists to `app-data/grist/redis` — losing it only forces MCP/OAuth clients and browser sessions to sign in again.

Migrating from the official Runtipi Grist app: stop it, copy its `grist-data` directory into this app's `app-data` path, then start this one. The two apps share port 8484, so do not run both.

Upstream: <https://github.com/gristlabs/grist-core> · MCP docs: <https://support.getgrist.com/mcp/>
