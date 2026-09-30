# Receipt Wrangler

Receipt Wrangler is a self-hosted receipt manager. Throw a photo or a PDF at it and it reads the merchant, date and total, files the receipt under a category and — if you share expenses — splits it between the members of a group.

## Features

- OCR and AI-assisted receipt scanning (local OCR or an external AI provider)
- Groups with automatic receipt splitting between users
- Email polling: receipts sent to a mailbox are imported on a schedule
- Categories, tags, custom fields and receipt workflows with approvals
- Dashboards, budgets and exports
- Web app plus a mobile client

## First start

Open the app and create the first user — that account becomes the admin. Everything else (groups, categories, email integrations, AI provider) is configured from the UI.

## What runs

Three containers:

- `receipt-wrangler` — API and web UI
- `receipt-wrangler-db` — MariaDB. Upstream explicitly advises against SQLite for long-term use (column and index changes do not always apply), so this app ships MariaDB
- `receipt-wrangler-redis` — required. It backs the background job queue used by OCR, email polling and scheduled tasks; the app refuses to start without it

## Keys

**Encryption key** protects stored email passwords and API keys and **cannot be rotated**. If it changes, existing encrypted records can no longer be decrypted and must be deleted and recreated — setting the old value back makes them readable again. Back it up together with `app-data`.

**Secret key** signs the JWT session tokens; changing it just logs everyone out.

## Data

- `app-data/data` — uploaded receipt images
- `app-data/logs` — application logs
- `app-data/db` — MariaDB data directory
- `app-data/redis` — Redis persistence

## Links

- Source: <https://github.com/Receipt-Wrangler/receipt-wrangler>
- Documentation: <https://receiptwrangler.io/docs>
