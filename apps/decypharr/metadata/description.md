# Decypharr

Decypharr is a downloader for Debrid services and Usenet. It presents qBittorrent- and SABnzbd-compatible APIs to media managers such as Scryer, Sonarr and Radarr, then downloads completed files to shared local storage.

This Runtipi package intentionally uses Decypharr's downloader-only mode. It does not grant FUSE access or elevated mount privileges and does not expose Decypharr's DFS or rclone mounting features.

## First start

Requires Runtipi 4.10.1 or newer. Open Decypharr at `http://<host-ip>:8282`, or expose it through a Runtipi domain, and complete the setup wizard. Configure authentication before exposing the app publicly; the UI stores provider API keys and media-manager credentials.

Use these settings:

- Mount type: `none`
- Default download action: `download`
- Download folder: `/data/downloads/decypharr`

Runtipi's shared media directory is mounted at `/data`. Downloaded files therefore persist under `${RUNTIPI_MEDIA_DIR}/downloads/decypharr` on the host.

The `download` action transfers complete files from the configured Debrid or Usenet provider to local storage. It uses local disk space and bandwidth; it does not create symlinks or stream files from a virtual mount.

## Connecting Scryer

For Debrid torrents, add Decypharr to Scryer as a qBittorrent-compatible download client. For Usenet, add it as a SABnzbd-compatible client.

Use `http://decypharr:8282` when the Docker service name resolves across Runtipi's main network. Otherwise, use the Runtipi domain or `http://<host-ip>:8282`.

Configure `/data/downloads/decypharr` as the completed-download path. Scryer sees the same Runtipi media tree at `/data`, so no remote path mapping is needed. Scryer can then import completed files into `/data/movies`, `/data/series` or `/data/anime`.

## Sonarr and Radarr

Add Decypharr as qBittorrent for torrents or SABnzbd for Usenet. The SABnzbd-compatible endpoint uses the `/sabnzbd` URL base. Configure a category for each media manager and use `/data/downloads/decypharr` on both sides.

If an Arr app maps the Runtipi media directory to a path other than `/data`, add a remote path mapping from `/data/downloads/decypharr` to its equivalent container path.

## Plex

Plex does not need access to Decypharr's download folder. Point Plex at the final library directories populated by Scryer or an Arr app, normally `/media/movies`, `/media/series` and `/media/anime` in the official Runtipi Plex app.

## Standalone rclone app

The standalone rclone app is independent and not required by this downloader-only Decypharr package. Its `/data/cloud` mount can coexist with Decypharr's local downloads, but Decypharr does not use it automatically.

## Backups

Configuration, authentication state and provider credentials persist in `${APP_DATA_DIR}/config`. Back up this directory. Downloaded files persist beneath `${RUNTIPI_MEDIA_DIR}/downloads/decypharr` and should follow your normal media backup policy.

[Documentation](https://decypharr.com/) · [Source code](https://github.com/sirrobot01/decypharr)
