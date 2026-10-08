provider "coder" {}
provider "docker" { host = "unix:///var/run/docker.sock" }
data "coder_provisioner" "me" {}
data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

data "coder_parameter" "docker_development" {
  name         = "docker_development"
  display_name = "Enable Docker development (isolated rootless sidecar)"
  description  = "Isolated rootless daemon, no host socket. Requires a privileged sidecar for user namespaces; trusted hosts only."
  type         = "bool"
  default      = "true"
  mutable      = true
}
data "coder_parameter" "ai_agents" {
  name         = "ai_agents"
  display_name = "Enable AI coding tools"
  description  = "Include Codex, Claude Code, OpenCode, Omnigent, OMP and Mistral Vibe in the workspace image."
  type         = "bool"
  default      = "true"
  mutable      = true
}
data "coder_parameter" "omnigent_url" {
  name         = "omnigent_url"
  display_name = "Optional Omnigent URL"
  type         = "string"
  default      = ""
  mutable      = true
}
data "coder_parameter" "mlflow_url" {
  name         = "mlflow_url"
  display_name = "Optional MLflow tracking URL"
  type         = "string"
  default      = ""
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
  image_hash = substr(sha256(join("", [
    file("${path.module}/image/Dockerfile"),
    file("${path.module}/image/entrypoint.sh"),
    file("${path.module}/image/zshrc"),
    file("${path.module}/image/agent-info"),
    data.coder_parameter.ai_agents.value,
  ])), 0, 16)
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
    if [ -n "$${DOCKER_HOST:-}" ]; then
      ready=false
      for attempt in {1..60}; do
        if docker info >/dev/null 2>&1; then ready=true; break; fi
        sleep 2
      done
      if [ "$ready" != true ]; then echo 'Development Docker daemon did not become ready.' >&2; exit 1; fi
    fi
    if [ -n "$CODER_DEV_GIT_NAME" ]; then git config --global user.name "$CODER_DEV_GIT_NAME"; fi
    if [ -n "$CODER_DEV_GIT_EMAIL" ]; then git config --global user.email "$CODER_DEV_GIT_EMAIL"; fi
    printf 'Coder ${var.development_stack} Development Workspace\nClone a repository: git clone <repo>\n'
  EOT
  env = {
    DOCKER_HOST                = data.coder_parameter.docker_development.value == "true" ? "unix:///docker-socket/docker.sock" : ""
    OMNIGENT_SERVER            = data.coder_parameter.omnigent_url.value
    MLFLOW_TRACKING_URI        = data.coder_parameter.mlflow_url.value
    OMNIGENT_ANALYTICS         = "0"
    OMNIGENT_DISABLE_TELEMETRY = "true"
    DO_NOT_TRACK               = "1"
    CODER_DEV_GIT_NAME         = var.git_name
    CODER_DEV_GIT_EMAIL        = var.git_email
    CCACHE_DIR                 = "/cache/ccache"
    CONAN_HOME                 = "/cache/conan"
    PIP_CACHE_DIR              = "/cache/pip"
    UV_CACHE_DIR               = "/cache/uv"
    npm_config_cache           = "/cache/npm"
    PNPM_HOME                  = "/home/coder/.local/share/pnpm"
    XDG_CACHE_HOME             = "/cache"
    PUB_CACHE                  = "/cache/pub"
    CARGO_TARGET_DIR           = "/cache/cargo-target"
    UV_PYTHON_INSTALL_DIR      = "/cache/uv-python"
  }
}
module "zed" {
  count    = data.coder_workspace.me.start_count
  source   = "registry.coder.com/coder/zed/coder"
  version  = "1.1.5"
  agent_id = coder_agent.main.id
  folder   = "/workspaces"
}
# Builds on the host daemon, using the architecture of the Coder provisioner.
resource "docker_image" "development" {
  count        = data.coder_workspace.me.start_count
  name         = "coder-dev-workspace:${var.development_stack}-1.3.0-${local.image_hash}-${data.coder_provisioner.me.arch}"
  keep_locally = true
  build {
    context = "${path.module}/image"
    target  = var.development_stack
    build_args = {
      ENABLE_AI_AGENTS = data.coder_parameter.ai_agents.value
    }
  }
  lifecycle {
    precondition {
      condition     = var.development_stack != "flutter" || data.coder_provisioner.me.arch == "amd64"
      error_message = "The packaged Flutter SDK requires an AMD64 Linux host. Use a Python, Rust or general template on ARM64."
    }
  }
}
resource "docker_container" "workspace" {
  count        = data.coder_workspace.me.start_count
  name         = "coder-dev-${data.coder_workspace.me.id}"
  hostname     = data.coder_parameter.docker_development.value == "true" ? null : data.coder_workspace.me.name
  network_mode = data.coder_parameter.docker_development.value == "true" ? "container:${docker_container.docker_development[0].id}" : "bridge"
  image        = docker_image.development[0].image_id
  command      = ["bash", "-c", coder_agent.main.init_script]
  env          = concat(["CODER_AGENT_TOKEN=${coder_agent.main.token}"], data.coder_parameter.docker_development.value == "true" ? ["DOCKER_HOST=unix:///docker-socket/docker.sock"] : [])
  memory       = tonumber(data.coder_parameter.memory.value)
  cpu_quota    = tonumber(data.coder_parameter.cpu.value) * 100000
  cpu_period   = 100000
  restart      = "unless-stopped"
  mounts {
    type   = "volume"
    source = "coder-dev-workspaces"
    target = "/home/coder"
    volume_options {
      no_copy = true
      subpath = "${data.coder_workspace.me.id}/home"
    }
  }
  mounts {
    type   = "volume"
    source = "coder-dev-workspaces"
    target = "/workspaces"
    volume_options {
      no_copy = true
      subpath = "${data.coder_workspace.me.id}/source"
    }
  }
  mounts {
    type   = "volume"
    source = "coder-dev-caches"
    target = "/cache"
    volume_options {
      no_copy = true
      subpath = data.coder_workspace.me.id
    }
  }
  dynamic "volumes" {
    for_each = data.coder_parameter.docker_development.value == "true" ? [1] : []
    content {
      volume_name    = docker_volume.docker_socket[0].name
      container_path = "/docker-socket"
    }
  }
  depends_on = [docker_container.docker_development, docker_container.storage]
  dynamic "host" {
    for_each = data.coder_parameter.docker_development.value == "true" ? [] : [1]
    content {
      host = "host.docker.internal"
      ip   = "host-gateway"
    }
  }
  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }
}
resource "docker_volume" "docker_socket" {
  count = data.coder_parameter.docker_development.value == "true" ? 1 : 0
  name  = "coder-dev-${data.coder_workspace.me.id}-docker-socket"
}
resource "docker_volume" "docker_data" {
  count = data.coder_parameter.docker_development.value == "true" ? 1 : 0
  name  = "coder-dev-${data.coder_workspace.me.id}-docker-data"
}
resource "docker_image" "docker_development" {
  count        = data.coder_parameter.docker_development.value == "true" && data.coder_workspace.me.start_count > 0 ? 1 : 0
  name         = "docker:29.8.2-dind-rootless"
  keep_locally = true
}
# Fresh named socket volumes otherwise belong to root, preventing UID 1000
# from creating its socket. Attach waits for this one-shot initializer to exit.
resource "docker_container" "docker_permissions" {
  count        = data.coder_parameter.docker_development.value == "true" ? data.coder_workspace.me.start_count : 0
  name         = "coder-dev-${data.coder_workspace.me.id}-docker-permissions"
  image        = docker_image.development[0].image_id
  user         = "0:0"
  network_mode = "none"
  must_run     = false
  attach       = true
  entrypoint   = ["/bin/bash", "-ec"]
  command      = ["chown 1000:1000 /docker-socket /docker-data && chmod 700 /docker-socket"]
  volumes {
    volume_name    = docker_volume.docker_socket[0].name
    container_path = "/docker-socket"
  }
  volumes {
    volume_name    = docker_volume.docker_data[0].name
    container_path = "/docker-data"
  }
  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }
}
resource "docker_container" "docker_development" {
  count        = data.coder_parameter.docker_development.value == "true" ? data.coder_workspace.me.start_count : 0
  name         = "coder-dev-${data.coder_workspace.me.id}-docker"
  hostname     = data.coder_workspace.me.name
  image        = docker_image.docker_development[0].image_id
  depends_on   = [docker_container.docker_permissions, docker_container.storage]
  privileged   = true
  security_opts = var.docker_apparmor_profile == "" ? [] : ["apparmor=${var.docker_apparmor_profile}"]
  user         = "1000:1000"
  wait         = true
  wait_timeout = 180
  # Bind only a Unix socket; never introduce a Docker TCP listener.
  command = ["dockerd", "--host=unix:///run/user/1000/docker.sock"]
  env     = ["DOCKER_TLS_CERTDIR=", "DOCKER_HOST=unix:///run/user/1000/docker.sock"]
  restart = "unless-stopped"
  volumes {
    volume_name    = docker_volume.docker_socket[0].name
    container_path = "/run/user/1000"
  }
  volumes {
    volume_name    = docker_volume.docker_data[0].name
    container_path = "/home/rootless/.local/share/docker"
  }
  # Compose bind sources must exist at the same absolute paths in the daemon.
  mounts {
    type   = "volume"
    source = "coder-dev-workspaces"
    target = "/home/coder"
    volume_options {
      no_copy = true
      subpath = "${data.coder_workspace.me.id}/home"
    }
  }
  mounts {
    type   = "volume"
    source = "coder-dev-workspaces"
    target = "/workspaces"
    volume_options {
      no_copy = true
      subpath = "${data.coder_workspace.me.id}/source"
    }
  }
  mounts {
    type   = "volume"
    source = "coder-dev-caches"
    target = "/cache"
    volume_options {
      no_copy = true
      subpath = data.coder_workspace.me.id
    }
  }
  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }
  healthcheck {
    test     = ["CMD", "docker", "info"]
    interval = "10s"
    timeout  = "5s"
    retries  = 30
  }
}

# Shared named volumes belong to the store Compose deployment, not Terraform:
# destroying a workspace must not destroy its persisted files.
# Native volume subpaths require Docker Engine 26+ (API 1.45).
resource "docker_container" "storage" {
  count        = data.coder_workspace.me.start_count
  name         = "coder-dev-${data.coder_workspace.me.id}-storage"
  image        = docker_image.development[0].image_id
  user         = "0:0"
  network_mode = "none"
  must_run     = false
  attach       = true
  entrypoint   = ["/bin/bash", "-ec"]
  command      = [file("${path.module}/storage-migrate.sh")]
  env          = ["WORKSPACE_ID=${data.coder_workspace.me.id}"]
  volumes {
    host_path      = var.data_root
    container_path = "/legacy"
    read_only      = true
  }
  mounts {
    type   = "volume"
    source = "coder-dev-workspaces"
    target = "/persistent"
    volume_options { no_copy = true }
  }
  mounts {
    type   = "volume"
    source = "coder-dev-caches"
    target = "/cache-storage"
    volume_options { no_copy = true }
  }
  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }
}
