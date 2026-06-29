# Zigbee2MQTT

[Zigbee2MQTT](https://www.zigbee2mqtt.io/) bridges your Zigbee devices to MQTT, letting you control them from Home Assistant, Node-RED, openHAB or any MQTT client — without a proprietary vendor bridge or cloud.

## What's different in this build

The official Runtipi Zigbee2MQTT app **requires** a USB Zigbee stick and passes a host `/dev` device into the container. This copy **removes that mandatory device passthrough** so it works with a **network (serial-over-IP) adapter** — e.g. a SLZB-06, a Sonoff dongle behind `ser2net`, or any `tcp://host:port` coordinator.

The adapter is configured entirely through the **Serial port** field instead of a device mapping:

- **Network adapter:** `tcp://192.168.68.100:6638`
- **USB adapter:** a `/dev/ttyUSB0`-style path — note that a local USB stick *also* needs a docker `devices` mapping, which this build does not add. Use the official app, or add the mapping manually, for USB sticks.

## Configuration

| Field | Purpose |
|---|---|
| **Serial port** | Coordinator address. `tcp://<host>:<port>` for a network adapter. |
| **MQTT server** | Broker URL, e.g. `mqtt://192.168.68.10:1883`. |

Both are written into Zigbee2MQTT via its `ZIGBEE2MQTT_CONFIG_*` environment overrides on every start. Any further settings can be edited in `configuration.yaml` under the app data directory.

The web UI is reachable at `http://<host-ip>:8290`.
