variable "data_root" {
  type        = string
  description = "Absolute RunTipi app-data directory on the Docker host (injected by bootstrap)."
  validation {
    condition     = startswith(var.data_root, "/") && !strcontains(var.data_root, "..")
    error_message = "data_root must be an absolute host directory without traversal."
  }
}
variable "git_name" {
  type    = string
  default = ""
}
variable "git_email" {
  type    = string
  default = ""
}
variable "development_stack" {
  type        = string
  default     = "general"
  description = "Workspace image target, selected by the published template."
  validation {
    condition     = contains(["general", "python", "rust", "flutter"], var.development_stack)
    error_message = "Select general, python, rust or flutter."
  }
}

variable "docker_apparmor_profile" {
  type        = string
  default     = ""
  description = "Optional host-loaded AppArmor profile for the rootless Docker sidecar."
  validation {
    condition     = var.docker_apparmor_profile == "" || can(regex("^[a-zA-Z0-9_.-]+$", var.docker_apparmor_profile))
    error_message = "Use a simple host-loaded profile name, or leave empty."
  }
}
