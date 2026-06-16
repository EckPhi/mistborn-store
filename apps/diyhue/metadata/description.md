# diyHue

diyHue is an open-source emulator of the Philips Hue bridge. It speaks the Hue API, so you can control a huge range of smart lights from the official Hue app, Home Assistant, Alexa, Google Home and HomeKit — without buying the original bridge hardware.

## Supported lights

Hue, Yeelight, Tasmota, ESPHome, WLED, MiLight/LimitlessLED, Shelly, Tradfri, native ESP8266/ESP32 lights and more.

## Important: host networking

diyHue must run in **host network mode** so it can discover lights and respond to the SSDP/UPnP discovery the Hue app uses. This package runs with `network_mode: host`.

The **MAC address** of your host's primary network interface is **required** — diyHue uses it to generate the certificates that make the bridge appear genuine to the Hue app.

Configuration is stored in the `config` volume (`/opt/hue-emulator/config`). The web UI is served on host port **80**. See the [documentation](https://diyhue.readthedocs.io/) for adding lights.
