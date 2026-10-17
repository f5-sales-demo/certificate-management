variable "namespace" {
  type        = string
  description = "Existing namespace; this configuration never owns it."
  default     = "demo-app"
}
variable "name" {
  type        = string
  description = "Unique name owned only by this Terraform state."
  default     = "example-tls"
}
variable "domain" {
  type        = string
  description = "Application hostname covered by the server certificate SAN."
  default     = "tls.example.com"
}
variable "certificate_file" {
  type        = string
  description = "Absolute path to a leaf-first PEM chain outside Git."
}
variable "private_key_file" {
  type        = string
  description = "Absolute path to the matching private PEM key outside Git."
}
variable "description" {
  type        = string
  description = "Operator-editable resource description."
  default     = "Native Terraform Blindfold certificate example"
}

data "xcsh_namespace" "existing" {
  name = var.namespace
}
variable "origin_hostname" {
  type        = string
  description = "Existing reachable origin hostname; certificate must allow clientAuth for mTLS."
}
variable "origin_ca_file" {
  type        = string
  description = "Public PEM trust anchor for the origin server. Verification remains enabled."
}

variable "serve" {
  type        = bool
  default     = false
  description = "Opt in to public HTTP advertisement and the concrete /get default-pool route."
}
variable "origin_port" {
  type        = number
  default     = 443
  description = "Owned backend listener port."
}
variable "backend_service" {
  type        = object({ service_name = string, virtual_site_name = string, virtual_site_namespace = string })
  default     = null
  description = "Explicit runtime-owned service and configured virtual site; no site discovery."
}

variable "send_client_certificate" {
  type        = bool
  default     = true
  description = "Disable only for a reviewed missing-client negative-control plan."
}
variable "origin_sni" {
  type        = string
  default     = null
  description = "Optional explicit TLS hostname; DNS origin address remains independent."
}

variable "frontend_tls" {
  type        = object({ certificate_file = string, private_key_file = string })
  default     = null
  description = "Optional distinct downstream server material for trusted public qualification traffic."
}
