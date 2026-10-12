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
variable "virtual_site_name" {
  type        = string
  description = "Existing CE virtual site with workload capacity; no site is created here."
}
variable "virtual_site_namespace" {
  type        = string
  description = "Namespace of that existing virtual site."
}
variable "image" {
  type        = string
  description = "Container image available on your authorized CE sites."
  default     = "nginx:alpine"
}
