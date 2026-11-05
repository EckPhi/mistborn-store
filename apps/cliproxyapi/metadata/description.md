# CLIProxyAPI

CLIProxyAPI turns the OAuth logins of CLI coding subscriptions — Codex (ChatGPT),
Claude Code, Gemini CLI, Antigravity, Kimi, xAI and others — into standard
OpenAI-, Claude- and Gemini-compatible API endpoints. Several accounts per
provider are load-balanced round-robin. A web management panel handles logins,
client keys and usage statistics.

In this store it is meant to sit **behind LiteLLM**: CLIProxyAPI holds the
subscription logins, LiteLLM holds the virtual keys, budgets and model aliases
that your clients use.

## Install and open the panel

Choose a **management password** during installation. Open
`http://<runtipi-host>:8317/management.html` and sign in with that password.
The panel is downloaded from the upstream project's GitHub releases on first
open, so the server needs outbound internet access.

On first start the app writes `app-data/data/config.yaml` with one client API
key: `sk-cpa-` followed by the generated **Initial client API key material**
shown in this app's Runtipi settings. After that the file belongs to
CLIProxyAPI — change keys and settings in the panel. Changing the form field
later does not rewrite the key.

| Port | Purpose |
|---|---|
| 8317 | API (`/v1`, `/v1beta`), management panel and management API |

## Log in to your subscriptions

In the panel, open **OAuth login** and start the login for a provider. The
provider redirects your browser to a `localhost` callback URL, which will not
load because the proxy runs on the Runtipi host. Copy that full URL from the
browser's address bar and paste it back into the panel to finish the login.
Credentials are stored in `app-data/data/auths/`.

API keys for providers (Gemini, Claude, Codex, OpenAI-compatible upstreams) can
also be added in the panel.

## Connect LiteLLM

Both apps join Runtipi's shared network, so LiteLLM reaches this app directly
by its service name — no domain or host port required:

- **API base:** `http://cliproxyapi:8317/v1`
- **API key:** `sk-cpa-<Initial client API key material>` (or another key
  created in the panel)

In the LiteLLM dashboard, add a model with the **OpenAI-Compatible Endpoints**
provider, the API base and key above, and the model name `openai/<model id>`.
The `openai/` prefix selects LiteLLM's OpenAI-compatible adapter. List the
available model IDs once logins are set up:

```bash
curl -H "Authorization: Bearer sk-cpa-..." http://<runtipi-host>:8317/v1/models
```

Equivalent `config.yaml` entry for LiteLLM:

```yaml
model_list:
  - model_name: coding
    litellm_params:
      model: openai/<model id from /v1/models>
      api_base: http://cliproxyapi:8317/v1
      api_key: sk-cpa-...
```

CLIProxyAPI also serves the Claude Messages API at `/v1/messages`. To use
LiteLLM's native Anthropic adapter instead, use `anthropic/<model id>` with API
base `http://cliproxyapi:8317`.

Clients outside Runtipi use `http://<runtipi-host>:8317/v1` or the exposed
domain. Runtipi's additional browser authentication redirects API clients to a
login page, so leave it off when exposing the API.

## Security

The API port answers anyone who holds a client key, and every request is billed
to your subscriptions. Keep the keys secret and prefer routing clients through
LiteLLM's virtual keys. The management password grants full control including
reading stored credentials; avoid the `$` character in it, because Compose
interpolation can mangle it.

## Backups and updates

Back up `app-data/data` — it contains `config.yaml`, client keys and all
provider login tokens. Image updates keep the existing `config.yaml`;
CLIProxyAPI migrates older layouts when it saves the configuration.

## References

- [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI)
- [Documentation](https://help.router-for.me)
- [LiteLLM OpenAI-compatible endpoints](https://docs.litellm.ai/docs/providers/openai_compatible)
