# Scrape Dojo

[Scrape Dojo](https://scrape-dojo.com) is a self-hosted, config-driven web scraping platform. You describe what to scrape in JSONC config files — sequences of `navigate`, `extract`, `transform` and `logger` actions — and Scrape Dojo runs them in a Puppeteer-driven browser. A single container serves both the **UI** and the **REST API** on the same port.

## Quick start

1. Install the app. The five required auth/encryption secrets are **generated automatically** and persisted — no manual `openssl`/`node` key generation needed.
2. Open the UI at `http://<host-ip>:8092`. The API lives under `/api` on the same port (e.g. `http://<host-ip>:8092/api/scrape/<id>`).
3. Create your first account (MFA is on by default).

## Your first scrape

Scrapes are picked up via hot reload from the `config/sites/` directory under the app data folder. Drop a `my-first-scrape.jsonc`:

```jsonc
{
  "$schema": "../scrapes.schema.json",
  "scrapes": [
    {
      "id": "my-first-scrape",
      "metadata": {
        "description": "My first scrape — reads the page title",
        "version": "1.0.0",
        "triggers": [{ "type": "manual" }]
      },
      "steps": [
        {
          "name": "Read title",
          "actions": [
            { "name": "navigate", "action": "navigate", "params": { "url": "https://example.com" } },
            { "name": "title", "action": "extract", "params": { "selector": "h1" } },
            { "name": "logTitle", "action": "logger", "params": { "message": "Found title: {{previousData.title}}", "level": "log" } }
          ]
        }
      ]
    }
  ]
}
```

Then run it from the UI, or hit `http://<host-ip>:8092/api/scrape/my-first-scrape`.

## Configuration

| Field | Purpose |
|---|---|
| **Initialize database schema** | `DB_SYNCHRONIZE`. Must be **on** for the first start so the SQLite tables are created. Turn **off** afterwards to avoid accidental schema changes or data loss on updates. |
| **Require MFA** | Turn off to skip TOTP/MFA on account creation. |

The encryption key, JWT secret, refresh-token secret and the two MFA secrets are auto-generated on install and reused on every subsequent start — losing them means losing access to stored secrets, so they are kept stable by Runtipi.

Data, config, downloads, logs and the Puppeteer browser profile all persist under the app data directory.
