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
