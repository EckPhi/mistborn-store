# Termix Server

Termix is a self-hosted server management platform. Connect to your servers through an SSH terminal, manage files, monitor host metrics and enable additional features through plugins. Use the browser interface or connect the Termix desktop and mobile apps to this server.

## First start

Open Termix from Runtipi or visit `http://<host-ip>:8106`. Create your account: the first registered user becomes the administrator. Follow the workspace setup, choose your plugins, then add a host with its address, SSH port and credentials.

Before exposing Termix on a domain, create the administrator account, use HTTPS through Runtipi, and review **Settings → General → Allow User Registration**. Disable registration if you intend to create accounts yourself.

## Data and backups

The database, encryption keys, installed plugins, uploads and recordings persist in `${APP_DATA_DIR}/data`, mounted at `/app/data`. Back up this entire directory together; losing the encryption keys can make saved credentials unusable. Stop the app before making a consistent filesystem backup and back up before upgrading.

The upstream entrypoint initializes permissions and runs the application as UID/GID 1000. No external database is required; this installation uses the default SQLite database. Additional plugins may require their own configuration or services; remote desktop configuration is described in the upstream documentation.

## Documentation

- [Docker installation](https://docs.termix.site/install/server/docker/)
- [First-run setup](https://docs.termix.site/install/first-run/)
- [Source and releases](https://github.com/Termix-SSH/Termix)
