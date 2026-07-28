# Power Price Collector

Collects European power prices and writes them to whichever sinks you configure. A scheduler fetches once the daily auction has cleared, and a web UI shows component health, run history and the current price curve.

## Upgrading from 1.x

2.x replaced the single `source:` block and the global `collection.zones` with a `sources:` list, each entry owning its own zones. **Since 2.2.0 an old config is migrated automatically on startup** — nothing to edit by hand. The log says what it changed, and the file on disk is left alone until you save from the UI, so a downgrade still works.

Old:

```yaml
source:
  type: entsoe
  api_token: ${ENTSOE_API_TOKEN}
collection:
  zones: [DE_LU, AT]
```

New (what the migration produces):

```yaml
sources:
  - type: entsoe
    api_token: ${ENTSOE_API_TOKEN}
    zones: [DE_LU, AT]
```

`collection:` still exists and keeps `lookback_days`, `lookahead_days` and `fail_fast` — only `zones` moved out of it.

> **Avoid 2.0.0 and 2.1.0.** They rejected a 1.x config and exited, which under runtipi's restart policy is a crash loop with no web UI to fix it from. 2.2.0 migrates instead. If you are stuck on one of those, upgrading is enough — no manual edit needed.

QuestDB tables created before 2.2.0 are migrated on startup too: a `product` column is added and the dedup keys widen to `(timestamp, zone, product)`, so day-ahead and imbalance prices for the same hour stop overwriting each other.

## Why ENTSO-E and not EPEX directly

EPEX SPOT's own data feed needs a commercial licence. The auction results are published to the ENTSO-E Transparency Platform as document type `A44` (day-ahead prices), which is free and covers every European bidding zone through one API — DE-LU, AT, FR, NL, BE, CH, GB, PL and the Nordics included, 40 zones in total.

Get a token: register at [transparency.entsoe.eu](https://transparency.entsoe.eu/), then email `transparency@entsoe.eu` from the registered address with the subject "Restful API access" and your account email in the body. The token appears under Account Settings.

Until a token is set the app runs but every fetch fails with that instruction, and the health endpoint reports degraded.

## Sources

Each source owns its own zones, because coverage is a property of the upstream.

| Type | Key needed | Coverage | Resolution | Markets | Independent of ENTSO-E? |
| --- | --- | --- | --- | --- | --- |
| `entsoe` | yes, free | all 40 zones | 15/30/60 min | day-ahead, intraday auctions, imbalance | — (is the source) |
| `nordpool` | no, but only the last ~90 days | Nordics + Baltics | 15 min | day-ahead | **Yes** — the exchange itself |
| `omie` | no | ES, PT | 15 min | day-ahead | **Yes** — the exchange itself |
| `awattar` | no | DE-LU, AT | 60 min only | day-ahead | **Yes** — EPEX reseller |
| `energy_charts` | no | 39 zones | 15 min | day-ahead | **No** — relays SMARD/ENTSO-E |

Each source also has `products:`, defaulting to `[day_ahead]`. Only ENTSO-E carries more; the config form greys out markets a given type cannot serve. Nord Pool's public portal only serves roughly the last 90 days without credentials, so pair it with ENTSO-E if you want to backfill years.

Two sources must not claim the same zone **and** market — the sinks de-duplicate on (timestamp, zone, product), so both writing one would race and the later write would silently win. The config refuses to load rather than let that happen. Splitting by market is fine: one source can take DE-LU day-ahead while another takes its imbalance prices.

energy-charts is not a second opinion: it relays SMARD/ENTSO-E, so it fails whenever the upstream publication chain does. What it buys is working without an API token and covering the ENTSO-E web API being unreachable. Note also that 24 of its 39 zones are licensed by Fraunhofer for private and internal use only; those are refused unless you set `allow_restricted_zones: true`.

## Sinks

| Type | Transport |
| --- | --- |
| `questdb` | InfluxDB line protocol over HTTP `:9000/write`, or TCP `:9009` |
| `ilp` | Line protocol to InfluxDB 1.x/2.x, VictoriaMetrics, anything compatible |
| `telegraf` | `influxdb_v2_listener` on `:8186`, or `socket_listener` over TCP |
| `mqtt` | Retained messages, optional Home Assistant discovery |
| `grist` | REST, add-or-update |

Every sink is idempotent. The collector deliberately re-fetches overlapping windows to pick up late corrections, so re-runs update in place instead of duplicating — QuestDB via `DEDUP UPSERT KEYS(timestamp, zone, product)` on the auto-created table, Grist via `PUT /records` with a `require` clause.

If you collect more than day-ahead, keep `{product}` in the MQTT topic template (it is there by default). Without it every market publishes to the same topic and the last write wins.

## Importing history

The dashboard has an **Import history** panel: pick a date range and it runs in the background with a progress bar. Re-importing a range you already loaded is safe.

Set `backfill: false` on the MQTT sink before importing — a multi-year import would otherwise publish thousands of retained messages and leave the topic holding an arbitrary historic day instead of today's curve.

## Configuration

The config lives at `/config/config.yaml`, which is `app-data/data/config/config.yaml` on the host. Edit it in the web UI's **Config** tab — a generated form, with zones picked from a filterable list. Saving validates, writes and hot-applies without a restart.

Secrets stay out of that file. `${VAR}` and `${VAR:-default}` expand from the environment when the config is loaded, and are stored verbatim, so reference the app's form fields instead of pasting values:

```yaml
sources:
  - type: entsoe
    api_token: ${ENTSOE_API_TOKEN}
    zones: [DE_LU, AT]

sinks:
  - name: questdb
    type: questdb
    host: ${QUESTDB_HOST}
    port: 9000
    table: power_price
```

On a fresh install no config file exists yet, so the app starts with defaults and **no sinks** — it fetches nothing useful until you configure it in the UI.

If the config cannot be loaded at all, the app still starts and still serves the UI — inert, with no sources, sinks or scheduler — showing the error and the offending values in the editor so you can fix and save without a restart. It reports unhealthy throughout, so it never looks fine while collecting nothing.

## Pairing with the QuestDB app

Install the QuestDB app from this store, then set the QuestDB host form field to the runtipi host's **LAN IP**, not `questdb`. Each app is its own compose project on its own network, so service names do not resolve across apps; QuestDB publishes `9000` and `9009` on the host, and that is the reachable path.

Add `power_price` to QuestDB's **Retention: managed tables** setting for downsampling, archiving and backups.

Query it:

```sql
SELECT timestamp, price FROM power_price
WHERE zone = 'DE_LU' AND timestamp IN today()
ORDER BY timestamp;
```

## Data notes

- Prices are **EUR/MWh**; `price_ct_kwh` is written alongside.
- Timestamps are UTC. Fetch windows align to each zone's **local** midnight, so DST days stay 23 or 25 hours instead of being clipped.
- Resolutions of 60, 30 and 15 minutes are handled — several zones have moved to 15-minute market time units, and both can appear in one document.
- Negative prices are normal and nothing clamps them. The UI renders them below a zero baseline.
- Day-ahead auctions clear around 12:45 CET/CEST, so the default schedule is 13:15 `Europe/Berlin` with a two-hourly retry sweep. A run that finds nothing published yet is recorded as *skipped*, not as an error.

## Security

The web UI has **no authentication**. Keep it on a trusted network or behind the reverse proxy, and set `web.allow_config_edit: false` in the config to make it read-only — the config editor otherwise accepts arbitrary sink endpoints.
