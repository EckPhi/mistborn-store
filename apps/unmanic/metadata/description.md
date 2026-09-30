# Unmanic

Unmanic watches media libraries and uses plugins to process files automatically. It can transcode video, optimize storage, and run other file management tasks that you choose in its web interface.

## Media and storage

The Runtipi `media` folder is mounted at `/library` with write access. Add `/library` as a library in Unmanic, then choose and configure the plugins you want to run. Plugins can replace or remove media files, so back up your library before enabling processing.

Settings and plugins persist in `app-data/unmanic/config`. In-progress conversions use `app-data/unmanic/cache`; leave enough free space there for the largest files you plan to process. Back up the config directory along with your media library. The cache contains temporary work and does not need a backup.

Unmanic uses Runtipi's UID and GID for file ownership. That user needs read and write access to the media folder.

## Access

Open `http://<runtipi-host>:8888` on your local network. Unmanic has no built-in web authentication, so this app does not enable domain exposure. If you publish it through your own reverse proxy, require authentication there.

Hardware transcoding is not configured by this app; it requires device access and settings specific to your host.

## Links

- [Unmanic documentation](https://docs.unmanic.app/docs/installation/docker/)
- [Source code](https://github.com/Unmanic/unmanic)
