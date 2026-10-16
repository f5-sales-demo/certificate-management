variable "namespace" {
  type        = string
  default     = null
  description = "Existing namespace; bootstrap and runtime must agree."
}
variable "name" {
  type        = string
  default     = null
  description = "Naming base shared with bootstrap and the existing Terraform owner."
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
  description = "Published immutable Wingman application image."
  validation {
    condition     = can(regex("^ghcr.io/f5-sales-demo/certificate-management-wingman@sha256:[a-f0-9]{64}$", var.application_image))
    error_message = "Supply the governed application image by SHA-256 digest."
  }
}
variable "certificate_file" {
  type        = string
  description = "Absolute private path to the existing public PEM chain."
}
variable "private_key_file" {
  type        = string
  description = "Absolute private path to the existing matching PEM key. Never mount the plaintext key."
}
variable "domain" {
  type        = string
  default     = "certificate-management-terraform.f5-sales-demo.com"
  description = "Existing application hostname covered by the shared certificate."
}

variable "xcsh_encrypted_location_file" {
  type        = string
  default     = ""
  description = "Private path to a separate xcsh-prepared Wingman-policy encrypted location for cross-tool qualification. Never supply retained certificate ciphertext from another policy."
}
