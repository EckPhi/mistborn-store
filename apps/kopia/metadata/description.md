# Kopia Workspace Backups

Encrypted, deduplicated Coder workspace backups with a dedicated Kopia web UI.
Install **Coder Development Environment** first: this app requires its existing
`coder-dev-workspaces` named volume on the same Docker host. It reads workspace
home/source at `/data/workspaces` **read-only**. Workspace caches and the Docker
socket are not mounted.

Expose this app as `kopia.example.com` using RunTipi, and leave Coder at
`coder.example.com`. Log in as **kopia** with the web UI password. The server uses
HTTP behind RunTipi's HTTPS proxy; direct LAN access uses port **51515**. Use HTTPS
for remote access. Coder does not support `/coder` subpath hosting.

## First backup

1. Create or connect a remote repository in the UI, using the repository password
   supplied at installation. Keep a separate, secure copy of that password.
2. Add `/data/workspaces` as a snapshot source, set a schedule and retention policy,
   then create a snapshot. Installation alone does not create a repository or schedule.
3. Restore a sample into `/restore` and verify the files before relying on backups.

Running workspaces can change during a snapshot. For a consistent backup, stop
workspaces in Coder, run and verify the snapshot, then start them again. Kopia does
not stop workspaces automatically. Back up Coder's control plane with RunTipi too;
workspace files alone do not restore users, templates or Terraform state.

## rclone

The pinned official image includes rclone; no custom image or separate rclone
app is needed. Put `rclone.conf` in this app's `${APP_DATA_DIR}/rclone/` directory,
or use `rclone config` inside the container. The configuration is writable so
OAuth token refresh can persist. Use a dedicated remote directory for the repository.
For CLI setup and recovery commands, see the [operator guide](https://github.com/EckPhi/mistborn-store/blob/main/apps/kopia/README.md).
Kopia labels its rclone backend **not maintained**; prefer a native storage backend
such as S3 when your destination supports one.

## Storage and restore

RunTipi backs up this app's repository connection, rclone credentials and logs.
Repository contents live on the remote. Local cache and `/restore` use separate
named volumes and are excluded from app-data backups. Treat config backups as
secret-bearing. Source is deliberately read-only: recover to `/restore`, then
copy verified files into a stopped workspace from the host. Do not prune Coder's
workspace volume or uninstall it with volume deletion before recovery is verified.
