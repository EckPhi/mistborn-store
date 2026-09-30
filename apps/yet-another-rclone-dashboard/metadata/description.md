# Yet Another Rclone Dashboard

This dashboard provides an alternative web interface for the same host-installed rclone service used by the Rclone app. It can browse remotes, manage files, and show transfers. It does not manage mounts or perform interactive remote configuration.

The proxy downloads and verifies the upstream `v0.4.4` dashboard release at startup, then serves its static files. Startup requires access to GitHub. Browser API requests to `/api/` are forwarded to the authenticated host service through its Unix socket. The dashboard and the Rclone app can be installed together; they use separate host ports.

## Host service

Set up and start the host `rclone rcd` service as described in the Rclone app's store description. It must create `/run/rclone/rc.sock` before this app starts. Keep `RCLONE_RC_USER` and `RCLONE_RC_PASS` configured on that service. The proxy reads the socket's group ID at startup so its Nginx worker can access the group-restricted socket.

When the dashboard opens, add a connection profile with the API URL `http://<host-ip>:5573/api/` and the host service's RC username and password. If opening the dashboard through a domain, use `https://<your-domain>/api/` instead. The URL must match the browser's scheme and host so requests stay on the same origin. Credentials are stored by the dashboard in your browser.

The dashboard's media preview and direct download features require `--rc-serve` and do not work with RC Basic Auth. Keep Basic Auth enabled for the host service; file management and transfer monitoring still work.

[Dashboard source and documentation](https://github.com/outlook84/yet-another-rclone-dashboard) · [Rclone RC documentation](https://rclone.org/rc/)
