# Rclone Mount

Rclone connects to cloud-storage providers, encrypts remote content with a `crypt` remote, and exposes the decrypted view under Runtipi's shared media directory. This package includes the modern [rclone-web](https://github.com/rclone/rclone-web) interface embedded in rclone and automatically mounts one configured remote at `/data/cloud` inside the container, corresponding to `cloud/` in Runtipi media.

## Host prerequisite: shared mount propagation

This is an advanced app. A FUSE mount created inside a container is invisible to the host and other containers unless the Runtipi media directory is a shared mount. Before installing, use `${ROOT_FOLDER_HOST}/media` as the host path, ensure its `cloud` child exists, bind the directory onto itself, and mark it recursively shared:

```bash
sudo mkdir -p /path/to/runtipi/media/data/cloud
sudo mount --bind /path/to/runtipi/media/data /path/to/runtipi/media/data
sudo mount --make-rshared /path/to/runtipi/media/data
findmnt -o TARGET,PROPAGATION /path/to/runtipi/media/data
```

The final command must report `shared` for that path. The bind and propagation settings must be recreated after reboot, normally with systemd mount units or equivalent host configuration. Installation fails with `path is mounted ... but it is not a shared mount` when this prerequisite is missing.

This requirement cannot safely be applied by an ordinary Runtipi app: changing host mount propagation requires host-level administration and depends on where Runtipi is installed.

## First start and encrypted remote

Open the app at `http://<host-ip>:5572`, or through its Runtipi domain. The bundled proxy initializes rclone-web with the matching same-origin API address; sign in with the GUI credentials chosen during installation. The interface is embedded in the pinned rclone image and requires no UI download at startup.

Rclone's normal GUI startup notice contains its full login URL, including the password. This package suppresses notice-level rclone output and supplies the credentials through rclone's environment options so they are not exposed in container logs or process arguments. Errors are still logged.

The public proxy removes rclone's HTTP Basic authentication challenge so browsers use the rclone-web login form instead of opening a separate native credentials dialog.

On the first start the configured `encrypted:` remote does not exist, so only the GUI runs:

1. Create the underlying provider remote, such as `cloud-provider`.
2. Create a `crypt` remote named `encrypted` whose target is the provider path, such as `cloud-provider:media`.
3. Choose encryption for filenames and directory names and keep the generated crypt passwords in a separate password manager.
4. Test browsing the `encrypted` remote in the GUI.
5. Restart the Rclone Mount app.

After restart, the decrypted view is mounted at `${ROOT_FOLDER_HOST}/media/cloud` on the host, `/data/cloud` in the Scryer and Weaver apps, and `/media/cloud` in the official Plex app. Cloud-provider objects remain encrypted; applications using the mount see decrypted names and contents.

If you choose another remote name or mount a subdirectory, update **Mounted remote** in the Runtipi app settings and restart. Editing `rclone.conf` or changing the remote in the GUI does not live-reload an active mount.

## Consumption by other apps

Scryer and Weaver use slave propagation on their `${ROOT_FOLDER_HOST}/media` mounts, so they receive rclone remounts without acquiring permission to propagate mounts back to the host.

The official Plex app currently uses a normal private bind mount. Start or restart Plex after Rclone Mount is healthy so Docker captures the existing `/media/cloud` submount. If rclone is restarted or remounted later, restart Plex again. An advanced Plex user override can change its media bind propagation to `rslave` instead.

Do not use the cloud mount for Weaver's incomplete or completed downloads. Keep `/data/downloads` local and use `/data/cloud` as a distinct cloud-backed library or destination. Hard links cannot cross between local storage and the FUSE filesystem.

## Cache, privileges and recovery

Rclone configuration persists in `${APP_DATA_DIR}/config`; VFS data persists in `${APP_DATA_DIR}/cache`. The mount uses full VFS caching for compatibility, with a configurable size limit and a seven-day maximum cache age. Open files can temporarily exceed the configured size.

The container requires `/dev/fuse`, `SYS_ADMIN`, `--allow-other`, an unconfined AppArmor profile, and shared bind propagation. These privileges are substantial: treat the app and its web credentials as administrative infrastructure. Runtipi exposes only the proxy on port `5572`; it routes `/api/` to rclone's separately authenticated RC service without publishing the raw API port on the host. Decypharr can use `http://rclone:5533` with the configured GUI credentials over Runtipi's Docker network for external-rclone cache refreshes.

The authenticated RC service also enables file serving for Runtipi Companion
restore downloads. Authentication remains mandatory; internal consumers
should use `http://rclone:5533` rather than exposing the API publicly.

Back up `rclone.conf` and the crypt passwords outside the server. Losing the crypt passwords permanently prevents decryption. Before restoring or moving the app, stop media consumers, stop rclone, restore the configuration, start rclone, confirm `/cloud` contents, and then restart Plex and other consumers.

[rclone-web](https://github.com/rclone/rclone-web) · [GUI documentation](https://rclone.org/gui/) · [Mount documentation](https://rclone.org/commands/rclone_mount/) · [Docker and mount propagation](https://rclone.org/docker/) · [Source code](https://github.com/rclone/rclone)
