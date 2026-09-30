# OpenThread Border Router

OpenThread Border Router (OTBR) is a Thread border router for POSIX platforms. It bridges a low-power Thread mesh network to your regular IP network, which is what brings **Matter-over-Thread** smart-home devices online.

## What's different in this build

This package uses the [`bnutzer/otbr-tcp`](https://github.com/bnutzer/docker-otbr-tcp) image instead of the stock `openthread/border-router`. The stock image only talks to a **USB serial** RCP; this one runs `socat` internally to bridge a **network-attached (serial-over-IP) RCP** to OTBR. So no USB dongle or host `/dev` device is required — point it at the radio's IP and TCP port (e.g. an **SLZB-06 / SLZB-MR** running its Thread radio over the network).

It runs in **host network mode** (so it cannot be reverse-proxied — reach it directly at `http://<host-ip>:8080`), `privileged` with `NET_ADMIN`, the IPv6-forwarding sysctls OTBR needs, and passes `/dev/net/tun` through.

## Configuration

| Field | Purpose |
|---|---|
| **RCP radio host** | IP/hostname of the network Thread radio, e.g. `192.168.68.100`. |
| **RCP radio TCP port** | Serial-over-IP port. SLZB default `6638`. |
| **RCP baudrate** | RCP UART baudrate, default `460800`. |
| **Backbone interface** | Host LAN/Wi-Fi interface, e.g. `eth0`. |

The web GUI is served on host port **8080** and lets you form or join a Thread network. State is stored in the `data` volume (`/var/lib/thread`). See the [OpenThread docs](https://openthread.io/guides/border-router) and the [image README](https://github.com/bnutzer/docker-otbr-tcp) for details.
