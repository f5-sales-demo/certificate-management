variable "client_mtls" {
  type = object({
    trusted_ca_file     = string
    crl_revisions       = map(string)
    active_crl_revision = string
  })
  default     = null
  description = "Optional frontend client trust and public signed PEM CRLs. Private CA/client keys and issuance databases never enter Terraform."
  validation {
    condition     = var.client_mtls == null ? true : contains(keys(var.client_mtls.crl_revisions), var.client_mtls.active_crl_revision)
    error_message = "The active CRL revision must exist in crl_revisions."
  }
  validation {
    condition     = var.client_mtls == null ? true : alltrue([for revision in keys(var.client_mtls.crl_revisions) : can(regex("^[a-z0-9][a-z0-9-]{0,31}$", revision))])
    error_message = "CRL revisions must be immutable lower-case DNS labels of at most 32 characters."
  }
}

locals {
  client_crls = var.client_mtls == null ? {} : var.client_mtls.crl_revisions
}

resource "xcsh_trusted_ca_list" "client" {
  count          = var.client_mtls == null ? 0 : 1
  name           = "${var.name}-client-ca"
  namespace      = data.xcsh_namespace.existing.name
  trusted_ca_url = "string:///${filebase64(var.client_mtls.trusted_ca_file)}"
}

# The HTTP revision must already be downloadable before XC creates the CRL.
# Publication and activation are separate deployment/traffic acceptance gates.
resource "xcsh_crl" "client" {
  for_each         = local.client_crls
  name             = "${var.name}-client-${each.key}"
  namespace        = data.xcsh_namespace.existing.name
  server_address   = var.domain
  server_port      = 80
  refresh_interval = 6
  timeout          = 10
  http_access {
    path = "/mtls/crl/${each.key}.pem"
  }
  depends_on = [xcsh_http_loadbalancer.http]
}

resource "xcsh_service_policy" "client_write" {
  count      = var.client_mtls == null ? 0 : 1
  name       = "${var.name}-client-write"
  namespace  = data.xcsh_namespace.existing.name
  any_server = {}
  rule_list {
    rules {
      metadata {
        name = "deny-write-without-client-identity"
      }
      spec {
        action     = "DENY"
        any_client = {}
        http_method {
          methods = ["POST", "PUT", "PATCH"]
        }
        path {
          exact_values = ["/mtls/write"]
        }
        headers {
          name              = "X-Forwarded-Client-Cert"
          check_not_present = {}
        }
        waf_action {
          none = {}
        }
      }
    }
    rules {
      metadata {
        name = "allow-other-traffic"
      }
      spec {
        action     = "ALLOW"
        any_client = {}
        waf_action {
          none = {}
        }
      }
    }
  }
}

output "client_mtls_inventory" {
  value = var.client_mtls == null ? null : {
    owner                    = "named-certificate"
    resource_addresses       = concat(["xcsh_trusted_ca_list.client[0]", "xcsh_service_policy.client_write[0]"], [for revision in sort(keys(local.client_crls)) : "xcsh_crl.client[\"${revision}\"]"])
    certificate_roles        = { frontend = "xcsh_certificate.server", client_trust = "xcsh_trusted_ca_list.client[0]", origin = "xcsh_origin_pool.wingman[0]" }
    endpoints                = { identity = "https://${var.domain}/mtls/identity", write = "https://${var.domain}/mtls/write" }
    trusted_ca_bundle_sha256 = filesha256(var.client_mtls.trusted_ca_file)
    active_crl_revision      = var.client_mtls.active_crl_revision
    crls                     = { for revision, path in local.client_crls : revision => { url = "http://${var.domain}/mtls/crl/${revision}.pem", sha256 = filesha256(path) } }
    acceptance               = "Requires separate live authorization, revocation and CA-rotation receipts."
  }
}
