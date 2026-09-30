# MLflow

Independent authenticated tracking server using `ghcr.io/mlflow/mlflow:v3.16.1-full`, a dedicated PostgreSQL 17.11 instance and optional S3-compatible artifact storage. The official full image supplies authentication, PostgreSQL and object-store dependencies. No Coder or Omnigent dependency, no Docker socket, no database host port. Server processes run as UID 1000.

## Install

Choose an administrator username/password and allowed HTTP hosts. Enter comma-separated hostnames/IPs matching browser access, including ports where relevant, e.g. `mlflow.example.test,100.64.0.10:8098,localhost:*,127.0.0.1:*`. Do not include schemes or use `*` for all hosts. RunTipi publishes only the main port, 8098. Use HTTPS through normal routing or a trusted Tailscale-only deployment. Authentication is always enabled; initial credentials create the administrator only on an empty auth store. Changing the installer password does not rotate an existing password; use upstream's authenticated password API. PostgreSQL and CSRF secrets are generated and must be retained.

Tracking and authentication metadata use the dedicated PostgreSQL DB through supported SQLAlchemy configuration. Startup writes a mode-0600 auth config without an administrator password, then invokes upstream MLflow. DB credentials are passed by environment/config, not CLI arguments. No shell tracing or secret logging is enabled by glue code.

## Artifacts

Empty bucket uses `server/artifacts/` within app data. For S3, pre-create a bucket and set endpoint, access key, secret key and region. AWS may leave endpoint empty; MinIO and other compatible services need a full endpoint reachable from the server. Grant the account only access to the selected bucket/prefix. The server checks bucket access before startup. Use valid trusted TLS certificates. Artifacts are proxied through MLflow (`--serve-artifacts`); clients need MLflow credentials, not S3 credentials. HTTP health does not perform repeated writes or guarantee that every future bucket operation succeeds.

Migration: back up DB and artifact objects together. The proxy's destination can change, but existing relative artifact paths must be copied completely to the new prefix before changing destination. Preserve keys, verify old-run downloads and new-run uploads, then retain the original backup. Direct `file:` or `s3:` URIs from imported experiments need separate migration; changing the server does not rewrite stored artifact URIs. Never change bucket/destination and assume existing artifacts followed it.

For secrets containing literal dollar signs, place a private mode-0600 `server/secrets.json` under app data. Accepted keys are `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `MLFLOW_AUTH_ADMIN_PASSWORD`; these override installer values without Compose interpolation. Never commit this file. An existing admin password still requires API rotation. Back up this file encrypted.

## Clients

Install a compatible `mlflow==3.16.1` SDK in a project virtual environment, then configure:

```sh
export MLFLOW_TRACKING_URI=https://your-mlflow-host
export MLFLOW_TRACKING_USERNAME=your-user
# Load MLFLOW_TRACKING_PASSWORD from a protected environment file/secret manager.
```

Use `mlflow.start_run`, `log_param`, `log_metric`, `log_artifact`, and supported tracing/evaluation APIs. Create separate client accounts using MLflow's authentication API and grant narrowly scoped roles. Default permissions are `NO_PERMISSIONS`; the administrator manages grants. Coder/Omnigent URLs are unnecessary here. Analytics is disabled with `MLFLOW_DISABLE_TELEMETRY=true`.

## Backup, cleanup, upgrades

Critical: `postgres/`, `server/` configuration, and either local artifacts or the external bucket. RunTipi's native backup covers app data, **not external object storage**. Back up S3 independently with versioning/replication or a consistent export. Quiesce clients for a consistent snapshot. Test DB/object restoration together. Image layers are reproducible.

Upgrades are reviewable image changes; take a backup and test migrations/restoration on a disposable copy. PostgreSQL major upgrades require a supported dump/restore or pg_upgrade workflow, never just a major tag edit. The health endpoint is `/health`. A forbidden host response means allowed-hosts needs the actual browser/healthcheck host. S3 startup errors mean endpoint, credentials, region or bucket permissions need checking.

Retention must be explicit: inspect soft-deleted runs before running upstream `mlflow gc` with an age cutoff and the correct backend URI in a protected environment. GC can permanently delete artifacts. S3 lifecycle rules must agree with metadata retention; age alone is insufficient for deleting valuable experiment data. No automatic source/artifact deletion is configured.

Sources: [self-hosting](https://mlflow.org/docs/latest/self-hosting/), [auth](https://mlflow.org/docs/latest/self-hosting/security/basic-http-auth/), [artifact storage](https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/), [official full image](https://github.com/mlflow/mlflow/blob/v3.16.1/docker/Dockerfile.full).
