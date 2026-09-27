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

When the host `rclone rcd` service creates mounts through the RC API, systemd must allow it to access the mountpoint and let `fusermount3` perform its setuid operation. For a service hardened with `ProtectSystem=strict`, add a drop-in (replace the path with the parent directory of your mountpoints):

```ini
# sudo systemctl edit mistborn-rclone.service
[Service]
ReadWritePaths=/opt/runtipi/media
NoNewPrivileges=no
```

Use the **parent directory** in `ReadWritePaths`, not the mountpoint itself. Systemd can make an explicitly writable path appear as a bind mount inside the service's mount namespace; FUSE then rejects that path as already mounted. `NoNewPrivileges=no` is needed because `fusermount3` relies on its setuid bit. Keep the service running as a dedicated, unprivileged user and grant write access only to the directory tree containing the intended mountpoints. Apply changes with `sudo systemctl daemon-reload`, then restart the host service.

The container runs the web UI only for practical purposes; it also starts a local, unauthenticated RC listener on its loopback interface because rclone's bundled GUI launcher starts both servers together. That local API is not published or used by the proxy. All browser `/api/` requests go to the authenticated host socket.

## Host mounts

Create cloud mounts on the host through your systemd mount service or the rclone API. To make cloud files visible to Runtipi apps, use a host mountpoint under `${ROOT_FOLDER_HOST}/media`, such as `${ROOT_FOLDER_HOST}/media/cloud`. Configure VFS cache and other mount options in the host service. Other apps see the ordinary mounted directory through their media mounts.

[rclone GUI documentation](https://rclone.org/gui/) · [rclone `rcd` documentation](https://rclone.org/commands/rclone_rcd/) · [rclone mount documentation](https://rclone.org/commands/rclone_mount/)
