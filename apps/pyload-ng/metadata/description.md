# pyLoad-ng

pyLoad-ng is a lightweight download manager with a web interface, download queues, file-hosting account support, automatic extraction and plugins for many hosting services.

## First start

Requires Runtipi 4.10.1 or newer. Open `http://<host-ip>:8001` and sign in with username **pyload** and password **pyload**. Change the administrator password in pyLoad before exposing it through a Runtipi domain. Add hosting accounts and configure download and extraction options in the web interface.

This app uses LinuxServer's stable release channel, pinned to a specific image build. The upstream version currently uses a development-style version number even on this channel.

## Storage

Settings, accounts, users and queue state persist in `${APP_DATA_DIR}/config`, mounted at `/config`. Downloads and extracted files persist in `${ROOT_FOLDER_HOST}/media/downloads/pyload`, mounted at `/downloads`. Keep pyLoad's Download Folder set to `/downloads`.

The download directory is part of Runtipi's shared media tree: apps mounting that tree at `/data` see it as `/data/downloads/pyload`, while Plex sees `/media/downloads/pyload`. Download locally here before moving files to a cloud library. This app does not mount or manage an rclone remote.

The LinuxServer image initializes the configuration directory and sets its ownership at startup. It also sets ownership of the download directory itself. Its process uses Runtipi's UID/GID when supplied, defaulting to `0:0` to match this store's media applications.

## Network and backups

Runtipi handles the web interface's host port and domain routing. The optional Click'n'Load listener on port 9666 is not published by this app.

Back up the configuration directory and any downloads you want to retain. The configuration contains hosting credentials and should be kept private.

[pyLoad project](https://github.com/pyload/pyload) · [Container documentation](https://docs.linuxserver.io/images/docker-pyload-ng/)
