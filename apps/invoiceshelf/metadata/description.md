# InvoiceShelf

InvoiceShelf is a self-hosted invoicing application for freelancers and small businesses, maintained as the community continuation of Crater.

## Features

- Invoices, estimates, recurring invoices and payments
- Expense tracking, customers and items
- Multiple companies, currencies and tax rates
- Customisable invoice templates and numbering
- Email documents to clients directly from the app
- Roles and permissions for multiple users

## First start

Open the app and walk through the installation wizard: it checks the environment, asks for your company details and creates the admin account. The database settings are already supplied by this app — leave them as they are. The installation state lives in the database, so you only do this once.

## URL settings — read this before installing

The three URL fields must match how you actually open the app, or you get missing styling, failed logins or a `419` page after submitting the login form:

| Field | Example (LAN) | Example (domain) |
|---|---|---|
| App URL | `http://192.168.1.10:8090` | `https://invoices.example.com` |
| Session domain | `192.168.1.10` | `invoices.example.com` |
| Stateful domains | `192.168.1.10:8090` | `invoices.example.com` |

If you reach the app through more than one address, comma-separate them in *Stateful domains*. Change the fields and restart the app after moving it behind a domain.

## Data

- `app-data/storage` — uploads, logs, cache and the SQLite database (`app/database.sqlite`)
- `app-data/modules` — modules installed from the InvoiceShelf marketplace

The container runs as uid 82 (`www-data`), so an init container hands both directories to that uid before the app starts.

The generated **App key** is the Laravel `APP_KEY`. It is kept in the app settings rather than inside the container so it survives container recreation — encrypted settings such as stored mail passwords depend on it. Do not change it after the install.

A MySQL/MariaDB or PostgreSQL setup is also supported upstream; this app ships the SQLite variant, which needs no extra container.

## Links

- Source: <https://github.com/InvoiceShelf/InvoiceShelf>
- Docker images: <https://github.com/InvoiceShelf/docker>
- Features: <https://invoiceshelf.com/features>
