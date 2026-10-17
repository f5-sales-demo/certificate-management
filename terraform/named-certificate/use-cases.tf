variable "certificate_use_cases" {
  type = map(object({
    enabled                 = optional(bool, false)
    send_client_certificate = optional(bool, true)
    origin_sni              = optional(string)
    frontend_tls            = optional(object({ certificate_file = string, private_key_file = string }))
    name                    = string
    hostname                = string
    certificate_file        = string
    private_key_file        = string
    origin_hostname         = string
    origin_ca_file          = string
    origin_port             = optional(number, 18443)
    backend_service         = optional(object({ service_name = string, virtual_site_name = string, virtual_site_namespace = string }))
  }))
  default     = {}
  description = "Opt-in Default pool mTLS additions owned by this existing state; private files stay outside Git."
  validation {
    condition     = alltrue([for key, item in var.certificate_use_cases : key == "default-pool-mtls"])
    error_message = "This campaign stage supports default-pool-mtls; publish qualification before enabling the next case."
  }
  validation {
    condition     = length(distinct([for item in values(var.certificate_use_cases) : item.name])) == length(var.certificate_use_cases) && length(distinct([for item in values(var.certificate_use_cases) : item.hostname])) == length(var.certificate_use_cases)
    error_message = "Use distinct resource names and hostnames."
  }
  validation {
    condition     = alltrue([for item in values(var.certificate_use_cases) : item.name != var.name && item.name != "${var.name}-http" && "${item.name}-http" != var.name && "${item.name}-http" != "${var.name}-http" && item.hostname != var.domain])
    error_message = "Added cases must not adopt the retained resource names or hostname."
  }
}
module "certificate_use_cases" {
  source                  = "../http-origin-mtls"
  for_each                = { for key, item in var.certificate_use_cases : key => item if item.enabled }
  namespace               = var.namespace
  name                    = each.value.name
  domain                  = each.value.hostname
  certificate_file        = each.value.certificate_file
  private_key_file        = each.value.private_key_file
  origin_hostname         = each.value.origin_hostname
  origin_ca_file          = each.value.origin_ca_file
  origin_port             = each.value.origin_port
  backend_service         = each.value.backend_service
  serve                   = true
  send_client_certificate = each.value.send_client_certificate
  origin_sni              = each.value.origin_sni
  frontend_tls            = each.value.frontend_tls
}
output "certificate_use_case_inventory" {
  value = { for key, item in module.certificate_use_cases : key => merge(item.inventory, {
    resource_address   = "module.certificate_use_cases[\"${key}\"].${item.inventory.resource}"
    resource_addresses = [for address in concat([item.inventory.resource], item.inventory.supporting_resources) : "module.certificate_use_cases[\"${key}\"].${address}"]
    owner              = "named-certificate"
  }) }
}
