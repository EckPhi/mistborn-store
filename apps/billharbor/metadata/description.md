# BillHarbor (Development)

BillHarbor acquires receipts and bills, preserves immutable originals, and tracks authenticated delivery. This entry packages **0.5.0.dev7**, with local user authentication, from commit `70c89632d03c9a60fe73706e98a07eab14f28d2f`. The image supports **AMD64 and ARM64**.

## Installation and sign-in

Expose the app through Runtipi on an **HTTPS domain**. Its public origin follows Runtipi's `APP_PROTOCOL` and `APP_DOMAIN` automatically. Runtipi terminates HTTPS; the container serves HTTP on port 8080. Direct HTTP port 8105 can serve readiness checks, but secure session cookies require browser access over HTTPS.

Enter an initial administrator username and a password of 15–1024 characters. No OIDC provider or client configuration is needed. Initialization creates the first local user only when no local users exist, grants it administrator access to tenant `default`, and approves it as a plugin administrator. Later starts preserve users, passwords and revoked grants. Use **App users** to manage users and permissions and **Your password** to change your password; changing install-form credentials does not reset an existing user.

For an initial password containing `$`, pre-create `secrets/bootstrap-password` under the app-data directory with the exact password, owned by UID/GID 10001 and mode 0600. Enter a placeholder of at least 15 characters in the required form field. The protected file takes precedence during bootstrap; remove it after successful initialization. Passwords are stored as salted scrypt verifiers in SQLite.

## Configuration and persistence

Initialization creates `config/service.json` and `secrets/credential-key`, fixes bind-mount ownership for UID/GID 10001, and provisions state. The initialization sidecar stays running so Runtipi can gate startup on its health. Existing configurations retain their account/destination policies and encryption keys; this package sets authentication to `local` and synchronizes the public origin at each start. Upgrading an OIDC-only installation creates the first local administrator using the new form credentials. Existing OIDC users can no longer sign in through this package.

Stop the app before deliberately editing `config/service.json` for accounts, tenant grants, destinations and plugin policies. Apply intentional account/grant changes with `billharbor-service --config /config/service.json provision` as UID 10001 in the API container. Startup does not restore revoked grants. Local users are managed in the UI; local-user administration and plugin trust permissions are separate.

Back up `state` (SQLite, password verifiers and original documents), `config`, the generated encryption form value and `secrets`. Keep a separately protected backup of the 32-byte encryption key: losing it makes stored vendor credentials unreadable. Changing the form key does not rotate existing credentials; use upstream's explicit key-rotation procedure. Take consistent SQLite backups with the app stopped or SQLite's backup API.

## Development scope

The app starts with **zero vendors and accounts**. Configure trusted plugin stores and reviewed immutable plugins in the UI; account/destination provisioning remains deployment configuration. See [plugin operations](https://github.com/EckPhi/billharbor/blob/v0.5.0.dev7/docs/operations/plugin-stores.md) and [local-user operations](https://github.com/EckPhi/billharbor/blob/v0.5.0.dev7/docs/operations/local-users.md).

The acquisition worker runs without network access for offline development fixtures. No delivery sender is started. Live vendor acquisition and delivery require separate upstream acceptance and deployment configuration. This is a development build, not an accepted production deployment.
