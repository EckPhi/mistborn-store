# Coder development app validation

Implemented in the existing store as `apps/coder-dev`; existing staged pyLoad
changes were preserved. No live deployment was performed. Publication is requested in the follow-up.

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
  on these architectures remain pending.
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

A usable local Docker daemon and clean Linux RunTipi test host were unavailable.
The user will perform manual installation. Live Coder/image provisioning, IDE
connections, development builds, reboot persistence, security inspection,
vulnerability scanning and native backup/restore are **not verified**. The
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
database; reinstalling or deleting app data is unnecessary. Live workspace
provisioning remains pending the user's next manual installation attempt.
