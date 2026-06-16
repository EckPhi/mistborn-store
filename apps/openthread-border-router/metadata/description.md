# OpenThread Border Router

OpenThread Border Router (OTBR) is a Thread border router for POSIX platforms. It bridges a low-power Thread mesh network to your regular IP network, which is what brings **Matter-over-Thread** smart-home devices online.

## Requirements

OTBR needs a connected **802.15.4 Radio Co-Processor (RCP)** — a USB Thread dongle (e.g. Nordic nRF52840, Silicon Labs) flashed with RCP firmware.

This package runs in **host network mode** with `NET_ADMIN` and the IPv6 forwarding sysctls OTBR requires, and passes your serial dongle and `/dev/net/tun` through to the container.

## Configuration

Set these during install:

- **RCP radio device URL** — the Spinel URL, e.g. `spinel+hdlc+uart:///dev/ttyACM0?uart-baudrate=460800`
- **Serial device path** — the host path of the dongle, e.g. `/dev/ttyACM0` (must exist before install)
- **Infrastructure interface** — your host LAN/Wi-Fi interface, e.g. `eth0`

The web GUI is served on host port **80** and lets you form or join a Thread network. State is stored in the `data` volume (`/data`). See the [OpenThread docs](https://openthread.io/guides/border-router) for details.
