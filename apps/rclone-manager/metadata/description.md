# RClone Manager

RClone Manager provides a browser interface for managing remotes, files, transfers, scheduled tasks and mounts through the existing host-installed rclone service. This package uses the stable v0.3.3 release image, pinned to its published commit tag.

## Before installing

Set up and start the authenticated host `rclone rcd` service described in the Rclone app's store description. It must create `/run/rclone/rc.sock` before this app starts. Keep the existing host service and its configuration; this app does not replace them.

Enter the host service's `RCLONE_RC_USER` and `RCLONE_RC_PASS` in the installation form. Choose separate credentials for signing in to Manager. The private bridge checks the host connection before Manager starts; incorrect host credentials or a missing socket prevent startup.

Open `http://<host-ip>:5574`, or use the domain configured in Runtipi, and sign in with the **Web UI** credentials.

## Automatic host connection

On first startup, the package creates `/data/connections.json` with **Host rclone** selected as the active remote backend. A private HTTP bridge forwards requests to the host Unix socket and supplies the host credentials. The bridge has no published host port and does not join Runtipi's main network. Leave the Host rclone connection's username, password and config path empty in Manager.

Later starts preserve the connection file and any changes made in the UI, including the selected backend. Changing a remote backend's config path can change the configuration used by the host daemon; leave it blank to retain the existing host config.

Manager's upstream entrypoint still downloads its own rclone binary on first startup. With the seeded remote connection, operations use the host daemon. Selecting **Local** in Manager instead uses the container backend and its separate `/config/rclone.conf`.

## Files, mounts and cloud authentication

Paths used for operations on **Host rclone** belong to the host filesystem. Mountpoints such as `/opt/runtipi/media/cloud` are created by the host rclone service, with that service's permissions and FUSE configuration. Manager does not receive host media mounts, `/dev/fuse` or extra mounting privileges. The same host mount visibility and bind propagation considerations documented by the Rclone app apply here.

Existing cloud remotes and tokens stay on the host. Creating a remote that requires browser OAuth may need additional host-side authorization, such as running `rclone authorize` on a computer with a browser and supplying the resulting token. This package does not publish the OAuth callback port.

Manager can stop the remote rclone daemon through its controls. Host rclone binary upgrades and systemd configuration remain host administration tasks.

## Persistence and credentials

Manager's settings, schedules, saved connections and downloaded binary persist in `${APP_DATA_DIR}/data`. Its separate local-backend rclone configuration persists in `${APP_DATA_DIR}/config`. The existing host rclone configuration and cache remain in their existing locations.

Back up Manager's app data and the generated **Credential encryption secret** from the installation form together. Keep that secret unchanged; rotating it can make saved encrypted credentials unreadable. Host RC credentials are provided by the bridge rather than stored in the initial connection file. Update the installation form if the host credentials change.

[RClone Manager source](https://github.com/Zarestia-Dev/rclone-manager) · [Release v0.3.3](https://github.com/Zarestia-Dev/rclone-manager/releases/tag/v0.3.3) · [Rclone RC documentation](https://rclone.org/rc/)
