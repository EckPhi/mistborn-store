# Weaver

Weaver is an efficient Usenet downloader with an NZBGet-compatible API, repair and extraction support, and a web interface. It can serve Scryer, Sonarr, Radarr and other media managers.

## First start

Requires Runtipi 4.10.1 or newer. Open Weaver at `http://<host-ip>:9090`, or expose it through a Runtipi domain. Sign in with the **Admin username** and generated **Admin password** supplied during installation.

The bootstrap credentials create the first login only. Later changes must be made in Weaver under Settings → Security. Create a separate Integration-scoped API key there for each media manager instead of reusing the administrator password.

Strict security mode is enabled. Weaver will refuse to start without its bootstrap login on a fresh installation and will not run post-processing scripts.

## Shared media layout

Weaver sees Runtipi's shared media directory as `/data` and initially uses:

- `/data/downloads/usenet/intermediate` for active and incomplete work
- `/data/downloads/usenet/complete` for completed downloads

The sibling `/data/downloads/torrents` directory is reserved for torrent clients. Final media libraries can live at `/data/movies`, `/data/series` and `/data/anime`.

Install the standalone Scryer app with the same Runtipi UID and GID. In Scryer, configure `/data/downloads/usenet/complete` as Weaver's completed path. Because both applications mount `${ROOT_FOLDER_HOST}/media` once at `/data`, completed downloads and final libraries remain within one filesystem and can be hard-linked when the underlying storage supports it.

Do not add another `${ROOT_FOLDER_HOST}/media/data` mount. `${ROOT_FOLDER_HOST}/media` already points to Runtipi's shared media data directory; appending `/data` creates an unintended nested directory. Multiple overlapping mounts also obscure files and introduce extra mount boundaries.

## Connecting clients

From another Runtipi app, use `http://weaver:9090` when the Docker service name resolves across the shared main network. Otherwise use Weaver's Runtipi domain or `http://<host-ip>:9090`. Use an Integration-scoped API key as the client credential.

## Storage and backups

Weaver's database, settings and generated encryption key persist in `${APP_DATA_DIR}/config`. Back up that directory together with the shared media directory. Losing the encryption key makes stored provider credentials unrecoverable. Stop Weaver before taking a filesystem-level database backup.

The bootstrap password is stored in Runtipi's generated application environment and remains visible through Docker inspection. Rotate it inside Weaver after the first sign-in if that exposure is unsuitable for your threat model.

[Documentation](https://www.scryer.media/weaver/docs/) · [Source code](https://github.com/scryer-media/weaver)
