locals {
  contract  = jsondecode(file("${path.module}/../contract.json"))
  namespace = var.namespace == null ? local.contract.namespace : var.namespace
  base_name = var.name == null ? local.contract.base_name : var.name
  names     = { for key, suffix in local.contract.suffixes : key => "${local.base_name}${suffix}" }
}
variable "namespace" {
  type        = string
  default     = null
  description = "Existing namespace; this state never owns it."
}
variable "name" {
  type        = string
  default     = null
  description = "Naming base shared with runtime and the existing Terraform owner."
}
variable "site_selector" {
  type        = string
  default     = null
  description = "Existing Toronto RE label. Verify exactly one selected site and effective quota before applying."
}
data "xcsh_namespace" "existing" {
  name = local.namespace
}
resource "xcsh_secret_policy" "application" {
  name                  = local.names.policy
  namespace             = data.xcsh_namespace.existing.name
  description           = "Wingman application TLS authorization"
  allow_f5xc            = true
  decrypt_cache_timeout = "30s"
  rules = [
    {
      name            = "allow-application"
      action          = "ALLOW"
      client_selector = ["${local.contract.app_label}=${local.names.application}"]
    },
    { name = "deny-all", action = "DENY" }
  ]
}
resource "xcsh_virtual_site" "toronto" {
  name      = local.names.virtual_site
  namespace = data.xcsh_namespace.existing.name
  site_type = "REGIONAL_EDGE"
  site_selector {
    expressions = [var.site_selector == null ? local.contract.site_selector : var.site_selector]
  }
}
resource "xcsh_virtual_k8s" "application" {
  name      = local.names.virtual_k8s
  namespace = data.xcsh_namespace.existing.name
  vsite_refs {
    name      = xcsh_virtual_site.toronto.name
    namespace = data.xcsh_namespace.existing.name
  }
}
output "runtime_contract" {
  value = {
    namespace = local.namespace
    name      = local.base_name
    policy    = "${local.namespace}/${xcsh_secret_policy.application.name}"
    vk8s      = xcsh_virtual_k8s.application.name
  }
}

output "vk8s_name" {
  value = xcsh_virtual_k8s.application.name
}
output "policy" {
  value = "${local.namespace}/${xcsh_secret_policy.application.name}"
}
