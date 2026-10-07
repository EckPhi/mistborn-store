# LiteLLM gateway validation

Validated locally on 2026-10-07. This app has not been installed on the user's
Runtipi host and contains no real provider credentials.

## Passing checks

- Registry manifests confirm `ghcr.io/berriai/litellm:v1.104.0` and
  `postgres:17.11-bookworm` exist and support Linux AMD64 and ARM64. LiteLLM's
  image runs as root with its upstream entrypoint and listens on port 4000;
  no application-directory mount or permissions sidecar is required.
- The vendored schemas accept the app. The store has exactly one Compose source,
  one main service, a free host port (4011), generated secrets and a private DB.
- All 250 repository tests pass. On macOS, the existing Coder Unix-socket test
  requires a short temporary directory (`TMPDIR=/tmp`) and permission to create
  sockets outside the sandbox. No test or application changes were needed for it.
- Biome CI and `git diff --check` pass. Biome reports the existing configuration
  deprecation notice.
- The pinned Runtipi 4.10.1 Compose builder and Traefik label builder preserve
  readiness gates, environment and database isolation for direct-port, exposed
  domain and local-domain configurations. Only imports and the app-URN helper
  were adapted for the temporary harness; the builders were unchanged.
- Docker Compose 5.5.1 accepts all three generated configurations.
- A local ARM64 stack built from the generated direct-port configuration starts
  healthy and initializes PostgreSQL. Its test-only changes are a loopback port
  (14011), a private network without Runtipi's external network, no restart policy
  or Runtipi labels, and disposable storage with generated test credentials.
- The dashboard and database readiness endpoints respond successfully.
  Unauthenticated `/v1/models` requests are rejected. An admin can create a
  virtual key, and that key can list models. The key survives a gateway restart;
  deleting it rejects subsequent access.
- An admin can save a model in PostgreSQL and advertise its alias to clients.
  Chat Completions and SSE streaming pass with LiteLLM's local `mock_response`;
  no upstream model request or billable inference was made.
- The upstream logo is a visually inspected 460x460 JPEG.

## Automatic Coder provisioning

The optional Coder integration is disabled until a gateway URL, admin key and
allowed model aliases are configured in Runtipi. Coder's update counter advances
from 25 to 26 and its embedded runtime archive is regenerated.

Twelve provisioning regression scenarios pass: restart reuse, private delivery,
recovery after a lost creation response, complete-list deletion, manual revocation
and blocking, existing OMP configuration preservation, model permission updates,
gateway outages, invalid IDs/symlinks, complete pagination, admin-key isolation
and explicit gateway-switch cleanup.
The full store suite still passes all 250 tests, including 40 Python Coder scenarios
(two existing platform-specific scenarios are skipped on macOS).

An isolated LiteLLM instance also confirms that the actual provisioning helper can
create a custom inference-only key, route a local mock completion, reject key
management attempted with that key, reuse it, change its allowed models and revoke
it on workspace deletion. This uses LiteLLM's real management APIs and database,
with a scenario double for Coder workspace discovery. No real provider requests
were made. The final Coder deployment also passes the pinned Runtipi generator
and Docker Compose checks; provisioning secrets occur only in the trusted server
helper's environment. Live reconciliation on the user's Coder deployment remains
pending.

## Remaining acceptance

- Install on the user's Runtipi host and verify its chosen HTTPS endpoint from
  a Coder workspace.
- Add real OpenRouter and/or Requesty credentials through the dashboard and
  verify tool calls and streaming with the user's selected models in OMP.
- Clone the user's private skills repository and verify discovery in OMP.
- Rehearse a database/configuration backup and restore on the target host.

## Sources

- [LiteLLM release](https://github.com/BerriAI/litellm/releases/tag/v1.104.0)
- [Upstream two-service deployment](https://github.com/BerriAI/litellm/blob/v1.104.0/docker/docker-compose.quickstart.yml)
- [Pinned Runtipi builder](https://github.com/runtipi/runtipi/blob/5734817389df55aafb9afd571e42e12ab7e647e0/packages/backend/src/modules/docker/builders/compose.builder.ts)
- [Requesty OpenAI-compatible API](https://docs.requesty.ai/)
- [OMP gateway client configuration](https://github.com/can1357/oh-my-pi/blob/v18.8.0/docs/models.md)
