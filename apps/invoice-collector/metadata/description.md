# Invoice Collector

Invoice Collector is a free, self-hostable Docker image designed to automatically retrieve invoices and receipts from your suppliers. It connects to customer portals, APIs, and email inboxes to gather invoices in seconds, so you never have to log into a dozen websites at month-end again.

## Features

- Automatic invoice and receipt retrieval from a growing list of suppliers
- Connects to customer portals, APIs and email inboxes
- Self-hosted — your credentials and documents stay on your server
- REST API for integration with your own tooling

## Configuration

Invoice Collector stores its data in a bundled MongoDB instance and uses a secret manager (Bitwarden by default) to keep supplier credentials safe. Configure the secret manager via the service environment variables:

- `SECRET_MANAGER_BITWARDEN_ACCESS_TOKEN`
- `SECRET_MANAGER_BITWARDEN_ORGANIZATION_ID`
- `SECRET_MANAGER_BITWARDEN_PROJECT_ID`

See the [project documentation](https://github.com/invoice-collector/invoice-collector) for the full list of supported suppliers and configuration options.
