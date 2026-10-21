# BillHarbor (Development)

BillHarbor acquires receipts and bills, preserves immutable originals, and tracks authenticated delivery. This entry packages the vendor-independent **0.5.0.dev3** development service from commit `de783fcb26d46d0a1cbcf518a1e8653452b4ff8e`. The published image supports **AMD64 and ARM64**.

## Installation and sign-in

Expose the app through Runtipi on an **HTTPS domain** before signing in. Set the public origin to that exact origin, for example `https://bills.example.com`, without a trailing slash. The app requires HTTPS origins and secure cookies; the direct HTTP port 8105 is useful for readiness checks, but cannot provide a working login.

Configure your own HTTPS OpenID Connect provider and a confidential authorization-code client. Register `<public origin>/auth/callback` as its redirect URI. Enter the exact issuer, client ID, client secret and the administrator's **sub claim**. The first start provisions that identity as administrator of tenant `default` and as plugin administrator. The provider must be reachable from the API container.

Initialization creates `config/service.json`, `secrets/credential-key` and `secrets/oidc-client-secret` under the app-data directory, fixes ownership for UID/GID 10001, validates configuration and provisions initial grants once. The initialization sidecar stays running so Runtipi can gate startup on its health.

## Configuration and persistence

The form's public origin, administrator and secrets seed files **only when missing**. After installation, edit `config/service.json` deliberately for origin changes, account bindings, tenant grants, destinations and plugin policies; align OIDC form settings and provider configuration with it. Stop the app before editing. Apply intentional grant/account changes using `billharbor-service --config /config/service.json provision` as UID 10001 in the API container. Startup does not restore revoked grants. Use upstream's explicit revoke command for removals.

For a client secret containing `$`, pre-create `secrets/oidc-client-secret` with its exact value instead of relying on Compose interpolation. Existing secret files are preserved. Keep permissions at 0600 with ownership 10001:10001. The encryption key file contains 32 raw bytes, initially decoded from the generated hexadecimal form value.

Back up `state` (SQLite and original documents), `config`, the generated encryption form value and `secrets`. Keep a separately protected backup of the encryption key: losing it makes stored vendor credentials unreadable. Changing the form key does not rotate existing credentials; use upstream's explicit key-rotation procedure. Take consistent SQLite backups with the app stopped or SQLite's backup API.

## Development scope

The app starts with **zero vendors and accounts**. Configure trusted plugin stores and reviewed immutable plugins in the UI; account/destination provisioning remains deployment configuration. Consult [plugin operations](https://github.com/EckPhi/billharbor/blob/main/docs/operations/plugin-stores.md).

The acquisition worker runs without network access and supports offline development fixtures. No delivery sender is started. Live vendor acquisition and delivery require separate upstream acceptance and deployment configuration. This is a development build, not an accepted production deployment. Runtipi terminates public HTTPS; the internal API listens over HTTP on port 8080.
