# RundfunkArr

RundfunkArr searches German public broadcaster media libraries, including ARD and ZDF, and downloads programmes directly over HTTP. It provides a Newznab indexer and a SABnzbd-compatible download client for Sonarr, Radarr and Prowlarr, with optional FFmpeg MKV conversion, subtitles, scheduled searches and TVDB/TMDB metadata.

## First start

Open `http://<your-server-ip>:6767` and complete the setup wizard. Keep the download directory set to `/downloads`. Optional metadata API keys and broadcaster settings can be configured in the application.

The public URL is configured automatically from Runtipi's `APP_PROTOCOL` and `APP_DOMAIN` variables, covering LAN access, local HTTPS and public domain exposure. No manual domain or URL entry is needed.

Login is disabled by default upstream. Enable a username and password under **Settings → General → Security** before exposing the app publicly, and use HTTPS. Enabling login generates an integration API key; copy it into all connected indexers and download clients. The generated **Diagnostics admin key** from the Runtipi installation settings unlocks **Diagnostics & Logs** and is separate from that integration key.

## Sonarr, Radarr and Prowlarr

- Add a **Generic Newznab** indexer with URL `http://<your-server-ip>:6767/api/newznab`.
- Add a **SABnzbd** download client with host `<your-server-ip>` and port `6767` (without SSL for this LAN connection).
- Use the integration API key from RundfunkArr's security settings when login is enabled. With login disabled, upstream accepts an arbitrary API key.

Downloads are stored in Runtipi's shared `media/downloads` folder and mounted at `/downloads`. Sonarr and Radarr must have access to the same host folder. If their container path differs, configure a remote path mapping in the media manager from `/downloads` to its own path. Use the server's LAN address for connections from other apps; `localhost` inside another container points to that container.

## Persistent data

The SQLite database, settings, history and post-processing scripts persist under the app's `data` directory, mounted at `/app/prisma/data`. Back up this directory together with your Runtipi app settings. Place executable post-processing scripts in `data/scripts`; the Alpine image supports `sh`, not Bash.

The upstream entrypoint initializes the database and adjusts data/download permissions using the Runtipi UID/GID (falling back to 1000). It recursively adjusts permissions on the shared downloads folder at startup.

The optional local MediathekView index uses about 800 MB of additional data storage. Broadcaster availability and geographic restrictions still apply.
