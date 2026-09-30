# Scryer

Scryer is a media manager for movies, series and anime. It searches and evaluates releases, coordinates acquisition and imports, manages subtitles, and can notify Plex, Jellyfin or Emby after library changes.

## First start

Requires Runtipi 4.10.1 or newer. Open Scryer at `http://<host-ip>:8686`, or expose it through a Runtipi domain, then complete setup and create an administrator.

Scryer sees Runtipi's shared media directory as `/data`. Configure its completed-download path as `/data/downloads/usenet/complete` when using the standalone Weaver app. The default final library roots are:

- `/data/movies`
- `/data/series`
- `/data/anime`

Downloads and final libraries remain beneath one `/data` mount. When permissions and the underlying filesystem permit it, Scryer can therefore hard-link imports instead of copying entire files.

## Connecting Weaver

Install the standalone Weaver app, create an Integration-scoped API key in Weaver under Settings → Security, and add Weaver to Scryer as an NZBGet-compatible download client.

Use `http://weaver:9090` when the Docker service name resolves across Runtipi's main network. If it does not, use Weaver's Runtipi domain or `http://<host-ip>:9090`. Configure `/data/downloads/usenet/complete` as the completed path on both sides.

Scryer and Weaver do not share configuration or databases. Their only shared state is the Runtipi media filesystem and the API key entered into Scryer.

## Plex and future cloud storage

The official Runtipi Plex app mounts the same host media tree at `/media`. Consequently, Scryer's `/data/movies` is Plex's `/media/movies`, with equivalent paths for series and anime.

Do not place an rclone FUSE mount over the complete Runtipi media directory. A future rclone integration should use a child such as `/data/cloud`, leaving local downloads and libraries visible when the remote is unavailable. Hard links cannot cross between local storage and an rclone mount.

## Backups

Scryer state, its SQLite database and generated encryption key persist in `${APP_DATA_DIR}/config`. Back up that directory together with the Runtipi media directory. Losing the encryption key makes stored passwords and API keys unrecoverable. Stop Scryer before taking a filesystem-level database backup.

[Documentation](https://www.scryer.media/scryer/docs/) · [Source code](https://github.com/scryer-media/scryer)
