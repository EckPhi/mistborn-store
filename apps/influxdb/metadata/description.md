# InfluxDB

InfluxDB is an open-source time-series database purpose-built for metrics, events and IoT sensor data. This package runs **InfluxDB 2.x**, which bundles the database, the Flux query engine and a web UI in a single image.

## Features

- High-throughput ingestion and fast time-series queries
- Built-in web UI, dashboards and alerting
- Flux and InfluxQL query languages
- First-class integration with Telegraf, Grafana, Home Assistant and Node-RED

## Configuration

On first start the database is initialized automatically using the values you provide during install:

- **Admin username / password** — the initial admin account
- **Initial organization** and **initial bucket**

Data is stored in the `data` volume (`/var/lib/influxdb2`) and configuration in the `config` volume (`/etc/influxdb2`). The web UI and API are served on port **8086**.

Generate API tokens from the web UI after setup. See the [official docs](https://docs.influxdata.com/influxdb/v2/).

## Retention pipeline (maintenance sidecar)

The app ships a small `influxdb-jobs` sidecar that can provision a multi-stage downsampling pipeline using InfluxDB's native task engine, plus automatic compressed backups.

Configure it in the app settings:

- **Admin API token** — auto-generated on fresh installs and used to initialize the database. On installs that predate this setting, the generated value does not match the real admin token: create an all-access token in the InfluxDB UI (Load Data → API Tokens) and paste it here.
- **Retention stages** — empty disables the pipeline. `<age>:<resolution>` pairs separated by `;`, the last stage may be `<age>:drop`. Units: `h`, `d`, `w`, `M`, `y`.

Example, `30d:1h;2y:1d;10y:drop` on initial bucket `default` yields:

| Bucket | Contents | Retention |
|---|---|---|
| `default` | raw data | 30 days |
| `default_1h` | hourly means (Flux task) | 2 years |
| `default_1d` | daily means (Flux task) | 10 years |

The sidecar creates the stage buckets and one Flux task per stage (mean via `aggregateWindow`, numeric fields). The tasks run inside InfluxDB itself; the sidecar only provisions them idempotently. Adjust the generated tasks in the UI (Tasks) if you need different aggregations.

**Warning:** enabling the pipeline sets the retention of the initial bucket to the first stage age — raw data older than that is deleted by InfluxDB.

## Backups

At the configured interval the sidecar runs `influx backup` and stores rotated `influxdb_<timestamp>.tar.gz` archives in `app-data/data/backups/`. To restore, extract an archive and use `influx restore` — see the [restore docs](https://docs.influxdata.com/influxdb/v2/backup-restore/restore/).
