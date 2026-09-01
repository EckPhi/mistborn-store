# ERPNext

ERPNext is an open-source enterprise resource planning suite built on the Frappe Framework. It combines accounting, invoicing, inventory, manufacturing, purchasing, sales, CRM, projects, assets, point of sale and human resources in one system.

## First start

The first start creates the database configuration and a site named `frontend`, then installs ERPNext. This can take several minutes; the web interface becomes available after site creation finishes.

Sign in with the username **Administrator** and the administrator password entered during installation. The initial setup wizard will guide you through company, currency, locale and fiscal-year settings.

## Data and backups

Persistent data is stored below the app-data directory:

- `sites` contains the ERPNext site configuration, public and private files, and site metadata.
- `db` contains the MariaDB database.
- `redis-queue` contains queued background jobs.

Back up both `sites` and `db` together. Keep the generated database root password with the backup and do not change it in the app settings after the first start.

For a consistent application-level backup, use the Frappe Bench backup command from the backend container. ERPNext upgrades may also run database migrations, so make a backup before updating.

## Networking

Open ERPNext directly at `http://<runtipi-host>:8103` or expose it through Runtipi with a domain. The internal MariaDB and Redis services are not published to the host.

## Resources

ERPNext runs several application, worker, database and cache containers. A small production installation should have at least 4 GB of memory available; larger databases and concurrent workloads need more.

- [ERPNext documentation](https://docs.frappe.io/erpnext)
- [Frappe Docker documentation](https://github.com/frappe/frappe_docker)
- [ERPNext source](https://github.com/frappe/erpnext)
