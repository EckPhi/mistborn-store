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
Runtipi generates the domain route and maps host port 8104 for the main service;
the container listens on 8080. No additional port mapping is needed. If direct
host-port access must be unavailable, verify or override that generated Runtipi
mapping rather than relying only on the absence of a Compose `ports` entry.

The application requires its own login for UI, API and PDF routes; future Traefik
OAuth is an additional layer. On the first authenticated-runtime startup it creates
the `admin` operator and prints a random initial password once in the container
startup log. A restart-safe copy remains at `/data/initial-admin-password` inside
the container with mode 0600 until replacement. Save the password in a password
manager and sign in as `admin`; the application requires a new password before it
allows workspace or API access and then removes the bootstrap files. Forwarded
identity headers are ignored.

Browser login supports standard password-manager autocomplete. Signed-in users
can generate revocable read or operate API keys; plaintext is shown once and only
the hash is stored. Every application user currently shares the same operator
role and workspace. Only the loopback container health probe bypasses login.

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
