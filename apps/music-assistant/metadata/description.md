# Music Assistant

Music Assistant is a free, open-source music library manager and multi-room streaming server. It aggregates your streaming services and local files into one library and plays them on a huge range of supported devices — Sonos, Chromecast, AirPlay, Squeezebox, DLNA and more.

## Features

- Combine Spotify, Apple Music, Qobuz, Tidal, YouTube Music and local files in one library
- Multi-room, synchronized audio playback
- Deep Home Assistant integration
- No transcoding by default — sends the highest quality your players support

## Important: host networking

Music Assistant requires **host network mode** to discover and stream to players on your LAN (mDNS/UPnP). This package runs with `network_mode: host` and the elevated capabilities the project requires, so the web UI binds directly to host port **8095**.

Music and configuration are stored in the `data` volume (`/data`). See the [installation docs](https://www.music-assistant.io/installation/) for adding music providers and players.
