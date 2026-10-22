# Kopia for Coder workspaces

Install `coder-dev` first on the same Docker host. This app requires the existing
external `coder-dev-workspaces` volume and never creates an empty replacement.
Use RunTipi to expose Coder at `coder.example.com` and this app at
`kopia.example.com`. RunTipi supplies the HTTPS reverse proxy for each app; no
additional proxy service is necessary. Coder cannot be hosted under `/coder`.

The web UI login is `kopia` with the installation password. Kopia listens on
HTTP internally (`--insecure`), with authentication and CSRF checks enabled.
Use the RunTipi HTTPS domain for remote access. Direct HTTP access is port 51515.

## Configure storage and scheduling

Use the UI to create/connect a remote repository with the installation's
repository encryption password. Save that password separately from the host.
Nothing is uploaded until you configure a repository and snapshot source.

Create a snapshot source at `/data/workspaces`, configure a schedule (for example
hourly), and retention (for example 24 hourly, 7 daily, 4 weekly). This includes
all retained UUID directories, including deleted Coder workspaces, and Git
metadata, ignored files and secrets unless you explicitly exclude them. The
separate `coder-dev-caches` volume is never mounted. Kopia does not reproduce the
old helper's Git-aware filtering. Configure exclusions deliberately; keep local
`.env` files and credentials if they are required for recovery.

Running workspaces may change while being read. For consistent recovery points,
stop workspaces in Coder, take and verify a Kopia snapshot, then start workspaces.
Scheduled live snapshots are best effort, not filesystem-atomic snapshots.
Kopia has no Docker socket and does not automate workspace stop/start.
Use RunTipi backups for the Coder database, configuration and bootstrap state.
Record matching control-plane and workspace backup times for disaster recovery.

## rclone

The official pinned image already ships `/bin/rclone` and uses
`RCLONE_CONFIG=/app/rclone/rclone.conf`. No image modifications, privileged mode,
FUSE mounts or separately installed rclone app are required for this backend.
Kopia marks the rclone backend **not maintained**. Prefer a native backend when
available; test snapshot and recovery with your chosen remote.

Put your config at `${APP_DATA_DIR}/rclone/rclone.conf` for the **Kopia** app.
This directory stays writable for OAuth refresh. Protect it as a credential.
It is independent of any existing rclone app's config: copy the relevant remote
and keep credentials current, or configure it interactively in this container.

From the Kopia app's Compose directory (or substitute its container name with
`docker exec`), run:

```sh
docker compose exec kopia rclone config
docker compose exec kopia rclone listremotes
# Use a dedicated, empty remote directory for a NEW repository:
docker compose exec kopia kopia repository create rclone --remote-path=myremote:coder-backups
# For an EXISTING repository, use connect instead of create:
docker compose exec kopia kopia repository connect rclone --remote-path=myremote:coder-backups
```

The CLI inherits `KOPIA_PASSWORD` from the installation field. Restart the Kopia
app after a CLI repository change so the running server uses the connection.
Do not change the repository via CLI while snapshots or maintenance are running.
The UI can also create/connect supported backends.

For CLI policy setup after connecting:

```sh
docker compose exec kopia kopia policy set /data/workspaces --snapshot-interval=1h --keep-hourly=24 --keep-daily=7 --keep-weekly=4 --ignore-unknown-types=true
docker compose exec kopia kopia snapshot create /data/workspaces
docker compose exec kopia kopia snapshot list /data/workspaces
```

Check the UI shows successful snapshots and future scheduled runs. Keep the
stable hostname `coder-workspace-backup`: policies and sources include identity.

## Recover files

The shared source volume is read-only in Kopia. Restore a snapshot or selected
files into `/restore` using the UI or `kopia snapshot restore <snapshot-id> /restore/recovery`.
The restore directory uses a separate named volume, excluded from RunTipi
app-data backups. Copy recovered files out with `docker compose cp
kopia:/restore/recovery /safe/recovery`, inspect them, then copy into the correct
`coder-dev-workspaces/<uuid>/home` or `source` directory while that workspace is
stopped. Preserve ownership (Coder uid/gid 1000:1000) and symlinks. Restore into a
new directory first; do not overwrite a live workspace.

For full recovery restore matching Coder PostgreSQL/bootstrap state too. Restore
the original UUID layout before starting workspaces. Rehearse this on a separate
host; a file recovery test alone does not validate Coder disaster recovery.

RunTipi backs up Kopia's `config/`, `rclone/` and `logs/`, including credentials.
It does not back up the remote repository, the source volume, Kopia cache or
restore staging. Export repository credentials/password independently. Never
store a local repository inside app-data: it would enter RunTipi backups again.

## Existing Coder installations

Updating Coder disables the old shutdown file-copy snapshots, and removes its
bootstrap binds for legacy workspaces and snapshots. It retains graceful
workspace stop/resume. Existing files are not deleted or relocated automatically.
After verifying named-volume migration and a Kopia recovery, stop Coder and move
old `${APP_DATA_DIR}/snapshots`, `workspaces` and `caches` directories outside
Coder app-data. Keep them until recovery is verified. Older workspace templates
may still depend on the legacy bind paths: migrate every workspace first. The
offline storage initializer retains read-only legacy access solely for migration;
workspace containers use named-volume subpaths. RunTipi will keep including old
files until you move them; removing a Compose mount does not remove host data.
