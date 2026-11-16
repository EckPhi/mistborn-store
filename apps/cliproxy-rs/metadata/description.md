# CLIProxy-RS

CLIProxy-RS gives coding tools such as Codex CLI and Claude Code a shared API endpoint backed by provider API keys or supported account logins. Use the built-in dashboard to add providers and manage model routing.

## First start

Open the app in Runtipi to reach the dashboard at `/management.html`. Direct LAN access uses port 8318. The main container prints two generated keys in the Runtipi app logs at startup.

- `CLIPROXY_MANAGEMENT_KEY` signs in to the dashboard.
- `CLIPROXY_CLIENT_KEY` authenticates API clients. For OpenAI-compatible clients, use the app URL with `/v1` appended.

The startup logs contain both credentials in plaintext. Keep access to the logs private and redact them before sharing. The keys, config, provider credentials and plugins persist in the app's `data` directory. Startup prints the original bootstrap keys from `keys.env`. If you rotate keys in the app, save the new values separately.

## Plugins

The plugin runtime is enabled on first start. Open the dashboard's plugin store to install plugins when you need them. [Privacy Filter](https://github.com/rheodev/cpa-plugin-privacyfilter) redacts detected secrets and personal data in supported request fields before forwarding them to the model provider. Enable it for workloads where replacing that text with placeholders is appropriate.
