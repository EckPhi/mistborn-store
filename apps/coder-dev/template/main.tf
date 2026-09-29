provider "coder" {}
provider "docker" { host = "unix:///var/run/docker.sock" }
data "coder_provisioner" "me" {}
data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

data "coder_parameter" "host_docker" {
  name         = "host_docker"
  display_name = "Host Docker socket access"
  description  = "Grants administrative control over the RunTipi Docker host. Trusted users only."
  type         = "bool"
  default      = "false"
  mutable      = true
}
data "coder_parameter" "cpu" {
  name         = "cpu"
  display_name = "CPU limit (cores, 0 = unlimited)"
  type         = "number"
  default      = "0"
  mutable      = true
  validation { min = 0 }
}
data "coder_parameter" "memory" {
  name         = "memory"
  display_name = "Memory limit (MiB, 0 = unlimited)"
  type         = "number"
  default      = "0"
  mutable      = true
  validation { min = 0 }
}
locals {
  root       = "${var.data_root}/workspaces/${data.coder_workspace.me.id}"
  cache      = "${var.data_root}/caches/${data.coder_workspace.me.id}"
  image_hash = substr(sha256(join("", [file("${path.module}/image/Dockerfile"), file("${path.module}/image/entrypoint.sh")])), 0, 16)
}
resource "coder_agent" "main" {
  arch           = data.coder_provisioner.me.arch
  os             = "linux"
  startup_script = <<-EOT
    #!/bin/bash
    set -euo pipefail
    export PATH="$PNPM_HOME:$PATH"
    ccache --max-size=10G
    pnpm config set store-dir /cache/pnpm --global
    git lfs install --skip-repo >/dev/null
    if [ -n "$CODER_DEV_GIT_NAME" ]; then git config --global user.name "$CODER_DEV_GIT_NAME"; fi
    if [ -n "$CODER_DEV_GIT_EMAIL" ]; then git config --global user.email "$CODER_DEV_GIT_EMAIL"; fi
    printf 'Coder ${var.development_stack} Development Workspace\nClone a repository: git clone <repo>\n'
  EOT
  env = {
    CODER_DEV_GIT_NAME    = var.git_name
    CODER_DEV_GIT_EMAIL   = var.git_email
    CCACHE_DIR            = "/cache/ccache"
    CONAN_HOME            = "/cache/conan"
    PIP_CACHE_DIR         = "/cache/pip"
    UV_CACHE_DIR          = "/cache/uv"
    npm_config_cache      = "/cache/npm"
    PNPM_HOME             = "/home/coder/.local/share/pnpm"
    XDG_CACHE_HOME        = "/cache"
    PUB_CACHE             = "/cache/pub"
    CARGO_TARGET_DIR      = "/cache/cargo-target"
    UV_PYTHON_INSTALL_DIR = "/cache/uv-python"
  }
}
# Builds on the host daemon, using the architecture of the Coder provisioner.
resource "docker_image" "development" {
  count        = data.coder_workspace.me.start_count
  name         = "coder-dev-workspace:${var.development_stack}-${local.image_hash}-${data.coder_provisioner.me.arch}"
  keep_locally = true
  build {
    context = "${path.module}/image"
    target  = var.development_stack
  }
  lifecycle {
    precondition {
      condition     = var.development_stack != "flutter" || data.coder_provisioner.me.arch == "amd64"
      error_message = "The packaged Flutter SDK requires an AMD64 Linux host. Use a Python, Rust or general template on ARM64."
    }
  }
}
resource "docker_container" "workspace" {
  count      = data.coder_workspace.me.start_count
  name       = "coder-dev-${data.coder_workspace.me.id}"
  hostname   = data.coder_workspace.me.name
  image      = docker_image.development[0].image_id
  command    = ["bash", "-c", coder_agent.main.init_script]
  env        = ["CODER_AGENT_TOKEN=${coder_agent.main.token}"]
  memory     = tonumber(data.coder_parameter.memory.value)
  cpu_quota  = tonumber(data.coder_parameter.cpu.value) * 100000
  cpu_period = 100000
  restart    = "unless-stopped"
  volumes {
    host_path      = "${local.root}/home"
    container_path = "/home/coder"
  }
  volumes {
    host_path      = "${local.root}/source"
    container_path = "/workspaces"
  }
  volumes {
    host_path      = local.cache
    container_path = "/cache"
  }
  dynamic "volumes" {
    for_each = data.coder_parameter.host_docker.value == "true" ? [1] : []
    content {
      host_path      = "/var/run/docker.sock"
      container_path = "/var/run/docker.sock"
    }
  }
  host {
    host = "host.docker.internal"
    ip   = "host-gateway"
  }
  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }
}
