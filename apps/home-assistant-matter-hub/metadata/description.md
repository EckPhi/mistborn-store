# Home Assistant Matter Hub

Home Assistant Matter Hub simulates **Matter bridges** to publish your Home Assistant entities to any Matter-compatible controller — **Amazon Alexa**, **Apple Home**, **Google Home**, and others. It lets you expose lights, switches, sensors, climate and more from Home Assistant into the Matter ecosystem without re-implementing devices.

## This build

This package uses the community-maintained [`RiDDiX/home-assistant-matter-hub`](https://github.com/RiDDiX/home-assistant-matter-hub) fork, which continues development after the original `t0bst4r` project was discontinued. Migrating from the original keeps your existing fabric connections and device pairings — **no re-pairing required**.

The pinned image is `ghcr.io/riddix/home-assistant-matter-hub:1.7.18` (the latest stable `1.x` line; `2.0` is still alpha).

## Networking

It runs in **host network mode**, which Matter requires for mDNS service discovery and IPv6. A host-network container cannot be reverse-proxied, so it is **not exposable** on a domain — reach the web UI directly at `http://<host-ip>:8482`.

## Configuration

| Field | Purpose |
|---|---|
| **Home Assistant URL** | Base URL of your HA instance, e.g. `http://192.168.1.10:8123`. |
| **Home Assistant access token** | A long-lived access token (HA profile → Security → Long-lived access tokens). |
| **Log level** | `silly`, `debug`, `http`, `info` (default), `warn`, or `error`. |

After install, open the web UI to create one or more **bridges**, choose which entities each bridge exposes, then pair the bridge with your Matter controller using the QR code / pairing code it shows.

Bridge state and pairing data are persisted in the `data` volume (mounted at `/data`).

See the [project documentation](https://riddix.github.io/home-assistant-matter-hub) for bridge setup, entity filters, and controller-specific notes.
