# Matter Server

[Matter.js Server](https://github.com/matter-js/matterjs-server) is a **Matter controller** exposed over a WebSocket API, built on the JavaScript Matter SDK ([matter.js](https://github.com/project-chip/matter.js)). It is a **drop-in replacement for the Python Matter Server** and acts as the backend that **Home Assistant's Matter integration** talks to, handling commissioning and control of Matter devices on your network.

This package pins `ghcr.io/matter-js/matterjs-server:0.7.1` (latest stable).

## No web UI

This is a **headless WebSocket service** — there is nothing to open in a browser. Point the Home Assistant Matter integration at:

```
ws://<host-ip>:5580/ws
```

## Networking

It runs in **host network mode**, which Matter requires for mDNS service discovery, IPv6, and on-network commissioning. A host-network container cannot be reverse-proxied, so it is **not exposable** on a domain — reach it directly at the host IP on port `5580`.

## Bluetooth commissioning

Bluetooth (BLE) commissioning of new devices is supported via the host **D-Bus** socket (`/run/dbus`, mounted read-only) and `apparmor=unconfined`. If your host has no Bluetooth adapter you can still commission devices that are already reachable on the IP network / Thread.

## Storage

`--storage-path /data` keeps fabric and device state under the persistent `data` volume.

See the [project documentation](https://github.com/matter-js/matterjs-server) for details.
