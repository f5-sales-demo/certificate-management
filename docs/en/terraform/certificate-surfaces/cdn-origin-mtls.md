---
title: CDN origin mTLS
sidebar:
  order: 2
---

## Prerequisites

Install the latest Terraform and provider releases. Set the [provider environment](../../#prerequisites) and keep private inputs and state outside Git. Copy this configuration into its own directory and state; never reuse another owner's name.

Supply a reachable origin that requires client authentication, a matching client certificate with `clientAuth` usage, and its public server trust CA. Server-only certificates cannot authenticate a client.

## Configuration

The JSON below shows the complete public configuration resulting from native encryption, with encoded public chains and encrypted-key placeholders. API defaults and provider provenance may add fields. Never apply encoded-material placeholders. HCL includes the complete canonical root; download its files separately.

[Download JSON](../../../../assets/configurations/cdn-origin-mtls.json).

<div data-xcsh-context="json" data-xcsh-fields="XCSH_DOMAINNAME XCSH_LB_NAME XCSH_NAMESPACE XCSH_ORIGIN_HOSTNAME">

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
      "domains": ["<XCSH_DOMAINNAME>"],
      "no_service_policies": {},
      "disable_waf": {},
      "disable_api_definition": {},
      "disable_api_discovery": {},
      "disable_rate_limit": {},
      "disable_ip_reputation": {},
      "disable_malicious_user_detection": {},
      "disable_client_side_defense": {},
      "disable_threat_mesh": {},
      "no_challenge": {},
      "system_default_timeouts": {},
      "user_id_client_ip": {},
      "default_sensitive_data_policy": {},
      "l7_ddos_action_default": {},
      "origin_pool": {
        "origin_request_timeout": "60s",
        "origin_servers": [
          {
            "port": 443,
            "public_name": {
              "dns_name": "<XCSH_ORIGIN_HOSTNAME>"
            }
          }
        ],
        "use_tls": {
          "sni": "<XCSH_ORIGIN_HOSTNAME>",
          "tls_config": {
            "default_security": {}
          },
          "use_mtls": {
            "tls_certificates": [
              {
                "certificate_url": "string:///<BASE64_PUBLIC_CHAIN>",
                "private_key": {
                  "blindfold_secret_info": {
                    "location": "string:///<ENCRYPTED_KEY>"
                  }
                }
              }
            ]
          },
          "use_server_verification": {
            "trusted_ca_url": "string:///<BASE64_ORIGIN_CA>"
          }
        }
      },
      "http": {
        "port": 80
      }
    }
  }
]
```

</div>

<div data-xcsh-context="hcl" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL">

```hcl
resource "xcsh_cdn_loadbalancer" "example" {
  name                             = var.name
  namespace                        = data.xcsh_namespace.existing.name
  description                      = var.description
  labels                           = { certificate-example = "terraform" }
  domains                          = [var.domain]
  no_service_policies              = {}
  disable_waf                      = {}
  disable_api_definition           = {}
  disable_api_discovery            = {}
  disable_rate_limit               = {}
  disable_ip_reputation            = {}
  disable_malicious_user_detection = {}
  disable_client_side_defense      = {}
  disable_threat_mesh              = {}
  no_challenge                     = {}
  system_default_timeouts          = {}
  user_id_client_ip                = {}
  default_sensitive_data_policy    = {}
  l7_ddos_action_default           = {}
  origin_pool {
    origin_request_timeout = "60s"
    origin_servers {
      port = 443
      public_name {
        dns_name = var.origin_hostname
      }
    }
    use_tls {
      sni = var.origin_hostname
      tls_config {
        default_security = {}
      }
      use_mtls {
        tls_certificates {
          blindfold = { id = "server", certificate_file = var.certificate_file, private_key_file = var.private_key_file }
        }
      }
      use_server_verification {
        trusted_ca_url = "string:///${filebase64(var.origin_ca_file)}"
      }
    }
  }
  http {
    port = 80
  }
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
variable "origin_hostname" {
  type        = string
  description = "Existing reachable origin hostname; certificate must allow clientAuth for mTLS."
}
variable "origin_ca_file" {
  type        = string
  description = "Public PEM trust anchor for the origin server. Verification remains enabled."
}
terraform {
  required_providers {
    xcsh = {
      source = "f5-sales-demo/xcsh"
    }
  }
}

# XCSH_API_URL and XCSH_API_TOKEN configure the provider, without a CLI.
provider "xcsh" {}
```

</div>

## Configure

1. Supply the prerequisite fields in Customize examples. Download the files and review the saved plan.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CERT_FILE XCSH_DOMAINNAME XCSH_KEY_FILE XCSH_LB_NAME XCSH_NAMESPACE XCSH_ORIGIN_CA_FILE XCSH_ORIGIN_HOSTNAME XCSH_WORKDIR">

```bash
umask 077
configuration="$XCSH_WORKDIR/cdn-origin-mtls"
mkdir -p "$configuration"
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_LB_NAME"
export TF_VAR_domain="$XCSH_DOMAINNAME"
export TF_VAR_certificate_file="$XCSH_CERT_FILE"
export TF_VAR_private_key_file="$XCSH_KEY_FILE"
export TF_VAR_origin_hostname="$XCSH_ORIGIN_HOSTNAME"
export TF_VAR_origin_ca_file="$XCSH_ORIGIN_CA_FILE"
for file in main.tf variables.tf versions.tf; do
  curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/cdn-origin-mtls/$file" --output "$configuration/$file"
done
terraform -chdir="$configuration" init -upgrade
terraform -chdir="$configuration" validate
terraform -chdir="$configuration" plan -out=create.plan
terraform -chdir="$configuration" show create.plan
shasum -a 256 "$configuration/create.plan"
```

</div>

2. Confirm the resource names, references, and ownership in the plan. Apply that reviewed plan.

<div data-xcsh-context="shell" data-xcsh-fields="">

```bash
terraform -chdir="$configuration" apply create.plan
```

</div>

Expect the configured resource to be created with encrypted key material. A failed or uncertain apply requires named readback before recovery; create a fresh plan after reconciling state.

## Verify

Read the complete API configuration privately and check the new process's Terraform plan.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL XCSH_NAMESPACE">

```bash
curl --silent --show-error --fail --header "Authorization: APIToken $XCSH_API_TOKEN" \
  "$XCSH_API_URL/api/config/namespaces/$XCSH_NAMESPACE/cdn_loadbalancers/$TF_VAR_name?response_format=2" \
  --output "$configuration/example-readback.json"
terraform -chdir="$configuration" plan -detailed-exitcode
```

</div>

Expect HTTP `200`, the selected names and references, the encoded public chain, and `private_key.blindfold_secret_info.location` at every certificate node. No `blindfold` input or clear private key belongs in the API object. Expect exit `0` and **No changes**; exit `2` means changes and exit `1` means failure.

Configuration readback does not prove served TLS. Send a request through the configured consumer to the origin. Require trusted server TLS and an origin result confirming the configured client identity; a successful handshake from your laptop does not prove consumer mTLS.

After attaching this configuration to an HTTPS consumer whose certificate chains to your client trust store, request it without supplying your mTLS key from the client. Expect the application's response and separately confirm the origin observed the configured client identity.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_DOMAINNAME">

```bash
curl --silent --show-error --fail "https://$XCSH_DOMAINNAME/get" --output "$configuration/consumer-response" --write-out '%{http_code}\n'
```

</div>

## Maintain

Use [input and lifecycle guidance](../../input-lifecycle/) for renewal, stable IDs, import, and recovery. Change both private files together, preserve the logical ID and referenced algorithm, review a fresh plan, apply, and repeat configuration and traffic verification.

## Remove

Review and hash a destroy plan for this state. Remove dependent consumers first; the existing namespace is a data source.

<div data-xcsh-context="shell" data-xcsh-fields="">

```bash
terraform -chdir="$configuration" plan -destroy -out=remove.plan
terraform -chdir="$configuration" show remove.plan
shasum -a 256 "$configuration/remove.plan"
terraform -chdir="$configuration" apply remove.plan
terraform -chdir="$configuration" state list
```

</div>

Expect only this state's resources to be removed and an empty resource list. Confirm typed API absence; authentication and transport failures do not establish absence.
