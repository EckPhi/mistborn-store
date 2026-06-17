# Bambuddy

**Your printers. No cloud. Your rules.** Bambuddy is a self-hosted command center for Bambu Lab 3D printers — from a single A1 to a 40-printer farm. It controls printers directly over your local network (Developer Mode), keeps all print history on your own server, and replaces most of what Bambu's cloud offers.

## Features

- Multi-printer dashboard and print farm management
- Local print history, file/library manager
- Scheduling, automation, auto power-off, notifications
- Server-side slicing (optional sidecar) — slice & print from a browser or phone
- Virtual Printer / Proxy Mode for remote printing without the cloud
- Optional Home Assistant and Tailscale integration

## Networking — important

This app runs with **host networking** because:

- **Printer discovery** uses SSDP, which needs L2 multicast on your LAN.
- **Camera streaming** and the **virtual-printer** FTPS/RTSP listeners bind several ports.

Because of host networking it **cannot be reverse-proxied** by Runtipi (`exposable` is off). Reach the web UI directly at:

```
http://<your-server-ip>:8000
```

If you don't need discovery you can add printers manually by IP. Virtual-printer / proxy features use additional ports (3000, 3002, 8883, 990, 322, 6000, 2024-2026, 50000-50029); with host networking these are already available on the host — see the project docs.

## Configuration

- **PUID / PGID** (optional, default `1000`) — set to your host user/group (`id -u` / `id -g`) so files written to the data volume are owned by you.
- Timezone is taken from Runtipi's global `TZ`.
- Home Assistant integration (HA URL + token) and other advanced options can be set later from the Bambuddy UI / environment.

## Data

Application data and print history are stored in `data`, logs in `logs` (mounted under the app's data dir).

Requires Bambu Lab printers with **Developer / LAN Mode** enabled. Source: <https://github.com/maziggy/bambuddy>
