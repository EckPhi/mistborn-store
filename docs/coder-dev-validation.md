# Coder development app validation

Implemented in the existing store as `apps/coder-dev`; existing staged pyLoad
changes were preserved. Initial checks were local. Subsequent language-template
checks used the user's existing AMD64 deployment at `coder.hygge.quest`.

Local checks on 2026-09-29:

- 224 repository tests passed; the Coder test invokes 19 Python bootstrap/update/lifecycle
  scenarios, including restarts, partial failures, failed initial builds,
  password changes, stopped/deleted workspaces, upgrades, interrupted template
  publication and incomplete restore detection.
- Biome CI passed, with only the repository's existing configuration deprecation
  informational diagnostic.
- Terraform 1.15.5 validation passed for the final template. Provider versions
  are locked and checksums cover Linux AMD64 and ARM64.
- Pinned registry tags/manifests were checked for Coder v2.36.6, PostgreSQL
  17.11-bookworm, Python 3.13.15-bookworm, Node 24.21.0-bookworm and Docker
  28.5.2-cli. They publish AMD64 and ARM64 images. Actual workspace image builds
  were pending at this initial validation stage.
- The unmodified RunTipi 4.10.1 generator (only imports adapted in a temporary
  harness) preserved the entrypoint, volumes, readiness gates and generated
  routing for direct-port, exposed-domain, local-domain and Tailscale URL
  configurations. Docker Compose 5.4.0 accepted all four generated documents.
  This is configuration validation, not a network-connectivity test.
- Both shell wrappers passed syntax checks; the official Coder org avatar was
  converted to a 460x460 JPEG and visually inspected.
- The deterministic embedded archive matches the maintained source files.

The original local `node_modules` contains iCloud dataless files; normal
`bun install`/test loading stalled. Fresh dependencies were installed in a
separate temporary directory and the unchanged repository test suite was run
against those, with the original repository as its working directory. The
original dependency cache was left in place. No tracked dependency lock changed.

A usable local Docker daemon and clean Linux RunTipi test host were unavailable
during initial validation. The user subsequently installed the app manually;
the live language-template checks are recorded below. IDE connections, reboot
persistence, full security inspection, vulnerability scanning and native
backup/restore are **not verified**. The
[manual acceptance checklist](../tests/coder-dev/ACCEPTANCE.md) records the required
remaining checks. Production readiness depends on those passing.

Upstream references:

- [RunTipi dynamic Compose reference](https://runtipi.io/docs/reference/dynamic-compose)
- [Pinned RunTipi generator](https://github.com/runtipi/runtipi/blob/5734817389df55aafb9afd571e42e12ab7e647e0/packages/backend/src/modules/docker/builders/compose.builder.ts)
- [Pinned RunTipi backup implementation](https://github.com/runtipi/runtipi/blob/5734817389df55aafb9afd571e42e12ab7e647e0/packages/backend/src/modules/backups/backup.manager.ts)
- [Pinned Coder image base](https://github.com/coder/coder/blob/v2.36.6/scripts/Dockerfile.base)
- [Coder first-user API](https://coder.com/docs/reference/api/users)
- [Coder templates push](https://coder.com/docs/reference/cli/templates_push)

Follow-up adds a SIGTERM-driven graceful workspace stop/resume journal with a
five-minute Compose grace period. Tests cover running-versus-stopped selection,
version preservation, stop failure, asynchronous restart idempotency, deletion,
respecting a later user stop, and delivering SIGTERM to a real helper process. RunTipi's stop command calls Compose `down
--remove-orphans`; no native app-store pre-stop/post-start hook fields exist in
the pinned release or current source inspected. Live ordering remains unverified.

Git repair found `.DS_Store` in `refs/` (an invalid ref) and inactive iCloud
metadata placeholders. Locally available Git bytes and working changes were
archived before quarantining Finder files. No commits were discarded or forced.

The stale Git commit graph was rebuilt, remote main was fast-forwarded without
stashing or discarding the staged app work, and `git fsck --full --no-dangling`
then passed. iCloud can reintroduce placeholder metadata; this repair does not
move the checkout out of the synchronized Documents directory.

The user's first manual installation reached Coder template planning, which
failed because the unlimited CPU default resolved to `cpu_quota = -1`.
The pinned Docker provider 3.6.2 requires a nonnegative quota. App revision 2
uses `0` for unlimited CPU and retains the cores-to-microseconds conversion
for limits. The embedded template archive was regenerated.

A new regression plans the maintained CPU/memory expressions with the actual
locked Docker provider against a local HTTP ping stub. It checks unlimited
CPU/memory, half a CPU with 512 MiB, and two CPUs with 2048 MiB, including the
planned values. It creates no containers and does not exercise Coder's API or
workspace image builds. The prior `-1` setting reproduced the reported error
with the real provider; `terraform validate` alone had missed it. CI now
installs Terraform so this regression runs rather than skips. All 20 Python
scenarios passed locally, as did the repository suite and lint.

Existing installations should refresh the app store and update the app. The
new template fingerprint retries setup using the existing administrator and
database; reinstalling or deleting app data is unnecessary. The user's next
installation built `dev` successfully; the startup issue found subsequently
is described below.

## Language templates and live follow-up

App revision 3 publishes general, Python, Rust and Flutter templates using one
maintained Terraform definition and explicit Docker build targets. Flutter is
AMD64-only; Python/Rust retain ARM64 support pending live ARM64 verification.
Existing template fingerprints migrate to per-template state, partial
publication resumes independently, and existing workspaces aren't restarted
by bootstrap. Failed named-version retries now retain all injected variables.

The authenticated desktop CLI confirmed the initial `dev` build succeeded, but
its agent startup failed because pnpm's configured bin directory wasn't in
PATH. The corrected startup passes in the new live workspaces; bootstrap also
rejects a connected agent with a startup error instead of marking setup ready.
Applying the corrected version to `dev` requires an explicit workspace update;
the user's running `dev` was left in place.

Live AMD64 checks on the existing RunTipi host:

- Python workspace image built and its agent reached `ready`. Python 3.13.15,
  uv 0.8.22, Poetry 2.2.1, Bun 1.3.14 and pnpm 10.17.1 ran. A virtual environment
  executed a Python 3.13 assertion and sample computation.
- Rust workspace image built and its agent reached `ready`. Rust/Cargo 1.97.1,
  rustfmt, Clippy, rust-analyzer and `wasm32-wasip2` were present. A new Cargo
  project compiled successfully and Clippy passed with warnings treated as errors.
- Flutter 3.47.3 at verified commit `e8113bf45620cbeb8aff64947ee4c93e16adb4cf`
  initialized with Dart 3.13.3. Its image initially failed because runtime
  `/cache/pub` wasn't available during the build. Build-time tool dependencies
  now use `/opt/flutter/.pub-cache`; workspace packages use `/cache/pub`.
  A fresh workspace reached `ready`, and a generated Flutter app passed analysis,
  its widget test, web compilation and Linux compilation. It ran as UID 1000
  without the Docker socket. Source and compiled web outputs survived stop/start,
  and the cached image recreated successfully without downloading the SDK again.
- Images are now conditional on workspace start count, keeping local layers
  while removing Terraform ownership on stop. This prevents a stop from trying
  to build an image, including recovery from failed initial image creation.
- All 25 Python regressions, all 224 store tests, Biome CI, Terraform validation,
  shell syntax and deterministic packaging passed. The maintained RunTipi
  generator preserved all four URL/routing scenarios.

## Isolated Docker development — app revision 10

New workspaces now default to per-workspace rootless DinD. Workspace host-socket
access has been removed; the control plane retains its provisioning socket.
Source/home/cache bind paths and the sidecar network namespace are shared so
Compose bind mounts and workspace-local published ports can work. A one-shot
initializer prepares UID 1000 volume ownership. Docker data survives stop/start
and is disposable on workspace deletion or Docker disable.

The repository suite (240 tests, including 28 Python scenarios), locked-provider
Terraform validation, real-provider start/stop/disable plans, lint, shell syntax,
deterministic packaging and four pinned RunTipi/Docker Compose configuration
checks passed. Runtime execution remains pending without a local Docker daemon.
See [the follow-up verification record](development-platform-validation.md#per-workspace-docker-follow-up--2026-10-05)
and [acceptance checklist](../tests/coder-dev/ACCEPTANCE.md).
