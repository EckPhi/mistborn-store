# Kopia workspace backup validation

Validated locally on 2026-10-22. This change adds the separate `kopia` app and
updates `coder-dev` revision 40 to stop copying workspace snapshots into app-data.
The legacy read-only mount in the offline Terraform storage initializer remains
for migration; Coder bootstrap no longer mounts legacy workspace/snapshot paths.
Old host data is deliberately retained and requires operator relocation after
migration and recovery verification.

- Docker Hub confirmed `kopia/kopia:0.23.1` for Linux AMD64 and ARM64. The image
  index digest inspected was
  `sha256:89fd95ee2942880ca00eae964266958a394421ddbdf69bca62e38afc55f5900e`.
- The release Dockerfile includes rclone and points `RCLONE_CONFIG` at
  `/app/rclone/rclone.conf`. The pulled image reports rclone v1.68.2.
- A disposable container started the authenticated UI with no repository;
  anonymous HTTP returned 401 and authenticated HTTP returned HTML. CSRF
  protection was left enabled. No host port was published for this smoke test.
- Filesystem repository creation, snapshot and restore recovered a file and
  symbolic link. The same round trip passed through Kopia's rclone backend with
  a local rclone remote. No real cloud credentials or workspace data were used.
- The Runtipi 4.10.1 Compose builder and matching Traefik builder from commit
  `5734817389df55aafb9afd571e42e12ab7e647e0` generated both applications in direct
  and exposed-domain modes. A temporary harness adapted imports/type references
  and supplied the app-URN extraction helper; builder logic was unchanged.
  Assertions verified generated routing, the external workspace volume and its
  read-only mount. Docker Compose accepted all four generated documents.
- `bun install` succeeded; `bun run test` passed 281 tests. The Python tests
  reported two skips (Terraform is unavailable). Tests required execution outside
  the sandbox for the existing temporary Unix-socket regression.
- Biome passed for the added deployment test. Checking the existing Coder test
  also reports two pre-existing unused suppression warnings. `git diff --check`
  passed. The README app table was regenerated; the upstream logo was converted
  to a 460x460 JPEG and visually inspected.

Actual RunTipi installation, public HTTPS access, cloud-provider authentication,
OAuth refresh, timed scheduler execution, native app-data backup exclusion and
full Coder disaster recovery remain deployment acceptance checks. Live snapshots
are not atomic; stop workspace writers for consistent recovery points. The
upstream rclone backend is not actively tested/maintained, even though the local
round trip passed. Prefer a native backend when possible.

References:

- [Kopia v0.23.1 release](https://github.com/kopia/kopia/releases/tag/v0.23.1)
- [Release image Dockerfile](https://github.com/kopia/kopia/blob/v0.23.1/tools/docker/Dockerfile)
- [Kopia rclone backend](https://kopia.io/docs/reference/command-line/common/repository-create-rclone/)
- [Coder subpath limitation](https://github.com/coder/coder/issues/14832)
