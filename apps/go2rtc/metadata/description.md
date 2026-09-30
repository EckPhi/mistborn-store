# go2rtc

[go2rtc](https://github.com/AlexxIT/go2rtc) is an **ultimate camera streaming** application. It bridges many camera protocols and serves **zero-delay** streams as RTSP, WebRTC, MSE/MP4, HomeKit, RTMP, MJPEG and more, from a huge range of sources (RTSP/ONVIF cameras, USB, FFmpeg, HomeKit, Nest, and others).

This package pins `alexxit/go2rtc:1.9.14`.

## Ports

It runs in **host network mode**, which is required for WebRTC ICE candidate discovery and for reaching cameras / mDNS on your LAN. A host-network container cannot be reverse-proxied, so it is **not exposable** on a domain — reach it directly on the host:

| Port | Use |
|---|---|
| `1984` | Web UI / REST API (`http://<host-ip>:1984`) |
| `8554` | RTSP server |
| `8555` | WebRTC (TCP + UDP) |

## Use with Home Assistant / Eufy

go2rtc is commonly used as the streaming backend for camera integrations. For the [Home Assistant eufy_security integration](https://github.com/fuatakgun/eufy_security#2-install-go2rtc-add-on), install the separate **Eufy Security WS** app as well, then point the integration's go2rtc host/port at `http://<host-ip>:1984`. The integration registers each camera's stream with go2rtc at runtime over its API — no manual config needed.

## Configuration

go2rtc works out of the box. To predefine streams or change settings, edit `go2rtc.yaml` in the `config` volume (mounted at `/config`). See the [configuration docs](https://github.com/AlexxIT/go2rtc#configuration) for the full reference.
