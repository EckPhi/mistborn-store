# QuestDB

QuestDB is a high-performance, open-source time-series database with SQL support. It ingests millions of rows per second and is a great fit for IoT sensor data, home automation metrics and real-time analytics.

## Host prerequisites

QuestDB memory-maps every column file and warns at startup when the kernel's file-handle and mapping limits are low, e.g. `fs.file-max limit is too low [current=524288, recommended=1048576]`. These are host-global kernel settings and cannot be raised from inside the container — set them once on the runtipi host:

```sh
echo "fs.file-max = 1048576" | sudo tee /etc/sysctl.d/99-questdb.conf
echo "vm.max_map_count = 1048576" | sudo tee -a /etc/sysctl.d/99-questdb.conf
sudo sysctl --system
```

The warnings are harmless for small setups; the limits matter once you have many tables/partitions.

The per-process file-descriptor limit is a separate knob: containers inherit it from the Docker daemon (not from host sysctls), so the app sets `ulimits.nofile` to 1048576 in its compose file. If a low limit persists, raise the daemon default in `/etc/docker/daemon.json` (`default-ulimits`) or the dockerd systemd unit (`LimitNOFILE`).

## Endpoints

- **Web console / REST / ILP-over-HTTP**: the app port (`9000` inside the container) — query UI, `/exec`, `/exp`, `/imp` and InfluxDB line protocol ingestion (`/write`).
- **PostgreSQL wire**: `<host-ip>:8812` — connect with any Postgres client using the username/password configured in the app settings. A second, read-only account (default `viewer`, SELECT only) can be enabled in the settings — use that one for Grafana and other dashboards.
- **ILP over TCP**: `<host-ip>:9009` — legacy InfluxDB line protocol socket.

## Retention pipeline (maintenance sidecar)

The app ships a small `questdb-jobs` sidecar that implements a configurable multi-stage downsampling and retention pipeline on top of QuestDB's native materialized views and TTLs.

Configure it in the app settings:

- **Retention: managed tables** — comma-separated list of tables to manage. Empty disables the pipeline.
- **Retention stages** — `<age>:<resolution>` pairs separated by `;`, the last stage may be `<age>:drop`. Units: `h`, `d`, `w`, `M`, `y`.

Example, `30d:1h;2y:1d;10y:drop` gives you:

| Data | Kept for | Where |
|---|---|---|
| Raw rows | 30 days | the table itself |
| Hourly avg/min/max | 2 years | materialized view `<table>_1h` |
| Daily avg/min/max | 10 years | materialized view `<table>_1d` |

For every managed table the sidecar creates one incremental materialized view per stage (`<table>_1h`, `<table>_1d`, ...) containing `avg`/`min`/`max` of all numeric columns, sampled at the stage resolution. QuestDB keeps these views up to date on ingestion — no cron queries. Each view gets a TTL equal to the next stage's age; the raw table is kept until the first stage age. Query the view that matches the time range you are interested in.

Notes:

- Tables need a designated timestamp and numeric columns; non-numeric columns are not carried into the aggregate views.
- Changing the stage list later creates new views but does not delete old ones — drop obsolete `<table>_<res>` views yourself.

## Archiving instead of deleting

Enable **Archive expired raw partitions** to keep the original raw data: instead of a TTL delete, partitions older than the first stage are detached (`ALTER TABLE ... DETACH PARTITION`) and stored as compressed tarballs in `app-data/data/archive/`.

To restore an archive, extract the tarball back into the table's directory, rename the `*.detached` folder to `*.attachable`, and run `ALTER TABLE <table> ATTACH PARTITION LIST '<partition>'` — see the [QuestDB docs](https://questdb.com/docs/reference/sql/alter-table-attach-partition/).

## Backups

Automatic full backups use QuestDB's `CHECKPOINT` mechanism for filesystem-consistent snapshots. They are written as rotated `questdb_<timestamp>.tar.gz` archives to `app-data/data/backups/` at the configured interval. To restore, stop the app, extract a backup over `app-data/data/questdb/`, create an empty `_restore` trigger file if required by your QuestDB version, and start the app again.
