# Eufy Security WS

`eufy-security-ws` is a small server wrapper around the [eufy-security-client](https://github.com/bropat/eufy-security-client) library. It exposes Eufy Security devices — cameras, video doorbells, sensors and base stations — over a **WebSocket API** so other applications can read state and control them.

It is most commonly used as the backend for the [Home Assistant eufy-security integration](https://github.com/fuatakgun/eufy_security), but any WebSocket client can talk to it.

## How it works

- No web UI. The server only speaks WebSocket on port **3000** (`ws://<host-ip>:3000`).
- Clients on your LAN (e.g. Home Assistant) connect to that WebSocket.
- Because the WebSocket has no authentication, this app is **not exposable** on a public domain — keep it on the local network.

## Configuration

Set these at install time:

- **Eufy account email / password** (required). Strongly recommended: create a **dedicated secondary Eufy account** and share your devices with it, rather than using your primary account — running this alongside the official app on the same account can cause logouts.
- **Country** — two-letter code (e.g. `US`, `DE`, `GB`).
- **Language** — optional, e.g. `en`, `de`.
- **Trusted device name** — optional label shown in the Eufy app.

Two-factor authentication / CAPTCHA may be requested on first login; follow the project docs for completing it via the WebSocket API.

## go2rtc (live streaming)

For camera **live streaming** (RTSP / WebRTC) the [eufy_security integration recommends](https://github.com/fuatakgun/eufy_security#2-install-go2rtc-add-on) running **go2rtc**. This is packaged as a **separate [`go2rtc`](https://github.com/AlexxIT/go2rtc) app** in this store — install it and point the integration's go2rtc host/port at `http://<host-ip>:1984`. The integration registers each camera's stream with go2rtc at runtime, so no manual `go2rtc.yaml` is needed.

## Data

Persistent state (tokens, device data) is stored in the app's `data` volume (`/data` in the container).

Source: <https://github.com/bropat/eufy-security-ws>
