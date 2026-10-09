# NZBGet

[NZBGet](https://nzbget.com) is an efficient Usenet downloader with a browser-based queue, automatic repair and extraction, RSS feeds and scheduling.

## First start

Open NZBGet through Runtipi or at `http://<host-ip>:6789`. Sign in using the username and password entered during installation. Add your Usenet provider under **Settings → NEWS-SERVERS**, save the configuration and reload NZBGet. A Usenet provider account and NZB files or an indexer are needed to download content.

The installation fields set web authentication on container startup. Change these fields in Runtipi to change the credentials; changes made only in NZBGet may be overwritten on restart.

## Persistent storage

Configuration is stored in `${APP_DATA_DIR}/config`, mounted at `/config`. Downloads are stored in Runtipi’s shared `${ROOT_FOLDER_HOST}/media/downloads` directory (`/opt/runtipi/media/downloads` for a standard installation), mounted at `/downloads`; keep NZBGet's download directories beneath `/downloads` so that queued and completed files survive container recreation. Back up the config directory and shared downloads.

This package uses the LinuxServer image with Runtipi’s UID and GID, matching Weaver and Scryer. Its startup initializes the bind-mount permissions. Use `/downloads/usenet/intermediate` for incomplete work and `/downloads/usenet/complete` for completed downloads. Weaver and Scryer see these same host directories as `/data/downloads/usenet/intermediate` and `/data/downloads/usenet/complete`; configure a remote path mapping from `/downloads` to `/data/downloads` when integrating NZBGet with them. Downloads and final libraries use separate container mounts, so hardlinks across those mounts are unavailable.

Update through Runtipi to use the pinned container image; do not use NZBGet's in-app binary updater.

Container documentation: https://docs.linuxserver.io/images/docker-nzbget/
