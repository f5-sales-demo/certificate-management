---
title: Terraform — Configuration
description: Configuration for the Terraform certificate workflow.
sidebar:
  label: Configuration
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../prerequisites/
  label: Prerequisites
next:
  link: ../configure/
  label: Configure
---

<!-- generated-configuration -->
The JSON below shows the complete public configuration resulting from native encryption, with encoded public chains and encrypted-key placeholders. API defaults and provider provenance may add fields. Never apply encoded-material placeholders. HCL includes the complete canonical root; download its files separately.

[Download JSON](../../../assets/configurations/named-certificate.json).

## Public JSON

<div data-xcsh-context="json" data-xcsh-fields="XCSH_DOMAINNAME XCSH_LB_NAME XCSH_NAMESPACE">

```json
[
  {
    "metadata": {
      "name": "<XCSH_LB_NAME>",
      "namespace": "<XCSH_NAMESPACE>",
      "description": "Native Terraform Blindfold certificate example",
      "labels": {
        "certificate-example": "terraform"
      }
    },
    "spec": {
      "certificate_url": "string:///<BASE64_PUBLIC_CHAIN>",
      "private_key": {
        "blindfold_secret_info": {
          "location": "string:///<ENCRYPTED_KEY>"
        }
      }
    }
  },
  {
    "metadata": {
      "name": "<XCSH_LB_NAME>",
      "namespace": "<XCSH_NAMESPACE>",
      "description": "Native Terraform Blindfold certificate example",
      "labels": {
        "certificate-example": "terraform"
      }
    },
    "spec": {
      "domains": ["<XCSH_DOMAINNAME>"],
      "advertise_on_public_default_vip": {},
      "disable_waf": {},
      "no_service_policies": {},
      "disable_api_definition": {},
      "disable_api_discovery": {},
      "disable_bot_defense": {},
      "disable_rate_limit": {},
      "disable_ip_reputation": {},
      "disable_malicious_user_detection": {},
      "https": {
        "port": 443,
        "tls_cert_params": {
          "no_mtls": {},
          "tls_config": {
            "default_security": {}
          },
          "certificates": [
            {
              "name": "<XCSH_LB_NAME>",
              "namespace": "<XCSH_NAMESPACE>"
            }
          ]
        }
      },
      "routes": [
        {
          "direct_response_route": {
            "http_method": "GET",
            "path": {
              "path": "/get"
            },
            "route_direct_response": {
              "response_code": 200,
              "response_body_encoded": "string:///eyJleGFtcGxlIjoidGVycmFmb3JtLWNlcnRpZmljYXRlIiwibmF0aXZlX2JsaW5kZm9sZCI6dHJ1ZX0="
            }
          }
        }
      ]
    }
  },
  {
    "metadata": {
      "name": "<XCSH_LB_NAME>-http",
      "namespace": "<XCSH_NAMESPACE>",
      "description": "Native Terraform Blindfold certificate example",
      "labels": {
        "certificate-example": "terraform"
      }
    },
    "spec": {
      "domains": ["<XCSH_DOMAINNAME>"],
      "advertise_on_public_default_vip": {},
      "disable_waf": {},
      "no_service_policies": {},
      "disable_api_definition": {},
      "disable_api_discovery": {},
      "disable_bot_defense": {},
      "disable_rate_limit": {},
      "disable_ip_reputation": {},
      "disable_malicious_user_detection": {},
      "http": {
        "port": 80,
        "dns_volterra_managed": true
      },
      "routes": [
        {
          "redirect_route": {
            "http_method": "ANY",
            "path": {
              "prefix": "/"
            },
            "route_redirect": {
              "proto_redirect": "https",
              "host_redirect": "<XCSH_DOMAINNAME>",
              "response_code": 301
            }
          }
        }
      ]
    }
  }
]
```

</div>

## Complete HCL

<div data-xcsh-context="hcl" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL">

```hcl
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
          invert_matcher    = false
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
    resource_addresses       = ["xcsh_trusted_ca_list.client[0]", "xcsh_service_policy.client_write[0]"]
    certificate_roles        = { frontend = "xcsh_certificate.server", client_trust = "xcsh_trusted_ca_list.client[0]", origin = "xcsh_origin_pool.wingman[0]" }
    endpoints                = { identity = "https://${var.domain}/mtls/identity", write = "https://${var.domain}/mtls/write" }
    trusted_ca_bundle_sha256 = filesha256(var.client_mtls.trusted_ca_file)
    published_crl_revision   = var.client_mtls.active_crl_revision
    edge_revocation          = "unsupported on Regional Edges; no_crl selected"
    crls                     = { for revision, path in local.client_crls : revision => { url = "http://${var.domain}/mtls/crl/${revision}.pem", sha256 = filesha256(path) } }
    acceptance               = "Requires separate live authorization and CA-rotation receipts; Regional Edge CRL revocation is excluded."
  }
}
resource "xcsh_certificate" "server" {
  name        = var.name
  namespace   = data.xcsh_namespace.existing.name
  description = var.description
  labels      = { certificate-example = "terraform" }
  blindfold   = { certificate_file = var.certificate_file, private_key_file = var.private_key_file }
}

resource "xcsh_http_loadbalancer" "https" {
  name                             = var.name
  namespace                        = data.xcsh_namespace.existing.name
  description                      = var.description
  labels                           = { certificate-example = "terraform" }
  domains                          = [var.domain]
  advertise_on_public_default_vip  = {}
  disable_waf                      = {}
  no_service_policies              = var.client_mtls == null ? {} : null
  disable_api_definition           = {}
  disable_api_discovery            = {}
  disable_bot_defense              = {}
  disable_rate_limit               = {}
  disable_ip_reputation            = {}
  disable_malicious_user_detection = {}
  dynamic "active_service_policies" {
    for_each = var.client_mtls == null ? [] : [1]
    content {
      policies {
        name      = xcsh_service_policy.client_write[0].name
        namespace = data.xcsh_namespace.existing.name
      }
    }
  }
  lifecycle {
    precondition {
      condition     = var.client_mtls == null || var.wingman != null
      error_message = "Qualify and configure the Wingman origin before enabling client mTLS."
    }
  }
  https {
    port = 443
    tls_cert_params {
      no_mtls = var.client_mtls == null ? {} : null
      dynamic "use_mtls" {
        for_each = var.client_mtls == null ? [] : [var.client_mtls]
        content {
          client_certificate_optional = true
          trusted_ca {
            name      = xcsh_trusted_ca_list.client[0].name
            namespace = data.xcsh_namespace.existing.name
          }
          no_crl = {}
          xfcc_options {
            xfcc_header_elements = ["XFCC_CERT", "XFCC_CHAIN"]
          }
        }
      }
      tls_config {
        default_security = {}
      }
      certificates {
        name      = xcsh_certificate.server.name
        namespace = data.xcsh_namespace.existing.name
      }
    }
  }
  routes {
    direct_response_route {
      http_method = "GET"
      path {
        path = "/get"
      }
      route_direct_response {
        response_code         = 200
        response_body_encoded = "string:///${base64encode(jsonencode({ example = "terraform-certificate", native_blindfold = true }))}"
      }
    }
  }
  dynamic "routes" {
    for_each = var.wingman == null ? [] : [var.wingman]
    content {
      simple_route {
        http_method          = "GET"
        disable_host_rewrite = {}
        path {
          prefix = local.wingman_contract.route_prefix
        }
        origin_pools {
          weight   = 1
          priority = 1
          pool {
            name      = xcsh_origin_pool.wingman[0].name
            namespace = data.xcsh_namespace.existing.name
          }
        }
      }
    }
  }

  dynamic "routes" {
    for_each = var.client_mtls == null ? [] : ["/mtls/identity", "/mtls/write"]
    content {
      simple_route {
        http_method          = "ANY"
        disable_host_rewrite = {}
        path { path = routes.value }
        origin_pools {
          weight   = 1
          priority = 1
          pool {
            name      = xcsh_origin_pool.wingman[0].name
            namespace = data.xcsh_namespace.existing.name
          }
        }
      }
    }
  }

}

resource "xcsh_http_loadbalancer" "http" {
  name                             = "${var.name}-http"
  namespace                        = data.xcsh_namespace.existing.name
  description                      = var.description
  labels                           = { certificate-example = "terraform" }
  domains                          = [var.domain]
  advertise_on_public_default_vip  = {}
  disable_waf                      = {}
  no_service_policies              = {}
  disable_api_definition           = {}
  disable_api_discovery            = {}
  disable_bot_defense              = {}
  disable_rate_limit               = {}
  disable_ip_reputation            = {}
  disable_malicious_user_detection = {}
  http {
    port                 = 80
    dns_volterra_managed = true
  }
  dynamic "routes" {
    for_each = local.client_crls
    content {
      direct_response_route {
        http_method = "GET"
        path { path = "/mtls/crl/${routes.key}.pem" }
        route_direct_response {
          response_code         = 200
          response_body_encoded = "string:///${filebase64(routes.value)}"
        }
      }
    }
  }
  routes {
    redirect_route {
      http_method = "ANY"
      path {
        prefix = "/"
      }
      route_redirect {
        proto_redirect = "https"
        host_redirect  = var.domain
        response_code  = 301
      }
    }
  }
}
output "endpoint" {
  value = "https://${var.domain}/get"
}
output "certificate_fingerprint" {
  value = xcsh_certificate.server.blindfold.fingerprint
}
output "certificate_expiration" {
  value = xcsh_certificate.server.blindfold.expires_at
}
output "encryption_context_digest" {
  value = xcsh_certificate.server.blindfold.context_digest
}
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
terraform {
  required_version = null
  required_providers {
    xcsh = {
      source  = "f5-sales-demo/xcsh"
      version = ">= 0"
    }
  }
}

# XCSH_API_URL and XCSH_API_TOKEN configure the provider, without a CLI.
provider "xcsh" {}
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
```

</div>

<!-- /generated-configuration -->

