# Kometa Quickstart

Kometa Quickstart is the Kometa team's guided web interface for configuring Plex collections, poster overlays, playlists, and metadata automation. It validates service connections, manages configuration profiles, generates YAML, and provides Kometa run controls and logs.

## Getting started

1. Install the app and click **Open**, or visit `http://<runtipi-host-ip>:8199`.
2. Follow the guided setup to connect your Plex server and enter your TMDb API key. Use a Plex address reachable from the container, such as your server's LAN IP; `localhost` refers to the Quickstart container.
3. Select your libraries, collections, and overlays, then resolve any validation tasks.
4. Use Quickstart's **managed** Kometa runtime. On the Kometa page, install the runtime and use the run controls to start and monitor it. The initial setup needs internet access to download Kometa and its dependencies.

Run timing and flags are configured through Quickstart's Kometa command builder. This package does not start a separate daily Kometa scheduler. Check the displayed command before starting a run, and check runtime status after restarting the app; do not assume a previously running job resumes automatically.

## Persistent data and updates

The entire Quickstart workspace is stored at `${APP_DATA_DIR}/quickstart`, mounted at `/config`. It contains configuration profiles, the database, generated YAML, managed runtimes, assets, and logs. Back up this directory and keep its service credentials private.

The pinned store image version is **Quickstart's version**. Quickstart installs and updates its managed Kometa runtime separately through the UI. Update the Quickstart container through Runtipi.

If you previously prepared a standalone Kometa configuration at `${APP_DATA_DIR}/config/config.yml`, it remains untouched. Import that YAML through Quickstart's configuration import flow and review the import preview. Quickstart's `/config` is its own workspace, not a standalone Kometa configuration directory.

## Access and prerequisites

Use Runtipi's domain exposure settings to access Quickstart through its reverse proxy. Protect remote access with authentication or a VPN: the interface provides access to service credentials and run controls. Keep the internal web port at **7171** so Runtipi's routing continues to work.

Plex and a TMDb API key are required and are not installed by this app. Review your selected collection and overlay rules before running Kometa against your library.

See the [Quickstart guide](https://kometa.wiki/en/latest/kometa/scripts/quickstart/) and [upstream project](https://github.com/Kometa-Team/Quickstart) for configuration and runtime details.
