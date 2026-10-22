# BillHarbor (Development)

BillHarbor acquires receipts and bills, preserves immutable originals, and tracks authenticated delivery. This entry packages **0.5.0.dev8**, with local user authentication, from commit `caf5bd5d4cbce618feab18bf5a13583c1ba80c5a`. The image supports **AMD64 and ARM64**.

## Installation and sign-in

Expose the app through Runtipi on an **HTTPS domain**. Its public origin follows Runtipi's `APP_PROTOCOL` and `APP_DOMAIN` automatically. Runtipi terminates HTTPS; the container serves HTTP on port 8080. Direct HTTP port 8105 can serve readiness checks, but secure session cookies require browser access over HTTPS.

Enter an initial administrator username and a password of 15–1024 characters. No OIDC provider or client configuration is needed. Initialization creates the first local user only when no local users exist, grants it administrator access to tenant `default`, and approves it as a plugin administrator. Later starts preserve users, passwords and revoked grants. Use **App users** to manage users and permissions and **Your password** to change your password; changing install-form credentials does not reset an existing user.

For an initial password containing `$`, pre-create `secrets/bootstrap-password` under the app-data directory with the exact password, owned by UID/GID 10001 and mode 0600. Enter a placeholder of at least 15 characters in the required form field. The protected file takes precedence during bootstrap; remove it after successful initialization. Passwords are stored as salted scrypt verifiers in SQLite.

## Configuration and persistence

Initialization creates `config/service.json` and `secrets/credential-key`, fixes bind-mount ownership for UID/GID 10001, and provisions state. The initialization sidecar stays running so Runtipi can gate startup on its health. Existing configurations retain their account/destination policies and encryption keys; this package sets authentication to `local` and synchronizes the public origin at each start. Upgrading an OIDC-only installation creates the first local administrator using the new form credentials. Existing OIDC users can no longer sign in through this package.

Use **Account setup** to create vendor accounts from installed plugins and choose download-only operation or an optional HTTPS destination. Select self-access explicitly when creating an account. Local user administrators can manage setup; plugin trust permissions remain separate. UI settings are stored in SQLite, survive restarts and supersede deployment seeds. Startup does not restore revoked grants. Advanced deployment configuration and plugin trust policy remain in `config/service.json`; stop the app before editing that file.

Back up `state` (SQLite, password verifiers and original documents), `config`, the generated encryption form value and `secrets`. Keep a separately protected backup of the 32-byte encryption key: losing it makes stored vendor credentials unreadable. Changing the form key does not rotate existing credentials; use upstream's explicit key-rotation procedure. Before rotation, stage both old and new keys in both configurations; retain old keys for historical callback revisions. Older images do not support UI-created accounts or encrypted callback tokens, so rollback requires a compatible database/key backup. Take consistent SQLite backups with the app stopped or SQLite's backup API.

## Development scope

The app starts with **zero vendors and accounts**. Configure trusted plugin stores and reviewed immutable plugins in the UI, then create accounts and optional destinations through **Account setup**. Download-only operation does not require a receiver. See [plugin operations](https://github.com/EckPhi/billharbor/blob/v0.5.0.dev8/docs/operations/plugin-stores.md), [UI setup](https://github.com/EckPhi/billharbor/blob/v0.5.0.dev8/docs/operations/ui-setup.md) and [local-user operations](https://github.com/EckPhi/billharbor/blob/v0.5.0.dev8/docs/operations/local-users.md).

The acquisition worker runs without network access for offline development fixtures. No delivery sender is started. Live vendor acquisition and delivery require separate upstream acceptance and deployment configuration. This is a development build, not an accepted production deployment.
