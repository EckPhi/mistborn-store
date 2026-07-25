# Power Price Collector

Collects European day-ahead power prices and writes them to whichever sinks you configure. A scheduler fetches once the daily auction has cleared, and a web UI shows component health, run history and the current price curve.

## Why ENTSO-E and not EPEX directly

EPEX SPOT's own data feed needs a commercial licence. The auction results are published to the ENTSO-E Transparency Platform as document type `A44` (day-ahead prices), which is free and covers every European bidding zone through one API — DE-LU, AT, FR, NL, BE, CH, GB, PL and the Nordics included, 40 zones in total.

Get a token: register at [transparency.entsoe.eu](https://transparency.entsoe.eu/), then email `transparency@entsoe.eu` from the registered address with the subject "Restful API access" and your account email in the body. The token appears under Account Settings.

Until a token is set the app runs but every fetch fails with that instruction, and the health endpoint reports degraded.

## Sinks

| Type | Transport |
| --- | --- |
| `questdb` | InfluxDB line protocol over HTTP `:9000/write`, or TCP `:9009` |
| `ilp` | Line protocol to InfluxDB 1.x/2.x, VictoriaMetrics, anything compatible |
| `telegraf` | `influxdb_v2_listener` on `:8186`, or `socket_listener` over TCP |
| `mqtt` | Retained messages, optional Home Assistant discovery |
| `grist` | REST, add-or-update |

Every sink is idempotent. The collector deliberately re-fetches overlapping windows to pick up late corrections, so re-runs update in place instead of duplicating — QuestDB via `DEDUP UPSERT KEYS(timestamp, zone)` on the auto-created table, Grist via `PUT /records` with a `require` clause.

## Configuration

The config lives at `/config/config.yaml`, which is `app-data/data/config/config.yaml` on the host. Edit it in the web UI's **Config** tab — saving validates, writes and hot-applies it, rebuilding sinks and reinstalling cron jobs without a restart.

Secrets stay out of that file. `${VAR}` and `${VAR:-default}` expand from the environment when the config is loaded, so reference the app's form fields instead of pasting values:

```yaml
source:
  type: entsoe
  api_token: ${ENTSOE_API_TOKEN}

collection:
  zones: [DE_LU, AT]

sinks:
  - name: questdb
    type: questdb
    host: ${QUESTDB_HOST}
    port: 9000
    table: power_price
```

On a fresh install no config file exists yet, so the app starts with defaults and **no sinks** — it fetches nothing useful until you configure it in the UI.

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
