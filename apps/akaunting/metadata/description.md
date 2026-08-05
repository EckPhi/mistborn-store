# Akaunting

Akaunting is free, open-source and online accounting software designed for small businesses and freelancers. It runs entirely on your own server, so your books, customers and documents never leave the house.

## Features

- Invoicing with recurring invoices, taxes, discounts and multiple currencies
- Expense and bill tracking, vendor management, payment recording
- Bank accounts, transfers and reconciliation
- Customer and vendor portals
- Reports: profit & loss, tax summary, income/expense breakdowns
- Multi-company, multi-user with roles and permissions
- Extendable through the [Akaunting app marketplace](https://akaunting.com/apps)

## First start

The install runs automatically. On the first start the app:

1. seeds `app-data/html` with the Akaunting source from the image,
2. waits for the bundled MariaDB to become healthy,
3. runs `php artisan install` with the company name, company email, admin email and admin password you entered in the settings.

Give it a minute, then open the app and log in with the admin email and password. Once the installer has written `APP_INSTALLED=true` into `app-data/html/.env`, later starts skip the installer automatically — the upstream warning about never running `AKAUNTING_SETUP=true` twice is handled for you.

The company/admin settings fields are only read during that first install. Change your password and company details from the Akaunting UI afterwards; editing the fields here has no effect on an installed instance.

## App URL

Set **App URL** to the address you actually reach Akaunting on (e.g. `https://akaunting.example.com` when exposed through a domain, or `http://<your-server-ip>:8102` on the LAN). Akaunting builds asset and redirect URLs from it, so a wrong value produces broken styling or redirect loops.

## Data

- `app-data/html` — the Akaunting application directory, including `.env`, uploads and installed marketplace apps
- `app-data/db` — MariaDB data directory

Do not change the generated **Database password** or the **Database table prefix** after the first start: the MariaDB user is created only on the very first boot, and the prefix is baked into the installed schema.

## Updates

Because the application directory is persisted, bumping the image tag alone does **not** replace the PHP code of an existing install — this matches upstream's volume-based setup. Update an installed instance from **Settings → Updates** inside Akaunting. A fresh install always uses the code from the pinned image.

## Links

- Upstream docker images: <https://github.com/akaunting/docker>
- Source: <https://github.com/akaunting/akaunting>
- Documentation: <https://akaunting.com/docs>
