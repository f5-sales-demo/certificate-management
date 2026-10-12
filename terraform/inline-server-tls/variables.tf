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
variable "certificates" {
  type = list(object({
    id               = string
    certificate_file = string
    private_key_file = string
  }))
  description = "Ordered server chains with unique, stable identities; file paths stay private."
  validation {
    condition     = length(var.certificates) > 0 && length(distinct([for c in var.certificates : c.id])) == length(var.certificates)
    error_message = "Provide at least one certificate and unique stable IDs."
  }
}
variable "description" {
  type        = string
  description = "Operator-editable resource description."
  default     = "Native Terraform Blindfold certificate example"
}

data "xcsh_namespace" "existing" {
  name = var.namespace
}
