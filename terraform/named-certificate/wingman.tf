# Disabled by default. Enable only after real Wingman backend qualification.
variable "wingman" {
  type = object({
    name              = string
    virtual_site_name = string
    trusted_ca_file   = optional(string)
    origin_pool_name  = optional(string)
  })
  default     = null
  description = "Runtime owner_integration output, after authorized unseal and denial qualification."
}
variable "wingman_contract_file" {
  type        = string
  default     = null
  description = "Optional explicit contract path when applying from a private owner directory."
}
locals {
  wingman_contract = var.wingman == null ? null : jsondecode(file(var.wingman_contract_file == null ? "${path.module}/../../wingman/contract.json" : var.wingman_contract_file))
}
resource "xcsh_origin_pool" "wingman" {
  count     = var.wingman == null ? 0 : 1
  name      = var.wingman.origin_pool_name == null ? "${var.wingman.name}${local.wingman_contract.suffixes.origin_pool}" : var.wingman.origin_pool_name
  namespace = data.xcsh_namespace.existing.name
  port      = local.wingman_contract.backend_port
  origin_servers {
    k8s_service {
      protocol      = "PROTOCOL_TCP"
      service_name  = "${var.wingman.name}${local.wingman_contract.suffixes.service}.${var.namespace}"
      vk8s_networks = {}
      site_locator {
        virtual_site {
          name      = var.wingman.virtual_site_name
          namespace = data.xcsh_namespace.existing.name
        }
      }
    }
  }
  use_tls {
    sni     = var.domain
    no_mtls = {}
    tls_config {
      default_security = {}
    }
    use_server_verification {
      trusted_ca_url = "string:///${filebase64(var.wingman.trusted_ca_file == null ? var.certificate_file : var.wingman.trusted_ca_file)}"
    }
  }
}
output "wingman_endpoint" {
  value = var.wingman == null ? null : "https://${var.domain}${local.wingman_contract.route_prefix}get"
}
