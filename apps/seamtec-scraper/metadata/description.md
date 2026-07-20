# Seamtec Scraper

Read-only scraper for the Seamtec SCADA web UI (`scc.seamtec.net`). The site is a Blazor Server app, so content only exists after a real browser renders it — the scraper drives a headless Chromium (Playwright), logs in, walks the configured entity pages plus the active-errors and event-history pages on individual schedules, and emits datapoints to one or more sinks.

This is a headless service: there is no web UI. Watch its output with the container logs.

## Configuration

- **Username / password** — Seamtec credentials, passed via environment.
- **Config file** — `weissenberg.toml` (baked into the image, full Weissenberg facility setup) or `/config/seamtec.toml` to use the editable copy in `app-data/data/config/seamtec.toml`. The config defines entities, schedules, errors/events pages and sinks.
- **Sink** — overrides the sinks from the config file:
  - `stdout` — JSON lines to the container log
  - `ilp:<host-ip>:9009` — InfluxDB line protocol over TCP, points at the QuestDB app on the same runtipi host (use the host's LAN IP)

  For multiple simultaneous sinks (MQTT, Telegraf HTTP, several ILP targets), define them in the custom config file instead.
- **Failure notification URLs** — optional [apprise](https://github.com/caronc/apprise) URLs for scrape-failure notifications.

The Playwright session (login state) persists in `app-data/data/storage/`, so restarts reuse the login instead of re-authenticating.

## Pairing with the QuestDB app

Install the QuestDB app from this store, then set the sink to `ilp:<host-ip>:9009`. Add the scraped tables to QuestDB's **Retention: managed tables** setting to get multi-stage downsampling, archiving and backups of the scraped data.
