# Development templates

Pinned Coder and Docker Terraform providers create a sibling Docker container
using a Debian Bookworm/Node LTS image built by the host Docker engine. The
Dockerfile bundles Git/LFS, SSH client, compilers/debuggers, CMake/Ninja, Python,
uv, Conan, Node/npm/pnpm, Docker/Compose, ccache and common terminal tools.
The first build needs Internet access and substantial free disk space.

Bootstrap injects the absolute host `data_root` and optional Git identity.
Do not replace `data_root` on an existing template without migrating its data.
The sources bind at `/workspaces`, developer home at `/home/coder` and disposable
caches at `/cache`. Paths use workspace UUIDs, survive container deletion, and
are not Terraform-owned resources that a destroy can remove. Restarting a
workspace preserves SSH configuration, Git settings and repositories.

CPU cores and memory MiB default to 0 (unlimited). Host Docker access is false by
default; enabling it grants host administrative privileges. No privileged
container, host network, direct SSH port or Docker TCP listener is created.
The entrypoint initializes a fresh home, detects the optional socket GID, and
runs the agent as `coder` (UID 1000). Bash lands in `/workspaces`.

The agent configures ccache (10 GB), persistent pnpm storage and optional Git
identity. IDE backends live in persistent home; their indexing and builds run
remotely. Use Coder forwarding for development web ports.

Bootstrap publishes this shared definition under `general-development`,
`python-development`, `rust-development` and (AMD64 only)
`flutter-development`. It selects the corresponding Docker build target using
the `development_stack` variable. Profiles have distinct image names and share
cached base-image layers, but each workspace has independent source/home/cache
directories. Image resources exist only while the workspace is started;
stopping removes Terraform image ownership while retaining the local image.

Python adds Python 3.13/Poetry and Chromium runtime dependencies. Rust adds
Rust 1.97.1, Clippy, rust-analyzer, WASI and native libraries. Flutter adds a
verified Flutter 3.47.3 source commit, Dart, Linux/web tooling and JDK 17.
Flutter's build-time tool cache lives in the SDK, while project packages use
the persistent `/cache/pub` bind mount at runtime. Android SDK setup is separate.
When changing Flutter, update both the tag and verified commit in the Dockerfile.
See [project migration](../MIGRATION.md) for legacy Dart projects and Mac builds.

For manual validation, run `terraform init -backend=false` and
`terraform validate` in this directory. `.terraform.lock.hcl` includes AMD64
and ARM64 provider checksums. Never commit Terraform state or `.terraform/`.
See the [app README](../README.md) for installation, IDEs, backups and security.
