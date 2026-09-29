# general-development

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
remotely. Use Coder forwarding for development web ports. Additional language
images/templates can reuse this storage and bootstrap structure later.

For manual validation, run `terraform init -backend=false` and
`terraform validate` in this directory. `.terraform.lock.hcl` includes AMD64
and ARM64 provider checksums. Never commit Terraform state or `.terraform/`.
See the [app README](../README.md) for installation, IDEs, backups and security.
