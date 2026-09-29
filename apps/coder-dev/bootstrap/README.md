# Bootstrap lifecycle

`server.sh` uses the upstream Alpine image's group tools and BusyBox `su`.
It resolves the socket's actual GID, grants UID 1000 membership, prepares the
persistent home and copies the matching static Coder CLI to `/runtime/bin`.
It then replaces itself with an unprivileged Coder server. No package installs
or socket permission changes occur during server startup.

`bootstrap.py` runs as UID 1000 in the pinned Python helper. PostgreSQL health
gates Coder startup; Coder health gates bootstrap. The supported first-user API
creates an administrator only on HTTP 404. Other HTTP errors never trigger
creation. It authenticates, discovers the organization, invokes `templates push`
with a content-derived version name and creates the default workspace once.
The initial agent must connect before successful setup is recorded.

The mode-0600 atomic state file stores the identity, session token, template
fingerprint, default workspace ID/name and completion state. A crash releases
an advisory file lock. Initial build failures can be retried; completed
workspaces are left alone, including stopped/deleted ones. Changing a password
in the UI requires updating the installer credential after token expiry.

Both successful helper services stay alive, so RunTipi's restart policy cannot
create an init-container restart loop. Health is recorded only after the work
succeeds. Errors stop bootstrap with a non-secret diagnostic and can be retried
by restarting the app. CLI/API response details are inspected in Coder, not
echoed into potentially public installation logs.

Generate the bundled Compose archive with `python3 scripts/coder-dev/package.py`
after editing these files. Do not edit the base64 archive directly.

`lifecycle.py` supplies the equivalent of pre-stop/post-start handling through
Docker SIGTERM and dependency ordering. The bootstrap service has five minutes
to stop running Coder workspaces, journaling their IDs and template versions
before issuing any stop. The journal survives recreation and backups. Startup
resumes that set only; subsequent checks remove entries once running. Deleted
workspaces and later user/scheduler stops are respected. A failed/forced stop
cannot prevent RunTipi's backup, so logs explicitly require manual verification.
This path is scenario tested; live Docker shutdown/backup behavior is pending.
