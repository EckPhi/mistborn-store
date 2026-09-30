# Arcane

Arcane is a self-hosted Docker management interface. Manage containers, Compose projects, images, volumes and networks; inspect logs, open container terminals and monitor resource usage from your browser.

## First start

Requires Runtipi 4.10.1 or newer. Open `http://<host-ip>:3552`, or expose Arcane through a Runtipi domain. Set **Application URL** to the exact browser origin, including scheme and port (for example `http://192.168.1.10:3552` or `https://arcane.example.com`). The localhost default is only appropriate when browsing on the server itself.

Sign in with username `arcane` and password `arcane-admin`, then change the password when prompted. Reverse proxies must support WebSockets for live updates; use Runtipi's generated routing.

## Storage and projects

The database, settings and application data persist in `${APP_DATA_DIR}/data`, mounted at `/app/data`. Arcane prepares directory ownership at startup, then runs as UID/GID `1000:1000` and acquires access to the Docker socket's group.

New Compose projects live in `${APP_DATA_DIR}/data/projects`. That directory is also mounted at its identical absolute host path inside Arcane, and `PROJECTS_DIRECTORY` points there so relative bind mounts resolve correctly on the Docker host. Other existing project directories require additional mounts at identical absolute host/container paths before Arcane can edit their Compose files. Existing host containers remain visible through Docker.

Back up app-data and the generated **Encryption key** together. Do not change or regenerate the key on an existing installation: stored encrypted credentials depend on it. Stop Arcane before copying its SQLite database for a consistent backup.

## Docker access and updates

Arcane has read/write access to `/var/run/docker.sock`, giving it administrative control over the host's Docker engine, including Runtipi containers. Only grant access to trusted administrators. Keep Runtipi-managed application updates and Compose changes in Runtipi; changing them in Arcane can conflict with Runtipi's generated configuration. Update Arcane itself through the store rather than its self-update action.

[Installation documentation](https://getarcane.app/docs/get-started/installation) · [Source code](https://github.com/getarcaneapp/arcane)
