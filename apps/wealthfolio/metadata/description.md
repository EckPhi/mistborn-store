# Wealthfolio

Wealthfolio is a privacy-first, open-source investment tracker. It pulls your holdings from several brokers and accounts into one dashboard and answers the question the broker apps avoid: how is the whole portfolio actually doing?

## Features

- Holdings, net worth and cash across multiple accounts and currencies
- Performance and return calculations benchmarked against indexes such as the S&P 500
- Dividends and income tracking
- Allocation views and rebalancing targets
- CSV import for activities, manual entry, and add-ons for broker connections
- Local SQLite database — no account, no telemetry, nothing leaves the server

## Before you install: the login password

Wealthfolio does not take a plaintext password. It wants an **Argon2id PHC hash**, which you generate yourself:

```bash
printf '%s' 'your-password' | argon2 yoursalt16chars -id -e
```

Use `printf`, not `echo` — a trailing newline produces a hash that never matches. The result looks like `$argon2id$v=19$m=65536,t=3,p=4$...`.

Paste it into the **Password hash** field. The `$` signs in the hash can be eaten before they reach the container depending on how the value is written out; if login then fails, put the hash in a file instead:

```bash
printf '%s' '$argon2id$v=19$...' > <runtipi>/app-data/wealthfolio/data/password.hash
chown 1000:1000 <runtipi>/app-data/wealthfolio/data/password.hash
```

The app reads that file at start and it takes precedence over the form field. Restart the app afterwards.

SSO is supported upstream through `WF_OIDC_*` variables; this app does not expose them yet.

## App URL

Set **App URL** to the exact origin you use in the browser — scheme, host and port. It becomes the allowed CORS origin, and a mismatch makes every API call fail even though the page itself loads.

## Data and backups

`app-data/data` holds `wealthfolio.db` and the encrypted secrets file, and is owned by uid 1000 (an init container sets this up).

Back up that directory **together with the Secret key** from the app settings. The database is useless without the key, and the key is useless without the database.

## Links

- Source: <https://github.com/wealthfolio/wealthfolio>
- Self-hosting docs: <https://wealthfolio.app/docs/guide/self-hosting/>
