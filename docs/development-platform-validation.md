# Development platform verification — 2026-09-30

The implementation extends the existing Mistborn custom RunTipi store; it does not replace existing apps. Three independent app definitions now exist: `coder-dev`, `omnigent`, `mlflow`. The user explicitly directed that live acceptance remain pending because this environment has no Docker daemon/socket. No clean-VPS completion is claimed.

## Passed here

- `bun install`: dependencies present; no lockfile change.
- `PATH=/tmp/platform-bin:$PATH bun run test`: 240 passed, 0 failed. This includes app metadata/schema validation, independent storage/network boundaries, runtime packaging consistency and Python scenarios. The CI-only workspace Docker build test returns without building when `CI` is unset; its reported pass locally is **not** image-build evidence.
- Direct Python tests: all 25 Coder bootstrap/lifecycle/provider-plan scenarios passed with Terraform available; all 6 new MLflow configuration, secret-file, restart, dependency-update and prototype-contract scenarios passed.
- Terraform 1.15.5 initialization, formatting and validation with locked providers passed for the updated template, including optional Docker sidecar resources and exclusivity guard.
- The supported RunTipi 4.10.1 Compose builder at commit `5734817389df55aafb9afd571e42e12ab7e647e0`, with only import paths adapted in a temporary harness, generated 12 documents: all three apps under direct-port, domain, local-domain and Tailscale/direct-port forms. Docker Compose accepted every generated document with `config --quiet`. Readiness dependencies were preserved and no database gained a published port. This is configuration validation, not network/host execution.
- Real MLflow 3.16.1 `basic-auth` server launched in a temporary Python environment using SQLite. Created experiment/run, logged parameter/metric/artifact, restarted the server, read them back, and verified that a changed initial-password environment variable did not reset the existing admin password. No paid model calls. This validates upstream auth/tracking/artifact/restart behavior, **not the PostgreSQL Docker deployment**.
- Biome CI passed (existing configuration deprecation informational diagnostic). Python syntax, shell syntax, `git diff --check`, and generated README table passed.
- Upstream org avatars were converted to genuine 460×460 JPEGs; transparency flattened to white. Assets were visually inspected.

## Upstream versions and interfaces checked

Release APIs reported Coder v2.36.6, Omnigent v0.16.0 and MLflow v3.16.1. Registry manifests verified:

| Image | Architectures verified |
| --- | --- |
| `ghcr.io/omnigent-ai/omnigent-server:v0.16.0` | Linux AMD64, ARM64 |
| `ghcr.io/mlflow/mlflow:v3.16.1-full` | Linux AMD64, ARM64 |
| `postgres:17.11-bookworm` | AMD64, ARM64 among other architectures |
| `busybox:1.38.0` | AMD64, ARM64 among other architectures |
| `python:3.13.15-bookworm` | AMD64, ARM64 among other architectures |
| `node:24.21.0-bookworm` | AMD64, ARM64 among other architectures |
| `docker:28.5.2-cli` | AMD64, ARM64 among other architectures |
| `docker:28.5.2-dind-rootless` | AMD64, ARM64 |
| `rust:1.97.1-bookworm` | AMD64, ARM64 among other architectures |

Coder's existing pin matches the latest release reported. OpenCode npm package `opencode-ai` reported current stable 1.18.33, used in the image. PyPI confirmed `omnigent==0.16.0` and `mlflow==3.16.1`. Existing Codex/Claude pins were retained; their new workspace image execution remains pending.

Sources inspected: [RunTipi custom stores](https://runtipi.io/docs/guides/create-your-own-app-store), [dynamic Compose](https://runtipi.io/docs/reference/dynamic-compose), [Coder first-user API](https://coder.com/docs/reference/api/users), [templates push](https://coder.com/docs/reference/cli/templates_push), [SSH](https://coder.com/docs/reference/cli/ssh), [workspace create](https://coder.com/docs/reference/cli/create), [tokens](https://coder.com/docs/reference/cli/tokens_create), [Omnigent pinned Docker deployment](https://github.com/omnigent-ai/omnigent/blob/v0.16.0/deploy/docker/docker-compose.yaml), [runner/login CLI](https://github.com/omnigent-ai/omnigent/blob/v0.16.0/omnigent/cli.py), [telemetry source](https://github.com/omnigent-ai/omnigent/blob/v0.16.0/omnigent/telemetry/client.py), [MLflow auth](https://mlflow.org/docs/latest/self-hosting/security/basic-http-auth/), [artifact storage](https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/), [official full image](https://github.com/mlflow/mlflow/blob/v3.16.1/docker/Dockerfile.full).

## Pending runtime acceptance

- Clean RunTipi install; Coder administrator/template/dev initialization on real PostgreSQL and sibling Docker containers.
- Full updated image builds and non-root execution of every tool on AMD64/ARM64. CI now includes tool/C++ build smoke checks; no CI run is claimed here.
- Workspace persistence across stop/start, app restart, template upgrade, host reboot and native backup/restore.
- VS Code, Cursor, JetBrains, SSH, CLI, private Tailscale and workspace forwarding at 3000/5173/8000/8080.
- Omnigent PostgreSQL startup, first-account flow, authenticated workspace-host registration, task/session persistence and reconnect.
- MLflow PostgreSQL migration/persistence, full-image dependencies/non-root startup, S3-compatible authenticated upload/readback, backup restoration.
- The supplied `tests/platform/live.py` three-service prepare/restart/verify acceptance; Omnigent health in this test must be supplemented with a real authenticated runner session test.
- Experimental rootless sidecar socket ownership, health/readiness, kernel compatibility, container build and data persistence; trusted host-socket mode validation.
- Upgrades of all three services and rollback/restore on disposable deployments.

## Integration limits

Omnigent's supported server/runner connectivity is configured/documented; native Coder provisioning is absent upstream and not invented here. Optional Coder installer fields are explicitly reserved for an adapter. `scripts/platform/task.py` is an isolated experimental operator bridge, with tested command construction but no live execution. It is not registered as an Omnigent UI/scheduler provider. Automatic issue handling, PR creation and retention policy remain future work.

MLflow SDK integration is standard and demonstrated locally. Automatic Omnigent OTLP-to-MLflow tracing is not configured; a tracking URI alone does not enable it. Provider login, least-privilege credential grants, production TLS/Tailscale setup, object-bucket provisioning, backup/restore and destructive cleanup require operator participation. Details are in the [platform guide](development-platform.md).
