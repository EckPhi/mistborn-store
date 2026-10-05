# Coder Development Environment

A remote development appliance for trusted users: Coder, PostgreSQL, a default
general, Python, Rust and Flutter templates and an automatically created `dev`
workspace. Flutter web/Linux development requires an AMD64 host; Android SDK
setup is separate, and iOS/macOS builds require a Mac.
Enter administrator username, email and password during installation. The
initial workspace image builds on first setup, so allow several minutes for
package downloads. Clean-host acceptance is pending manual installation.

Connect VS Code, Cursor, JetBrains or `coder ssh dev`; open `/workspaces`, clone a
repository, build and test remotely. Git/LFS, GCC/Clang, CMake/Ninja, debuggers,
Python/uv, Node/npm/pnpm, Conan, Docker CLI/Compose and ccache are included.
Sources, home/configuration and caches survive workspace recreation.

Create additional workspaces from `python-development` (Python 3.13, uv,
Poetry), `rust-development` (Rust 1.97.1, Clippy, rust-analyzer, WASI), or
`flutter-development` (Flutter 3.47.3/Dart, web/Linux tooling). Only `dev` is
created automatically. See the [project migration guide](https://github.com/EckPhi/mistborn-store/blob/main/apps/coder-dev/MIGRATION.md).

**Docker socket access gives approximately administrative control over the host.**
Coder needs it to provision workspaces. Workspaces never receive it. New workspaces enable an isolated rootless Docker
sidecar by default; each privileged sidecar requires host user-namespace support. This
app is for personal servers and trusted teams, not hostile-user isolation.
PostgreSQL is not published; Coder runs as UID 1000 after automatic permission
setup. No public workspace SSH port is needed.

RunTipi supplies the Coder URL automatically. Both your IDE and workspace agents
must reach it. Use the optional URL override for a different LAN or Tailscale
address (including port), or a RunTipi HTTPS domain. Never use localhost. Direct
host access uses port **8096**. Tailscale runs on the host separately.

Restarts never reset the administrator or recreate a deleted initial workspace.
Template updates do not automatically update existing workspaces. Deleting a
Coder workspace retains its source/home on disk; deleting RunTipi app-data can
remove that data. Keep the generated database password unchanged. After changing
the Coder administrator password, update the installer credential so bootstrap
can sign in when its saved session expires.

Back up PostgreSQL, Coder/bootstrap state and workspace source/home together.
Graceful app shutdown records and stops running workspaces via Coder; startup
resumes only that set. Verify shutdown completion before a backup/restore. A
forced shutdown or hook failure requires stopping workspaces manually. Native backups include caches;
selective backups may omit caches and reproducible builds. Treat archives as
secret-bearing. See the [full installation, IDE, backup and troubleshooting guide](https://github.com/EckPhi/mistborn-store/blob/main/apps/coder-dev/README.md).

## Modular agent and tracking integrations

The workspace image now includes pinned OpenCode and Omnigent CLI tools alongside Codex, Claude Code and tmux. Optional template URLs connect to separately installed Omnigent/MLflow apps through network interfaces. Login remains user-controlled. The rootless Docker sidecar defaults on for new workspaces and requires a privileged container. Compose bind mounts in home/source/cache and workspace-local published ports are supported. Docker data survives stop/start and is discarded on workspace deletion or Docker disable. Existing workspace parameters are retained; update the template and enable Docker explicitly if previously disabled. Workspace host-socket access has been removed. Live acceptance for these additions is pending. See the repository platform guide for backup and security boundaries.
