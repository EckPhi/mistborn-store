# ERPNext

ERPNext is an open-source enterprise resource planning suite built on the Frappe Framework. It combines accounting, invoicing, inventory, manufacturing, purchasing, sales, CRM, projects, assets, point of sale and human resources in one system.

This package uses the IEF Bookkeeping `v0.8.1` image. It extends ERPNext 16.33.0
with the `ief_bookkeeping` Frappe app, Poppler, and fully local German/English
Tesseract OCR. The image is currently published for amd64 only.

The custom image is pulled from its public Docker Hub repository. Installing and
updating this Runtipi app does not require registry credentials.

## Upgrade to v0.8.1

Requires Runtipi 4.10.1 or later. This release uses modern Compose YAML and keeps
image-generated assets in small, independent tmpfs mounts. Site configuration,
public/private uploads and database storage keep their existing persistent paths.
No separate runtime-assets user override is required; remove any older image or
assets override only after checking that unrelated customizations are preserved.

**Existing installations need a one-time preparation before updating.** Stop the
app's writers and preserve a consistent database/sites/configuration checkpoint
with the backup owner. Inspect `sites/assets` without following links. Only when
it is a symlink targeting exactly `/home/frappe/frappe-bench/assets`, remove that
single symlink and create an empty real `sites/assets` directory owned by
1000:1000. Do not recursively delete or copy assets, or change site files. Stop
for review if the path is another kind of file, has another link target, or is a
nonempty real directory. Startup deliberately refuses unconverted storage.

Preserve old archives unchanged: this fix does not repair their legacy symlink.
An independently usable recovery path is required before conversion; the backup
owner must handle any legacy archive compatibility on copies in isolation.
After updating, verify migration, login, assets and retained file hashes, then
perform a fresh backup/restore drill for the new image and storage layout.
Do not restore an old image against a migrated database without compatibility
proof; recover the matching database, sites and image together if required.

## First start

The first start creates the database configuration and a site named `frontend`, then installs ERPNext. On every start, including an upgrade, the startup gate migrates that site before the application services are allowed to start. This can take several minutes; the web interface becomes available after site creation and migration finish successfully.

The image makes `ief_bookkeeping` available to Bench but does not install it on a
site automatically. Install it only on the separately approved test site after
the stack is healthy. Do not install it on a production site.

Sign in with the username **Administrator** and the administrator password entered during installation. The initial setup wizard will guide you through company, currency, locale and fiscal-year settings.

## Data and backups

Persistent data is stored below the app-data directory:

- `sites` contains the ERPNext site configuration, public and private files, and site metadata.
- `db` contains the MariaDB database.
- `redis-queue` contains queued background jobs.

Back up both `sites` and `db` together. Keep the generated database root password with the backup and do not change it in the app settings after the first start.

Runtipi creates its upgrade backup before replacing the containers. Keep that backup until the automatically migrated site and retained records have been verified. An image rollback does not reverse a database migration; restore the matching pre-upgrade database and site files when schema rollback is required.

## Networking

Open ERPNext directly at `http://<runtipi-host>:8103` or expose it through Runtipi with a domain. The internal MariaDB and Redis services are not published to the host.

## Resources

ERPNext runs several application, worker, database and cache containers. A small production installation should have at least 4 GB of memory available; larger databases and concurrent workloads need more.

- [ERPNext documentation](https://docs.frappe.io/erpnext)
- [Frappe Docker documentation](https://github.com/frappe/frappe_docker)
- [ERPNext source](https://github.com/frappe/erpnext)
