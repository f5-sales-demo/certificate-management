---
title: Terraform
description: Prepare certificate keys with native Blindfold and deploy HTTPS using Terraform.
sidebar:
  label: Certificate workflow
  order: 3
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Deploy a named certificate and HTTPS load balancer with native provider encryption. The HTTP companion maintains managed Domain Name System (DNS) records and redirects requests to HTTPS. A built-in JavaScript Object Notation (JSON) response identifies the example; you need no origin service or xcsh installation.

## Prerequisites

Install the current published Terraform and
**`f5-sales-demo/xcsh` provider** artifacts. The provider supports Terraform 1.11 or later for write-only inputs.
See the [current qualification receipt](../../assets/current-artifacts.json) for resolved versions, digests, source commits, and the status of live gates. Provide an existing namespace, certificate permissions, load-balancer capacity, and a hostname in a tenant-managed
DNS zone. Terraform reads the namespace as a data source and never owns it.

Set `<XCSH_API_URL>` to your tenant console URL and supply a session credential. These are **provider environment settings**, independent of the xcsh command-line interface (CLI).

Keep credentials out of HashiCorp Configuration Language (HCL), variable files, and plans. Leave credentials blank in Customize examples to use shell environment values or a private prompt. Entered credentials appear in displayed/copied shell commands; avoid recording them in shell history:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_API_URL XCSH_API_TOKEN">

```bash
if [ -z "${XCSH_API_TOKEN:-}" ]; then
  read -r -s -p 'API token: ' XCSH_API_TOKEN
  printf '\n'
fi
export XCSH_API_URL="$XCSH_API_URL"
export XCSH_API_TOKEN
```

</div>

[HCL source](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/named-certificate) is authoritative. Use a dedicated private working directory and state for each example. Review the [certificate surfaces](./certificate-surfaces/) before selecting a prerequisite-bound configuration.

## Configuration

<!-- generated-configuration -->
The JSON below shows the complete public configuration resulting from native encryption, with encoded public chains and encrypted-key placeholders. API defaults and provider provenance may add fields. Never apply encoded-material placeholders. HCL includes the complete canonical root; download its files separately.

[Download JSON](../../assets/configurations/named-certificate.json).

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

<!-- /generated-configuration -->

Select an existing leaf-first Privacy Enhanced Mail (PEM) chain and matching key, or create self-signed material outside Git. The following recipe creates
a Rivest–Shamir–Adleman (RSA) 2048-bit self-signed server certificate valid for 3650 days. Select `<XCSH_WORKDIR>`, `<XCSH_CERT_FILE>`, and `<XCSH_KEY_FILE>` as absolute paths outside Git. Create the parent directories for those files first. Replace `<XCSH_DOMAINNAME>` and `<XCSH_COMPANION_DOMAINNAME>` with names you own.
OpenSSL generates inputs; the provider prepares and encrypts them without calling OpenSSL, xcsh, or vesctl.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE XCSH_LB_NAME XCSH_DOMAINNAME XCSH_COMPANION_DOMAINNAME XCSH_WORKDIR XCSH_CERT_FILE XCSH_KEY_FILE">

```bash
umask 077
mkdir -p "$XCSH_WORKDIR/material" "$XCSH_WORKDIR/deployment" "$(dirname "$XCSH_CERT_FILE")" "$(dirname "$XCSH_KEY_FILE")"
chmod 700 "$XCSH_WORKDIR" "$XCSH_WORKDIR/material" "$XCSH_WORKDIR/deployment"
openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 3650 \
  -subj "/CN=$XCSH_DOMAINNAME" \
  -addext 'basicConstraints=critical,CA:false' \
  -addext 'keyUsage=critical,digitalSignature,keyEncipherment' \
  -addext 'extendedKeyUsage=serverAuth' \
  -addext "subjectAltName=DNS:$XCSH_DOMAINNAME,DNS:$XCSH_COMPANION_DOMAINNAME" \
  -keyout "$XCSH_KEY_FILE" \
  -out "$XCSH_CERT_FILE"
```

</div>

Use these same local files in a separately owned xcsh example if needed. Each tool must manage its own XC resource name and references. Shared material does not imply shared resource ownership. Interception requires a separate signing certificate authority (CA); use the [CA recipe](./input-lifecycle/#interception-signing-ca).

## Configure

### Review a saved plan

Copy the configuration into the private deployment directory. The provider uses `blindfold.certificate_file` and `blindfold.private_key_file`,
retrieves the tenant public key and default `shared/ves-io-allow-volterra` policy, and computes the encrypted key location. Leave `certificate_url`,
`private_key`, and `blindfold.encrypted_location` unset.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_API_URL XCSH_API_TOKEN XCSH_NAMESPACE XCSH_LB_NAME XCSH_DOMAINNAME XCSH_CERT_FILE XCSH_KEY_FILE">

```bash
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_LB_NAME"
export TF_VAR_domain="$XCSH_DOMAINNAME"
export TF_VAR_certificate_file="$XCSH_CERT_FILE"
export TF_VAR_private_key_file="$XCSH_KEY_FILE"
for file in client-mtls.tf main.tf outputs.tf use-cases.tf variables.tf versions.tf wingman.tf; do
  curl --silent --show-error --fail \
    "https://f5-sales-demo.github.io/certificate-management/_data/terraform/named-certificate/$file" \
    --output "$XCSH_WORKDIR/deployment/$file"
done
terraform -chdir="$XCSH_WORKDIR/deployment" init -upgrade
terraform -chdir="$XCSH_WORKDIR/deployment" validate
terraform -chdir="$XCSH_WORKDIR/deployment" plan \
  -out="$XCSH_WORKDIR/deployment/create.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" show \
  "$XCSH_WORKDIR/deployment/create.plan"
```

</div>

Hash the reviewed plan with `shasum -a 256 "$XCSH_WORKDIR/deployment/create.plan"`. Expect one named certificate, one HTTPS load balancer, one HTTP DNS companion, and a namespace read. Confirm the names, hostname, references, and
ownership before applying. Protect the dependency lockfile, saved plans, state, and logs. They contain encrypted material and local paths. Read
[saved-plan input changes](./input-lifecycle/#saved-plans) before changing files after planning.

### Apply the configuration

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_API_URL XCSH_API_TOKEN XCSH_NAMESPACE XCSH_LB_NAME XCSH_DOMAINNAME XCSH_CERT_FILE XCSH_KEY_FILE">

```bash
terraform -chdir="$XCSH_WORKDIR/deployment" apply \
  "$XCSH_WORKDIR/deployment/create.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" output
```

</div>

Expect endpoint, SHA-256 certificate fingerprint, expiration, and encryption-context digest outputs. The provider does not expose plaintext private keys. The companion owns only this hostname’s managed DNS association; the configuration does not replace the tenant DNS zone.

## Verify

Check trust, hostname, the served leaf fingerprint, HTTP status, and response content. Self-signed certificates require explicit trust; use your public chain as the trust asset.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_DOMAINNAME XCSH_WORKDIR XCSH_CERT_FILE XCSH_API_URL XCSH_API_TOKEN XCSH_NAMESPACE XCSH_LB_NAME XCSH_KEY_FILE">

```bash
openssl s_client -connect "$XCSH_DOMAINNAME:443" \
  -servername "$XCSH_DOMAINNAME" -verify_hostname "$XCSH_DOMAINNAME" \
  -verify_return_error -CAfile "$XCSH_CERT_FILE" -showcerts \
  < /dev/null > "$XCSH_WORKDIR/handshake.txt" \
  2> "$XCSH_WORKDIR/handshake.err"
openssl x509 -in "$XCSH_CERT_FILE" -noout -sha256 -fingerprint \
  > "$XCSH_WORKDIR/expected.sha256"
openssl x509 -in "$XCSH_WORKDIR/handshake.txt" -noout -sha256 -fingerprint \
  > "$XCSH_WORKDIR/served.sha256"
cmp "$XCSH_WORKDIR/expected.sha256" "$XCSH_WORKDIR/served.sha256"
curl --silent --show-error --fail --cacert "$XCSH_CERT_FILE" \
  "https://$XCSH_DOMAINNAME/get" --output "$XCSH_WORKDIR/response.json" \
  --write-out '%{http_code}\n'
python3 -c 'import json,sys; assert json.load(open(sys.argv[1])) == {"example":"terraform-certificate","native_blindfold":True}' \
  "$XCSH_WORKDIR/response.json"
terraform -chdir="$XCSH_WORKDIR/deployment" plan -detailed-exitcode
```

</div>

Expect matching fingerprints, HTTP `200`, the identifying JSON object, and exit `0` with **No changes** after a new Terraform process. Exit `2` means a change; exit `1` means an error. Allow propagation and retry verification if a replacement has not reached the serving edge.

## Maintain

Keep the key algorithm unchanged when renewing a referenced certificate. Retain the old pair privately for rollback. Generate or obtain new matching material, validate it, then replace both configured inputs before making a new saved plan.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_RENEWED_CERT_FILE XCSH_RENEWED_KEY_FILE XCSH_API_URL XCSH_API_TOKEN XCSH_NAMESPACE XCSH_LB_NAME XCSH_DOMAINNAME">

```bash
export TF_VAR_certificate_file="$XCSH_RENEWED_CERT_FILE"
export TF_VAR_private_key_file="$XCSH_RENEWED_KEY_FILE"
terraform -chdir="$XCSH_WORKDIR/deployment" plan \
  -out="$XCSH_WORKDIR/deployment/renew.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" show \
  "$XCSH_WORKDIR/deployment/renew.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" apply \
  "$XCSH_WORKDIR/deployment/renew.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" plan -detailed-exitcode
```

</div>

Expect one material update followed by exit `0`. Select the renewed certificate and key as `<XCSH_CERT_FILE>` and `<XCSH_KEY_FILE>` in Customize examples before repeating the strict verification commands and compare the served
fingerprint. If xcsh uses the same inputs, rotate its separately owned certificate once after Terraform verification, preserving its metadata,
options, name, and references. Keep its previous saved manifest privately.

## Remove

Run cleanup only when you choose to retire your Terraform deployment. Review the saved destruction plan: it must contain only resources owned by this state, with no namespace or xcsh resource deletion.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_API_TOKEN XCSH_WORKDIR XCSH_API_URL XCSH_NAMESPACE XCSH_LB_NAME XCSH_DOMAINNAME XCSH_CERT_FILE XCSH_KEY_FILE">

```bash
terraform -chdir="$XCSH_WORKDIR/deployment" plan -destroy \
  -out="$XCSH_WORKDIR/deployment/destroy.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" show \
  "$XCSH_WORKDIR/deployment/destroy.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" apply \
  "$XCSH_WORKDIR/deployment/destroy.plan"
unset XCSH_API_TOKEN
```

</div>

See the [input and lifecycle reference](./input-lifecycle/) for protected files, write-only values, import, drift, and key-algorithm cutovers.
