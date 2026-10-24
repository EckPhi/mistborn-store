# Runtipi Store TUI

A local Rust terminal UI for maintaining this app store. It reads the checkout,
uses the repository's existing Bun/Ajv validators, and writes ordinary app files.
No server, browser, Docker socket or account token is required.

## Run

Install a current stable Rust toolchain, Git, and Bun. In the store checkout:

```sh
bun install
bun run tui
```

Or install the executable locally:

```sh
cargo install --path tools/store-tui --locked
runtipi-store-tui --root /path/to/mistborn-store
```

The installed binary embeds its small Bun bridge; it loads schemas, Compose
validation, tests and the README generator from the selected checkout. That
checkout still needs `bun install`. `--root` accepts a checkout or a directory
inside it. Plain output is also available:

```sh
runtipi-store-tui --root /path/to/mistborn-store --list
```

## Controls

| Key | Action |
| --- | --- |
| ↑/↓ or j/k | Select an app, service or tag |
| / | Filter apps by id or display name; Enter keeps the filter, Esc clears |
| Enter / i | Show the selected app's services; Enter fetches tags |
| u | Fetch tags for the main service image |
| m, in tag selection | Enter a published tag not in the fetched list |
| n | Create a simple app with the guided form |
| e | Edit metadata, port and categories |
| o | Import and preview an upstream icon |
| Tab / Shift-Tab / ↑ / ↓, in forms | Select a field |
| Type / Backspace / Ctrl-U | Append text / erase character / clear field |
| Enter, in forms | Validate and preview a draft |
| a, in review | Apply the reviewed files and regenerate README |
| v | Run the full repository test suite |
| d | Show the working diff |
| c | Run the full tests and commit this session's applied changes |
| r | Reload app metadata |
| Esc | Cancel an unapplied draft or return to the app list |
| q / Ctrl-C | Quit; already applied files remain on disk |

Network and validation work runs in a background thread with a visible status.
Keys are disabled while work is running so an apply/commit cannot be interrupted
halfway by quitting the UI. Errors appear in the status area; form values remain
available for correction. Normal exit, errors and Rust panics restore the terminal.

## Updating an image

The tag selector supports **public Docker Hub and GHCR** repositories. Docker Hub
lists up to 100 recently updated tags; enter another tag with `m`. GHCR uses its
registry tag listing. No private-registry credentials are read. Requests have a
30-second timeout. Rolling tags such as `latest` and floating major/minor tags
are rejected; choose a release or immutable build tag.

Before a draft is offered, the TUI checks the selected tag and every resulting
service image in the registry, and computes their shared Linux AMD64/ARM64
support. It updates every service using the *same complete old image reference*,
so an API, worker and init container stay together. Other images are retained.
Updating the main image synchronizes `config.version`; a backing-image-only
change leaves the application's version alone. Every change increments
`tipi_version` once and refreshes `updated_at`.

Legacy JSON keeps environment arrays. YAML edits change only image scalar nodes
and preserve comments and deployment options. Architecture overrides, YAML
aliases/merges and interpolated/digest references require manual editing.
Generated Coder, MLflow and Omnigent deployments require their maintained
packaging scripts; the TUI refuses direct image updates for these apps.

Registry checks verify that tags and platforms exist. They do **not** establish
upstream source provenance or runtime compatibility. Review upstream release
notes, migrations, image configuration and application-specific deployment
requirements before applying an update. The TUI neither pulls nor runs containers.

## Creating an app and importing icons

The new-app form creates a native YAML Compose definition with one main HTTP
service, a unique host port, optional persistent data mount, metadata and a JPEG
logo. The image must have a published version tag. Use an upstream **HTTPS raster
icon URL** or local PNG/JPEG/WebP/ICO file. Icons are limited to 10 MiB and 8192-pixel
dimensions, resized to 460×460, flattened onto white and encoded as JPEG. Review
the color icon thumbnail before applying it. Convert SVG to PNG beforehand.

This creates a simple deployment, not an automatic GitHub/Dockerfile importer.
It does not infer the upstream service port, permissions, non-root UID, database,
secret fields, initialization, health checks or additional services. Review these
against AGENTS.md and upstream deployment instructions. Complex Compose edits,
install fields, long Markdown documentation and GitHub release analysis remain
manual in this first version. The metadata editor preserves fields it does not
expose, including existing install fields.

## File and commit behavior

Planning starts only from a clean Git checkout. Unapplied drafts stay in memory;
validation uses a temporary directory. Applying rechecks the original bytes,
validates again, writes files, and invokes the existing README generator. A
normal apply failure restores original app files and README. Files are replaced
atomically individually; abrupt process/system termination is not a transaction
across all files. Use Git to inspect and restore any partial apply after a crash.
Symlinked app files are refused.

Committing is explicit. It requires no pre-existing staged changes, verifies the
applied bytes have not changed, runs `bun run test`, and commits **only** the
reviewed paths. Unrelated files created after apply are not included. A failed
validation leaves changes uncommitted. There is no push, release publication,
container deployment, or automatic inclusion of other repository changes.

## Development

```sh
cargo fmt --manifest-path tools/store-tui/Cargo.toml --check
cargo clippy --manifest-path tools/store-tui/Cargo.toml --locked --all-targets -- -D warnings
cargo test --manifest-path tools/store-tui/Cargo.toml --locked
```

Tests use temporary Git repositories and the actual store validators to exercise
YAML/JSON updates, linked images, new-app creation, rollback, stale previews,
commit scoping, failed validation and symlink refusal. They make no network calls
and do not modify this checkout's apps.
