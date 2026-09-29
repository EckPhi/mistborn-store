# Coder Development Environment

A remote development appliance for trusted users: Coder, PostgreSQL, a default
`general-development` template and an automatically created `dev` workspace.
Enter administrator username, email and password during installation. The
initial workspace image builds on first setup, so allow several minutes for
package downloads. Clean-host acceptance is pending manual installation.

Connect VS Code, Cursor, JetBrains or `coder ssh dev`; open `/workspaces`, clone a
repository, build and test remotely. Git/LFS, GCC/Clang, CMake/Ninja, debuggers,
Python/uv, Node/npm/pnpm, Conan, Docker CLI/Compose and ccache are included.
Sources, home/configuration and caches survive workspace recreation.

**Docker socket access gives approximately administrative control over the host.**
Coder needs it to provision workspaces. Ordinary workspaces do not receive it
unless you explicitly enable their Host Docker socket access parameter. This
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
