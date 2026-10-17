variable "namespace" {
  type        = string
  description = "Existing namespace; qualification never owns it."
}
variable "name" {
  type        = string
  description = "Existing runtime naming base; qualification never owns retained resources."
}
variable "kubeconfig_file" {
  type        = string
  description = "Absolute path to a one-day scoped kubeconfig in private session storage."
  validation {
    condition     = startswith(var.kubeconfig_file, "/")
    error_message = "An explicit absolute kubeconfig path is required."
  }
}
variable "kubeconfig_context" {
  type        = string
  description = "Explicit context from the scoped kubeconfig; never use the ambient context."
}
variable "application_image" {
  type        = string
  description = "Published governed Wingman application image."
  validation {
    condition     = can(regex("^ghcr.io/f5-sales-demo/certificate-management-wingman(:latest|@sha256:[a-f0-9]{64})$", var.application_image))
    error_message = "Supply the governed latest application image or an immutable SHA-256 reference."
  }
}
variable "domain" {
  type        = string
  description = "Hostname covered by the existing application certificate."
}
variable "run_id" {
  type        = string
  description = "Unique private run identity; use a new state directory for each run."
  validation {
    condition     = can(regex("^wingman-q-[a-f0-9]{12}$", var.run_id))
    error_message = "Use wingman-q- followed by twelve random lowercase hexadecimal characters."
  }
}
