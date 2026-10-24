# BillHarbor (Development)

BillHarbor acquires receipts and bills, preserves immutable originals, and tracks authenticated delivery. This entry packages **0.5.0a21001**, from source `41720d1cc6941d74fae3532b08c8a8f42348abc5`, with local user authentication and application-managed first-run setup. The image supports **AMD64 and ARM64**.

## Installation and sign-in

Expose the app through Runtipi on an **HTTPS domain**. Its public origin follows Runtipi's `APP_PROTOCOL` and `APP_DOMAIN` automatically. Runtipi terminates HTTPS; the container serves HTTP on port 8080. Direct HTTP port 8105 can serve readiness checks, but secure session cookies require browser access over HTTPS.

BillHarbor generates a private temporary **Deployment setup token** at startup. Copy it from the main `billharbor` container's server logs into BillHarbor's welcome-screen token field. Runtipi has no setup-token install field. Keep server logs private while setup is pending. Choose **Get started**, create the first administrator (password: 15–1024 characters), download the encryption-key backup, store it separately, and confirm custody to finish. The administrator becomes usable only after completion. Administrator names and passwords are entered directly into BillHarbor, without Compose environment interpolation.

Setup progress survives normal restarts, but the temporary token rotates after the main API fully restarts. Use the current token from its latest startup logs to resume. The token is discarded when setup finishes and is not an administrator login credential. The acquisition worker waits until setup finishes and can appear unhealthy while waiting. Existing installations retain their users, passwords, policies and original keys; this update never creates a replacement administrator or key. Use **App users** and **Your password** for later user management.

## Configuration and persistence

For fresh installs, initialization creates `config/service.json` and the durable installation marker. The main API keeps its temporary claim in its private runtime directory, outside durable state and encryption-key storage. The UI generates `secrets/credential-key` only when requested during setup. The initialization sidecar stays running so Runtipi can gate startup on its health. It prepares the installation before API processes or the worker can race to create state. The API has writable access to the protected secrets directory for managed key creation/recovery; the worker retains read-only access.

Existing authentication and account/destination policies are preserved; the public origin is synchronized and the obsolete `setup.token_file` override is removed so the main app owns startup claims. Other setup policies are retained, and any old protected `secrets/installation-token` file is left untouched but unused. Missing deployment configuration with existing state/secrets, missing databases, and conflicting installation state fail closed and require deployment recovery. An interruption during initial configuration or installation-marker creation can also require operator review before retrying. Never delete existing state, keys or installation markers to bypass these checks. OIDC-only deployments retain their existing OIDC configuration and separate deployment requirements.

Use **Account setup** to create vendor accounts from installed plugins and choose download-only operation or an optional HTTPS destination. Select self-access explicitly when creating an account. Local user administrators can manage setup; plugin trust permissions remain separate. UI settings are stored in SQLite, survive restarts and supersede deployment seeds. Startup does not restore revoked grants. Advanced deployment configuration and plugin trust policy remain in `config/service.json`; stop the app before editing that file.

Back up `state` (SQLite, password verifiers and original documents), `config`, `secrets` (key and installation marker; older installations may also retain an unused legacy token). Keep a separately protected backup of the 32-byte encryption key: losing it makes stored vendor credentials unreadable. Use upstream's explicit key-rotation procedure to rotate existing credentials. Before rotation, stage both old and new keys in both configurations; retain old keys for historical callback revisions. Older images do not support UI-created accounts or encrypted callback tokens, so rollback requires a compatible database/key backup. Take consistent SQLite backups with the app stopped or SQLite's backup API.

## Development scope

The app starts with **zero vendors and accounts**. Configure trusted plugin stores and reviewed immutable plugins in the UI, then create accounts and optional destinations through **Account setup**. Download-only operation does not require a receiver. See [plugin operations](https://github.com/EckPhi/billharbor/blob/v0.5.0a21001/docs/operations/plugin-stores.md), [UI setup](https://github.com/EckPhi/billharbor/blob/v0.5.0a21001/docs/operations/ui-setup.md) and [local-user operations](https://github.com/EckPhi/billharbor/blob/v0.5.0a21001/docs/operations/local-users.md).

The acquisition worker runs without network access for offline development fixtures. No delivery sender is started. Live vendor acquisition and delivery require separate upstream acceptance and deployment configuration. This is a development build, not an accepted production deployment.

## Web UI and live debugging

The React/TypeScript/Vite assets are built into the image. No Node runtime, npm install or separate frontend service is needed. UI and API share the same HTTPS origin through Runtipi, with the public origin derived automatically. Hash navigation such as `/#/collections` requires no SPA fallback configuration. Keep the application's cookies, CSRF checks, security headers and `Cache-Control: no-store` responses intact.

Live debugging is opt-in, read-only and currently synthetic-only. It uses authenticated HTTP polling and JPEG responses through the main API; no WebSocket, VNC or debugging port is exposed. Browser feeds require connector instrumentation. Frames and action logs are ephemeral and are not persisted.

API and acquisition worker share the same writable `state` mount and UID/GID 10001:10001. The ephemeral debug broker uses a private Unix socket in this directory, including when the worker has no network access. Keep this shared mount writable and preserve the existing configuration and separate encryption-key mounts.

## Credential recovery

Updates preserve the existing encrypted state and separate key files. Restore matching key bytes from backup; never regenerate a key to resolve a missing-key or integrity error. Keep the secrets directory owned by UID/GID 10001:10001 with mode 0700 and key/token files mode 0400 or 0600. Retain read-only secret access on the worker; the API needs directory write access for managed recovery.

After restoring a backup, run `billharbor-service --config /config/service.json check --verify-stored` as UID 10001 in an isolated restore before resuming work. This verifies all stored vendor and callback credential revisions and reports counts without printing secrets or making vendor/callback requests. A valid-length key can still contain the wrong bytes, so ordinary `check` is insufficient for restore verification. See [upstream restore guidance](https://github.com/EckPhi/billharbor/blob/v0.5.0a21001/docs/operations/service-candidate.md#restored-secret-file-permissions-and-updates).

See [first-run installation and recovery](https://github.com/EckPhi/billharbor/blob/v0.5.0a21001/docs/operations/installation.md) for setup-token handling, backup custody and rollback. BillHarbor 0.5.0a21001 is maintained upstream by EckPhi under Apache-2.0. No library or service is added; the image reuses the upstream locked dependency/license inventory. Data remains in the existing state mount and separately protected secrets directory. Before updating, retain matching state, configuration and separately protected keys for rollback; restoring the old configuration is necessary if returning to an image requiring an explicit setup token. Rollback requires the original matching state and separately protected keys; complete setup before using an older CLI-only image.
