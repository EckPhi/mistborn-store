# Rclone

This app serves rclone's bundled web interface from a container and forwards its API requests to an rclone service running on the host. The host owns the rclone config and any mounts. The API connection uses a Unix socket; the app does not expose a host API port, mount media, or run FUSE.

## Host service

Install rclone on the host, configure its remotes, and install a systemd service that runs only the remote-control API (`rclone rcd`). For example:

```ini
[Service]
User=rclone
Group=rclone
RuntimeDirectory=rclone
RuntimeDirectoryMode=0750
UMask=0007
EnvironmentFile=/etc/rclone/rc.env
ExecStart=/usr/bin/rclone rcd --config=/home/rclone/.config/rclone/rclone.conf --rc-addr=/run/rclone/rc.sock
Restart=on-failure
```

Put `RCLONE_RC_USER` and `RCLONE_RC_PASS` in `/etc/rclone/rc.env` and restrict that file to root (`chmod 600`). Adjust the binary and config paths for the host. `RuntimeDirectory` makes `/run/rclone` at service start, and rclone creates `/run/rclone/rc.sock`. Start this service before installing or starting the Runtipi app so Docker can bind-mount the socket directory. Sign in to the web interface with the credentials from `rc.env`.

At startup, the proxy reads the socket's group ID and runs its Nginx worker with that group, allowing access to the group-restricted socket and `0750` runtime directory without making the socket world-accessible. The socket is mounted read-only and only into the proxy container. Keep the host service under a dedicated unprivileged account and retain RC authentication: the API can run commands and access files as that account. If Docker uses user-namespace remapping, configure host socket ownership and permissions for the mapped container group as well.

### Allowing the host service to create FUSE mounts

Mistborn Bootstrap's mount-capable RC service creates FUSE mounts visible on the host without a systemd override. Existing installs must update and reapply the confirmed `rclone_service/service` task to receive the revised unit. Remove any obsolete local drop-in after verifying the managed unit, then restart the service and recreate the mount.

Keep the service running as the dedicated, unprivileged `mistborn-rclone` user and give that user write access to each mountpoint. `fusermount3` needs its setuid operation, so `NoNewPrivileges` must be disabled. A custom unit with filesystem isolation such as `ProtectSystem`, `PrivateTmp`, `ProtectHome`, `ProtectKernelTunables`, or `ProtectControlGroups` can create a mount visible only inside the service. Check host visibility with `findmnt -M /opt/runtipi/media/cloud`; if that is empty while the service sees the mount, inspect the unit's mount namespace settings.

The container runs the web UI only for practical purposes; it also starts a local, unauthenticated RC listener on its loopback interface because rclone's bundled GUI launcher starts both servers together. That local API is not published or used by the proxy. All browser `/api/` requests go to the authenticated host socket.

## Host mounts

Create cloud mounts on the host through your systemd mount service or the rclone API. To make cloud files visible to Runtipi apps, use a host mountpoint under `${ROOT_FOLDER_HOST}/media`, such as `${ROOT_FOLDER_HOST}/media/cloud`. Configure VFS cache and other mount options in the host service. If an app container bind-mounts the media directory before the cloud mount exists, Docker's default `rprivate` bind propagation can leave the container seeing the empty underlying directory. Start the host mount before that container, or configure host-to-container mount propagation for the media bind.

[rclone GUI documentation](https://rclone.org/gui/) · [rclone `rcd` documentation](https://rclone.org/commands/rclone_rcd/) · [rclone mount documentation](https://rclone.org/commands/rclone_mount/)
