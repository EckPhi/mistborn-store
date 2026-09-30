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
