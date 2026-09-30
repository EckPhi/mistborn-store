# Homey Pro (Self-Hosted Server)

The Homey Self-Hosted Server runs Athom's Homey Pro smart-home platform as a container on your own hardware. It gives you the full Homey experience — apps, Flows, logic and the Homey ecosystem of thousands of supported brands — without the dedicated Homey Pro device.

## Features

- Thousands of supported brands and devices over Wi-Fi and LAN
- Powerful Flow-based automations and advanced logic
- Managed through the Homey mobile app and `my.homey.app`

## Limitations

The self-hosted server communicates over your network only. **Zigbee, Z-Wave, Bluetooth and Infrared are not supported** — those radios require Homey Pro hardware.

## Important: host networking

Homey requires **host network mode** and **privileged** access to discover devices and provide a dedicated LAN presence. Make sure the host has a stable LAN IP.

There is no browser UI for this app — set it up by adding the server in the Homey app. Data is persisted in the `data` volume (`/homey/user`). See the [official guide](https://support.homey.app/hc/en-us/articles/24010537261980).
