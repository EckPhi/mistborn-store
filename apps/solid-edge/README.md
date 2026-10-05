# Experimental Solid Edge browser desktop for Runtipi

Target: Siemens Solid Edge Community 2026, version 2510, on amd64 Linux. **Compatibility is unverified.** This app distributes only a Linux desktop, Wine, and workflow helpers. No installer or Solid Edge binaries are available here. No image is published and no external instance is deployed by this app.

## Local build

Use an amd64 Linux host with Docker Engine and Compose v2. Reserve at least 40–60 GB free disk for the 5 GB archive, extracted installer, prefix, installed software, and build cache; increase this for projects. Start with 16 GB RAM and assess actual CAD workload needs.

From the mistborn-store checkout, first run `cd apps/solid-edge`.

```sh
docker build --platform linux/amd64 -t solid-edge-webtop:0.1.0 runtime
python3 -m unittest discover -s tests -v
bash tests/host-smoke.sh
```

The context is **only `runtime/`**, with an allowlist `.dockerignore`. Keep all private software outside the repository and build context. Base Webtop is fixed by an amd64 digest; Wine is Debian 10.0~repack-6; Debian dependency resolution uses a dated snapshot. The build has not run here; snapshot availability and package installation must be confirmed on your Docker host. No Winetricks downloads or speculative .NET/DXVK verbs run automatically.

For standalone use create `.env` locally (never commit it):

```dotenv
DESKTOP_USER=yourname
DESKTOP_PASSWORD=replace-with-a-long-unique-password
SE_STATE_DIR=/srv/private-solid-edge
PUID=1000
PGID=1000
```

```sh
mkdir -p /srv/private-solid-edge/config /srv/private-solid-edge/projects
docker compose -f compose.local.yml up -d
```

Access `https://localhost:3001/` on that host, or use an SSH tunnel. The direct endpoint uses a self-signed certificate. Mount directories must be owned by PUID/PGID. Installer and prefix paths are under `/config`; projects belong in `/projects` (Wine path `Z:\projects`).

## Runtipi installation

Build the local image on the **same Docker daemon used by Runtipi** before installing. This app uses `pull_policy: never` and `force_pull: false`; it intentionally has no public registry image. The `apps/solid-edge` folder uses current schema-2 YAML dynamic Compose and metadata. Solid Edge is part of [mistborn-store](https://github.com/EckPhi/mistborn-store). Add that repository URL in Runtipi Settings → App Stores, following the current custom store guide, or refresh the store if already configured. Runtipi must be at least 4.10.1 and support the documented schema-2 format; validate on your current release before use.

Install the app, enter a unique desktop username and password (minimum 16 characters), set the desktop user/group IDs to match your private host directories, and enable a TLS domain through Runtipi. Routing points to internal HTTP port 3000; Runtipi handles published ports and Traefik labels. HTTP is suitable only as the internal proxy hop. A secure HTTPS browser context is required for streaming. Do not use the generated plain HTTP LAN endpoint over an untrusted network. Prefer VPN access; Internet exposure additionally requires a robust proxy authentication layer. The desktop user has passwordless sudo inside the container. No Docker socket or privileged mode is configured.

Persistent host locations are `${APP_DATA_DIR}/config` and `${APP_DATA_DIR}/projects`. Find APP_DATA_DIR in Runtipi's generated app configuration; store paths include the store slug and can vary, so do not assume a universal directory.

## Bring your own installer

1. Obtain Solid Edge Community 2026 directly from [Siemens](https://solidedge.siemens.com/en/). Ensure your use complies with Siemens terms.
2. Archive the **entire extracted installer directory**, preserving its hierarchy. ZIP and tar/tar.gz/tar.bz2/tar.xz are supported; 7z is deliberately unsupported. Do not upload `setup.exe` alone. Keep `Solid Edge/setup.exe`, `Setup.ini`, `Siemens Solid Edge 2026.msi`, every CAB, `ISSetupPrerequisites`, and `LicenseFile/SELicense.lic`, plus every other supplied file.
3. Use the Selkies sidebar file transfer to upload the single archive. Files land in `/config/uploads`. Wait until transfer completes before selecting it. For ~5 GB, host copy is often more reliable: copy the complete directory into `${APP_DATA_DIR}/config/uploads/Your Installer Folder` (standalone: `/srv/private-solid-edge/config/uploads/`). Preserve permissions and ensure the desktop user can read it. Do not place it in the image context.
4. Click **Install Solid Edge**, choose Archive or Host folder, and select the source. Spaces and nested wrapper directories are supported. Exactly one structurally complete installer must be present. The validator cannot prove all CABs are present or correct without Siemens' manifest; compare your original download and preserve everything.
5. Preparation extracts into a new private `/config/installers/prepared-*` directory. Links, traversal, special files, duplicate paths and extraction above 30 GiB are rejected. Failed staging is removed. Preparation never starts setup. Confirm the separate start prompt to initialize the 64-bit Wine prefix, set Windows 11 mode, and run graphical `setup.exe` from its own directory. Review the installer terms, prerequisites, license and options yourself. No license acceptance or bypass is embedded.
6. Use **Launch Solid Edge** after installation. It searches for one `Siemens/**/Edge.exe` beneath the prefix's Program Files. If the actual layout differs, inspect it and adjust the helper after confirming the real installed path. Save project files to `/projects`.

All Wine operations use `/config/wine/solid-edge`; install and launch share a nonblocking lock. No installer runs at startup. Canceling the start prompt leaves the prepared files available; old prepared folders can be deleted manually when no installation is running. Boot only refreshes desktop shortcuts and directory ownership.

## Large uploads and proxy limits

Selkies file transfer is reused, with `FILE_MANAGER_PATH=/config/uploads`. Browser, WebSocket, proxy and storage limits still need testing with the actual 5 GB file. No promise of resumable transfer is made. Prefer a private host copy if a connection drops. ZIP must support ZIP64 for files over 4 GiB.

Allow WebSocket upgrades and long idle/read timeouts (for example 3600 seconds) at every proxy. For HTTP upload paths, permit more than the archive size (for example Nginx `client_max_body_size 8g`) and budget proxy buffering/temp storage; this setting alone does not change WebSocket frame/message limits. Check Traefik buffering `maxRequestBodyBytes`, CDN limits, WAF limits and any intermediate proxy. Avoid a CDN with a small upload cap. Keep HTTPS and auth enabled throughout transfer. No custom upload server bypasses the desktop's auth.

## GPU

CPU desktop rendering is the baseline. Optional Intel/AMD passthrough uses `/dev/dri:/dev/dri` under service `devices` in a Runtipi user Compose override; grant the container user the host render/video numeric groups via `group_add`. Confirm device permissions and `glxinfo -B` in the desktop. Do not add privileged mode to fix permissions. Webtop encoding acceleration does not establish Wine CAD rendering correctness. This pinned base predates the latest Selkies v2 documentation; verify GPU variables against its source before adding advanced options. Nvidia requires host drivers and NVIDIA Container Toolkit plus the matching Webtop instructions; GPU behavior and CAD rendering remain host validation tasks. See research notes for current guidance.

## Backups and updates

Stop the app and wait for Wine processes to exit, then back up the **whole config and projects directories**, preserving ownership. These backups contain private installer, license and installed program files; encrypt/access-control them and never publish them. Test restoration into a separate private directory. Wine registry and drive_c must stay together. Runtipi removal options may delete app data; inspect before confirming removal.

Runtime updates: stop the app, make a full backup, build a new local version tag from a reviewed base digest and package snapshot, update both Compose image references and app metadata version/tipi_version, and recreate. Keep the old local image. Wine upgrades can migrate prefixes; rollback may require restoring the backup, not just changing an image tag. Project and prefix mounts survive recreation by design; host smoke script checks markers across actual recreation. Do not run `docker compose down -v` or delete host data as an update procedure.

## Troubleshooting

Use **Solid Edge Logs** or inspect `/config/logs`; `docker logs` covers Webtop startup. Missing installer errors explain required structure. Zero candidates usually means an incomplete upload or wrong folder; multiple candidates require selecting a narrower directory. Extraction failures leave no prepared output; check space and archive integrity. Logs and installer-generated MSI logs may contain private paths or licensing details; redact before sharing.

For blank desktop, check HTTPS, auth, WebSocket proxying, 1 GB shared memory and host resources. Test direct localhost TLS first. For Wine prerequisites, review setup's actual messages; do not assume another CAD app's DLL recipe applies. Do not install random Microsoft runtimes or silently accept their licenses. Wine Mono/Gecko prompts and redistributable prerequisites may require user interaction and network access. An installer exit code is not proof of success.

Before claiming 2510 compatibility, use the real installer on an amd64 host and record install, licensing, launch, creating a part/sketch, editing, saving, reopening, assembly and graphics checks. Windows API, .NET/VC++ prerequisites, GPU/OpenGL behavior, licensing and installer bootstrap checks remain potential blockers. See [validation report](docs/validation.md) and [research](docs/research.md).
