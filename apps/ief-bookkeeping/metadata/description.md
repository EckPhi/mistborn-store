# IEF Bookkeeping

An independent bookkeeping workflow UI for one workspace. Configure reporting,
load fixed invented bank movements and PDFs, review exact building/payment-type
allocations, and prepare offline JSON exports or inspect disconnected pending work.
No accounting backend is required. This release supports synthetic evaluation;
it does not import real documents, connect to a bank, issue invoices, post entries,
reconcile payments or transmit accounting records.

## Installation and access

Requires Runtipi 4.10.1 or newer and an amd64 host. Set **Canonical application
origin** to the exact browser origin, without a trailing slash. Examples:

- Domain: `https://bookkeeping.example.com`
- Private LAN: `http://HOST:8104`, replacing HOST with the server hostname or IP

Use this one origin consistently. Change the setting when changing domain or port.
Runtipi generates the domain route and optional host port 8104; the container
listens on 8080. No additional port mapping is needed.

Authentication and TLS are owned by the deployment's external access layer.
The application provides no passwords or sign-in screen. Configure that layer
before exposing the app to untrusted users, covering UI, API and PDF routes, and
disable direct port access when using the authenticated domain. Every user who
can reach the app shares the same workflow permissions and workspace; there is
no individual user attribution. Forwarded identity headers are not a user system.

## Persistent state and recovery

`${APP_DATA_DIR}/data` contains `workflow.sqlite3`, its SQLite journal files when
present, and the `documents/` directory of immutable invented originals. An
idempotent one-shot helper gives this app-owned directory to UID/GID 1000 before
the non-root service starts. Do not mount shared directories here.

Back up the complete data directory and the Runtipi app configuration. Use the
project's verified snapshot/restore procedure, or stop the app before copying its
data directory. Copying only the SQLite file while it is running is insufficient.
Backups, retention, off-host storage and restore monitoring remain operator-owned.
Validate restores into a fresh directory before switching to them.

The `/api/health` endpoint reports local workflow health and intentionally reports
`production_ready=false`. A healthy container does not authorize real accounting
data or prove the external access and backup services. Preserve the prior image
and a verified pre-upgrade snapshot for rollback.
