---
title: Client mTLS
description: Optional frontend client certificates, forwarded identity and certificate-authorized synthetic writes.
sidebar:
  order: 4
---

## Prerequisites

Complete the [server certificate workflow](../) and [Wingman runtime](../../wingman/). Use the existing
named-certificate owner state and Wingman pool. [Origin mTLS](../certificate-surfaces/origin-mtls/) authenticates the
load balancer to an origin; client mTLS authenticates a caller to the frontend. Keep their material distinct.

The retained Regional Edge endpoint cannot attach a CRL: live XC validation returned `CRL is not allowed on regional
edge sites`. Keep client mTLS disabled there until a CRL-capable CE topology is selected and qualified. The
configuration below is an unqualified implementation for that topology; it does not establish retained edge revocation.

Use Python 3 and OpenSSL 3 on Ubuntu or macOS. Store the synthetic CA database, CA key, client keys and plans in an
owner-only directory outside Git. Only public CA certificates and signed PEM CRLs enter Terraform state. Select client
file paths produced below; never reuse server, origin or Wingman key inputs.

## Configuration

Client mTLS is disabled when `client_mtls = null`. The complete HCL retains the named server certificate and existing
routes. The public JSON describes the added resources and TLS extension; encoded-material placeholders are illustrative.

[Download public JSON](../../../assets/configurations/client-mtls.json).

<div data-xcsh-context="json" data-xcsh-fields="XCSH_CLIENT_CRL_REVISION XCSH_DOMAINNAME XCSH_LB_NAME XCSH_NAMESPACE">

```json
{
  "trusted_ca_list": {
    "metadata": {
      "name": "<XCSH_LB_NAME>-client-ca",
      "namespace": "<XCSH_NAMESPACE>"
    },
    "spec": {
      "trusted_ca_url": "string:///<BASE64_CLIENT_CA_BUNDLE>"
    }
  },
  "crl": {
    "metadata": {
      "name": "<XCSH_LB_NAME>-client-<XCSH_CLIENT_CRL_REVISION>",
      "namespace": "<XCSH_NAMESPACE>"
    },
    "spec": {
      "server_address": "<XCSH_DOMAINNAME>",
      "server_port": 80,
      "refresh_interval": 6,
      "timeout": 10,
      "http_access": {
        "path": "/mtls/crl/<XCSH_CLIENT_CRL_REVISION>.pem"
      }
    }
  },
  "service_policy": {
    "metadata": {
      "name": "<XCSH_LB_NAME>-client-write",
      "namespace": "<XCSH_NAMESPACE>"
    },
    "spec": {
      "any_server": {},
      "rule_list": {
        "rules": [
          {
            "metadata": {
              "name": "deny-write-without-client-identity"
            },
            "spec": {
              "action": "DENY",
              "any_client": {},
              "http_method": {
                "methods": ["POST", "PUT", "PATCH"]
              },
              "path": {
                "exact_values": ["/mtls/write"]
              },
              "headers": [
                {
                  "name": "X-Forwarded-Client-Cert",
                  "check_not_present": {}
                }
              ],
              "waf_action": {
                "none": {}
              }
            }
          },
          {
            "metadata": {
              "name": "allow-other-traffic"
            },
            "spec": {
              "action": "ALLOW",
              "any_client": {},
              "waf_action": {
                "none": {}
              }
            }
          }
        ]
      }
    }
  },
  "https_tls_cert_params_extension": {
    "use_mtls": {
      "trusted_ca": {
        "name": "<XCSH_LB_NAME>-client-ca",
        "namespace": "<XCSH_NAMESPACE>"
      },
      "client_certificate_optional": true,
      "crl": {
        "name": "<XCSH_LB_NAME>-client-<XCSH_CLIENT_CRL_REVISION>",
        "namespace": "<XCSH_NAMESPACE>"
      },
      "xfcc_options": {
        "xfcc_header_elements": ["XFCC_CERT", "XFCC_CHAIN"]
      }
    }
  }
}
```

</div>

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
          crl {
            name      = xcsh_crl.client[use_mtls.value.active_crl_revision].name
            namespace = data.xcsh_namespace.existing.name
          }
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
  name      = "${var.wingman.name}${local.wingman_contract.suffixes.origin_pool}"
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

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR">

```bash
umask 077
configuration="$XCSH_WORKDIR/named-certificate"
mkdir -p "$configuration"
curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/named-certificate/client-mtls.tf" --output "$configuration/client-mtls.tf"
curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/named-certificate/main.tf" --output "$configuration/main.tf"
curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/named-certificate/outputs.tf" --output "$configuration/outputs.tf"
curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/named-certificate/use-cases.tf" --output "$configuration/use-cases.tf"
curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/named-certificate/variables.tf" --output "$configuration/variables.tf"
curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/named-certificate/versions.tf" --output "$configuration/versions.tf"
curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/named-certificate/wingman.tf" --output "$configuration/wingman.tf"
curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/scripts/client_pki.py" --output "$XCSH_WORKDIR/client_pki.py"
```

</div>

The retained owner already has its Wingman contract and Default pool module dependencies. For an isolated deployment,
download the same dependencies listed in the server workflow before initializing.

## Configure

Initialize a new private synthetic CA directory once, then issue a client certificate with `clientAuth`. Set Client CA
file to `ca.pem`, Client certificate/key files to `clients/<client>/certificate.pem` and `key.pem`, and Client CRL file
to `crls/<revision>.pem` under that directory.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CLIENT_CA_DIR XCSH_CLIENT_CA_FILE XCSH_CLIENT_CERT_FILE XCSH_CLIENT_CRL_FILE XCSH_CLIENT_CRL_REVISION XCSH_CLIENT_NAME XCSH_WORKDIR">

```bash
umask 077
configuration="$XCSH_WORKDIR/named-certificate"
python3 "$XCSH_WORKDIR/client_pki.py" init "$XCSH_CLIENT_CA_DIR"
python3 "$XCSH_WORKDIR/client_pki.py" issue "$XCSH_CLIENT_CA_DIR" --client "$XCSH_CLIENT_NAME"
python3 "$XCSH_WORKDIR/client_pki.py" crl "$XCSH_CLIENT_CA_DIR" --revision "$XCSH_CLIENT_CRL_REVISION"
openssl verify -purpose sslclient -CAfile "$XCSH_CLIENT_CA_FILE" "$XCSH_CLIENT_CERT_FILE"
openssl crl -in "$XCSH_CLIENT_CRL_FILE" -noout -verify -CAfile "$XCSH_CLIENT_CA_FILE"
```

</div>

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CLIENT_CA_FILE XCSH_CLIENT_CRL_FILE XCSH_CLIENT_CRL_REVISION">

```bash
python3 - "$configuration/client.auto.tfvars.json" "$XCSH_CLIENT_CA_FILE" "$XCSH_CLIENT_CRL_FILE" "$XCSH_CLIENT_CRL_REVISION" <<'PY'
# ruff: noqa: S608 -- Markdown command generation; no SQL execution.
import json
import textwrap, os, sys
os.umask(0o077)
path, ca, crl, revision = sys.argv[1:]
with open(path, "x") as stream:
    json.dump({"client_mtls": {"trusted_ca_file": ca, "crl_revisions": {revision: crl}, "active_crl_revision": revision}}, stream, indent=2)
PY
terraform -chdir="$configuration" init -upgrade
terraform -chdir="$configuration" validate
terraform -chdir="$configuration" plan -out=client.plan
terraform -chdir="$configuration" show client.plan
shasum -a 256 "$configuration/client.plan"
```

</div>

Deploy in stages: first publish the new exact HTTP CRL route, then verify its bytes and signature, then create its XC
CRL object and verify successful download/activation. Only then attach trust, active CRL and Service Policy to HTTPS.
Review and hash a fresh saved plan for every stage. Preserve earlier revisions during transitions. Reject unrelated
changes and retained-resource replacement. A target plan is a staging aid; finish with a full zero-change plan.

The policy denies POST, PUT and PATCH on exact `/mtls/write` when XFCC is absent, then allows other traffic.
Qualification must prove the edge sanitizes client-supplied XFCC before policy evaluation. The origin parser alone
cannot establish edge trust. A header bypass fails acceptance and requires rollback.

## Verify

Use a new cURL process and unique challenge for every probe. Keep server verification enabled. Match the response
challenge and `forwarded_client_certificate_sha256` to the client leaf fingerprint; `origin_server_certificate_sha256`
identifies the Wingman server certificate separately. Synthetic acknowledgments store and echo no submitted data.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CLIENT_CA_FILE XCSH_CLIENT_CERT_FILE XCSH_CLIENT_CRL_FILE XCSH_CLIENT_CRL_REVISION XCSH_CLIENT_KEY_FILE XCSH_DOMAINNAME XCSH_WORKDIR">

```bash
challenge=$(openssl rand -hex 16)
curl --silent --show-error --fail "https://$XCSH_DOMAINNAME/mtls/identity?challenge=$challenge"
openssl x509 -in "$XCSH_CLIENT_CERT_FILE" -noout -fingerprint -sha256
for method in POST PUT PATCH; do
  challenge=$(openssl rand -hex 16)
  curl --silent --show-error --fail --cert "$XCSH_CLIENT_CERT_FILE" --key "$XCSH_CLIENT_KEY_FILE" \
    --request "$method" "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
  curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' \
    --request "$method" "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
done
curl --silent --show-error --fail "http://$XCSH_DOMAINNAME/mtls/crl/$XCSH_CLIENT_CRL_REVISION.pem" --output "$XCSH_WORKDIR/downloaded-crl.pem"
cmp "$XCSH_CLIENT_CRL_FILE" "$XCSH_WORKDIR/downloaded-crl.pem"
openssl crl -in "$XCSH_WORKDIR/downloaded-crl.pem" -noout -verify -CAfile "$XCSH_CLIENT_CA_FILE"
openssl crl -in "$XCSH_WORKDIR/downloaded-crl.pem" -noout -issuer -lastupdate -nextupdate -text
terraform -chdir="$configuration" output -json client_mtls_inventory
terraform -chdir="$configuration" plan -detailed-exitcode
```

</div>

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_DOMAINNAME">

```bash
for method in POST PUT PATCH; do
  for value in 'Hash=forged' 'Cert="%zz"' 'Hash=one;Hash=two'; do
    challenge=$(openssl rand -hex 16)
    curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' \
      --request "$method" --header "X-Forwarded-Client-Cert: $value" \
      "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
  done
  challenge=$(openssl rand -hex 16)
  curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' \
    --request "$method" --header 'X-Forwarded-Client-Cert: Hash=one' \
    --header 'X-Forwarded-Client-Cert: Hash=two' \
    "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
done
```

</div>

Expect public identity HTTP 200 with an empty client fingerprint, trusted writes HTTP 200, and certificate-free or
forged-header writes HTTP 403. Require duplicate and malformed header denial, including a copied complete valid XFCC
value presented without a client certificate. Presented untrusted, expired and revoked certificates must fail TLS before
the handler returns a challenge. Do not infer revocation from an XC object or download alone.

Recheck `/get`, `/wingman/get`, all HTTP redirects outside the exact CRL paths, server fingerprints, retained resource
IDs and Default pool responses. Repeat Wingman injection, READY, authorized unseal, denial, identity chain, TLS,
restart, cleanup and credential revocation after publishing its changed image. Record client acceptance separately from
the historical certificate matrix.

## Maintain

Renew by issuing another client under the same CA with a new issuance name. It has a new serial and fingerprint; both
old and renewed certificates remain valid until explicit revocation.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CLIENT_CA_DIR XCSH_CLIENT_CRL_REVISION XCSH_CLIENT_NAME XCSH_WORKDIR">

```bash
python3 "$XCSH_WORKDIR/client_pki.py" issue "$XCSH_CLIENT_CA_DIR" --client "$XCSH_CLIENT_NAME-renewed"
python3 "$XCSH_WORKDIR/client_pki.py" revoke "$XCSH_CLIENT_CA_DIR" --client "$XCSH_CLIENT_NAME"
python3 "$XCSH_WORKDIR/client_pki.py" crl "$XCSH_CLIENT_CA_DIR" --revision "$XCSH_CLIENT_CRL_REVISION-next"
```

</div>

Add the newly signed CRL to `crl_revisions`, publish and verify its exact HTTP path, create and verify activation, then
select its revision through a fresh reviewed plan. With fresh connections, prove the old serial is rejected and only the
renewed client succeeds.

For CA rotation, initialize a separate private CA database and client. Concatenate the two public CA certificates into
the trusted bundle and both issuers' signed PEM CRLs into a new CRL revision. Verify each CRL signature against its
issuer and both validity windows. Qualify XC support for the two-issuer bundle before overlap; object creation is
insufficient. Preserve `xcsh_trusted_ca_list.client[0]` identity while adding new trust. Prove both clients work during
overlap, then remove old CA trust through a reviewed update and prove old clients fail while new clients work. Retain
prior public revisions until the transition is verified.

## Remove

Set `client_mtls = null` through a fresh reviewed plan. Remove the client policy, trust and CRL additions while
preserving the server certificate, load balancers, Wingman and Default pool additions. Verify public reads and
redirects, unchanged server fingerprints and zero-change refresh. Exercise full destroy separately on an isolated
deployment of this same configuration; never destroy the retained owner to test removal.
