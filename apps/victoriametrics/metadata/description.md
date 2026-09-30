# VictoriaMetrics

VictoriaMetrics is a fast, cost-effective and scalable time-series database and monitoring solution. It ships as a single, dependency-free binary and is a popular drop-in replacement for Prometheus long-term storage.

## Features

- High performance and low resource usage — handles millions of metrics on modest hardware
- PromQL and the more powerful MetricsQL query languages
- Ingestion via Prometheus remote write, InfluxDB line protocol, Graphite, OpenTSDB and CSV
- Built-in `vmui` web UI for ad-hoc querying
- High data compression for cheap long-term retention

## Configuration

The web UI and HTTP API are served on port **8428**. Time-series data is stored in the `data` volume (`/victoria-metrics-data`).

Set the **Retention period** during install (default `12` months). For other options see the [official documentation](https://docs.victoriametrics.com/).
