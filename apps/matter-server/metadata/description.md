# Matter Server

[Python Matter Server](https://github.com/home-assistant-libs/python-matter-server) is a **Matter (CHIP) controller** exposed over a WebSocket API. It is the backend that **Home Assistant's built-in Matter integration** talks to, handling commissioning and control of Matter devices on your network.

This package pins `ghcr.io/matter-js/python-matter-server:8.1.2` (latest stable).

## No web UI

This is a **headless WebSocket service** — there is nothing to open in a browser. Point the Home Assistant Matter integration at:

```
ws://<host-ip>:5580/ws
```

## Networking

It runs in **host network mode**, which Matter requires for mDNS service discovery, IPv6, and on-network commissioning. A host-network container cannot be reverse-proxied, so it is **not exposable** on a domain — reach it directly at the host IP on port `5580`.

## Bluetooth commissioning

Bluetooth commissioning of new devices is supported via the host **D-Bus** socket (`/run/dbus`, mounted read-only) and `apparmor=unconfined`. If your host has no Bluetooth adapter you can still commission devices that are already reachable on the IP network / Thread.

## Storage

- `--storage-path /data` — fabric and device state.
- `--paa-root-cert-dir /data/credentials` — PAA root certificates.

Both live under the persistent `data` volume.

See the [project documentation](https://github.com/home-assistant-libs/python-matter-server) and the [Docker guide](https://github.com/home-assistant-libs/python-matter-server/blob/main/docs/docker.md) for details.
