# Telegraf

Telegraf is InfluxData's plugin-driven agent for collecting and reporting metrics. Hundreds of input plugins (system stats, Docker, MQTT, SNMP, HTTP, ping, ...) and output plugins (InfluxDB, QuestDB via ILP, Prometheus, Kafka, ...) make it the swiss-army knife of metrics collection.

## What this app does out of the box

- Mounts the host filesystem read-only at `/hostfs`, so the bundled configuration reports **host** CPU, memory, swap, disk, disk I/O and network stats (not the container's).
- Writes metrics to an **InfluxDB 2.x** instance using the URL, token, organization and bucket from the app settings — point it at the InfluxDB app running on the same runtipi host via the host's LAN IP (e.g. `http://192.168.1.10:8086`).

This is a headless agent: there is no web UI.

## Customizing

The full configuration lives at `app-data/data/config/telegraf.conf`. Edit it to add inputs/outputs and restart the app to apply. Examples:

- **QuestDB output** (InfluxDB line protocol over HTTP):

  ```toml
  [[outputs.influxdb_v2]]
    urls = ["http://192.168.1.10:9000"]
    content_encoding = "identity"
  ```

- **MQTT input** for home automation topics:

  ```toml
  [[inputs.mqtt_consumer]]
    servers = ["tcp://192.168.1.10:1883"]
    topics = ["sensors/#"]
    data_format = "json"
  ```

See the [Telegraf plugin directory](https://docs.influxdata.com/telegraf/v1/plugins/) for everything else.
