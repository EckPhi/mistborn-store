# Validation report — 2026-10-05

## Performed successfully

- Seven Python unittest cases: nested folder names and spaces; ZIP and compressed tar extraction preserving CAB fixtures; missing and ambiguous installers; Unix/Windows traversal; ZIP symlinks and case-insensitive duplicates; tar symlinks, hardlinks and FIFO entries; size limit and invalid archive cleanup; host-folder symlink rejection. Fixtures contain synthetic, nonexecutable text only and exist in temporary directories.
- `python3 tests/validate_metadata.py`: documented metadata invariants, app ID, amd64 restriction, required configuration fields, local-image policy and valid original JPEG metadata logo. The integration also passed mistborn-store’s vendored app-info and Runtipi 4.10.1 YAML schemas through Ajv.
- `docker compose config -q` on standalone and Runtipi YAML, with synthetic environment substitutions: both passed. Schema-2 extension structure reviewed against current Runtipi docs. The existing upstream Runtipi generator harness also produced valid private, TLS-domain and direct-port configurations while preserving volumes, platform and local-image policy. Actual proxy connectivity still requires a live instance.
- `bash -n` on startup scripts and host smoke script: passed.
- Invoking entrypoint without credentials: refused startup with exit 1 before `/init`.
- Registry manifest inspection: pinned Webtop release exists; amd64 digest resolved. Debian package page confirms Wine 10.0~repack-6. Codeberg README and repository tree read through HTTPS.
- Distribution review: Docker context explicitly allowlists runtime source; no Siemens installer, CAB, license or installed binaries were obtained or included.

- After integration into mistborn-store: `bun install` completed without dependency changes; regenerated store catalog; `bun run test` passed all 245 tests. Explicit SE_PUID/SE_PGID form fields replace variables omitted by Runtipi-generated app environments.

## Attempted but blocked by environment

`docker build --platform linux/amd64 -t solid-edge-webtop:0.1.0 runtime` failed before building: cannot connect to Docker daemon at `/var/run/docker.sock`. Docker client 28.5.2 and Compose 2.40.3 are available, but no engine is running. Therefore dependency installation, image size and boot behavior are unverified. No Wine binary or desktop runtime is available outside Docker here.

## Required on an amd64 Linux Docker host

1. Build image; confirm dated Debian snapshot and package dependencies resolve, then inspect `wine --version`.
2. Run `bash tests/host-smoke.sh`. It checks authenticated HTTPS, rejection of unauthenticated requests, Wine prefix initialization, and markers in Wine/project storage after container recreation. This script was syntax checked, **not executed** here. It does not establish GUI streaming correctness.
3. Manually view the desktop stream; test shortcuts and Wine GUI, credentials, reconnects and optional GPU rendering. Check the pinned base's upload target behavior; latest Selkies v2 documentation can differ from this release.
4. Add or refresh mistborn-store in Runtipi; install and verify configuration forms, TLS routing, WebSocket streaming, persistence and update/rollback behavior.
5. Transfer an actual ~5 GB archive through every deployed proxy; verify completion and original-file integrity or use host copy. Synthetic tests do not establish large-transfer reliability.
6. Test backup restore into isolated private directories.

## Requires the real Siemens installer

Installation and prerequisite dialogs, license review, executable discovery, launch and basic CAD operations have **not been tested**. Full CAB completeness and target 2510 authenticity cannot be determined by directory names alone. Record actual version, Wine/base digest, host/GPU and results for sketch/part creation, editing, assembly, save/reopen and rendering. Only then can compatibility be described as verified for that specific configuration.

Remaining risks include Wine Windows 11 reporting and API gaps; bootstrapper/prerequisite and .NET/VC++ requirements; licensing behavior; CAD graphics fidelity/performance; installer executable layout; host resource consumption; pinned versus current Selkies behavior; and prefix migration during Wine updates. This is an experimental integration scaffold, not a claim of working Solid Edge 2026 support.
