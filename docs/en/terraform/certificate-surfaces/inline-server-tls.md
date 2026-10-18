---
title: Inline server TLS
description: Inline server TLS configuration and certificate lifecycle checks.
sidebar:
  order: 6
---

## Prerequisites

Install the latest Terraform and provider releases. Set the [provider environment](../../prerequisites/) and keep private inputs and state outside Git. Copy this configuration into its own directory and state; never reuse another owner's name.

Supply a tenant-owned hostname with an existing DNS route. Keep each logical certificate's stable ID attached to its material.

## Configuration

The JSON below shows the complete public configuration resulting from native encryption, with encoded public chains and encrypted-key placeholders. API defaults and provider provenance may add fields. Never apply encoded-material placeholders. HCL includes the complete canonical root; download its files separately.

[Download JSON](../../../../assets/configurations/inline-server-tls.json).

Download HCL files: [main.tf](../../../../_data/terraform/inline-server-tls/main.tf) · [variables.tf](../../../../_data/terraform/inline-server-tls/variables.tf) · [versions.tf](../../../../_data/terraform/inline-server-tls/versions.tf).

### Public JSON

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
      "disable_waf": {},
      "no_service_policies": {},
      "disable_api_definition": {},
      "disable_api_discovery": {},
      "disable_bot_defense": {},
      "disable_rate_limit": {},
      "disable_ip_reputation": {},
      "disable_malicious_user_detection": {},
      "domains": ["<XCSH_DOMAINNAME>"],
      "advertise_on_public_default_vip": {},
      "https": {
        "port": 443,
        "tls_parameters": {
          "no_mtls": {},
          "tls_config": {
            "default_security": {}
          },
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
  }
]
```

</div>

### Complete HCL

<div data-xcsh-context="hcl" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL">

```hcl
resource "xcsh_http_loadbalancer" "example" {
  name                             = var.name
  namespace                        = data.xcsh_namespace.existing.name
  description                      = var.description
  labels                           = { certificate-example = "terraform" }
  disable_waf                      = {}
  no_service_policies              = {}
  disable_api_definition           = {}
  disable_api_discovery            = {}
  disable_bot_defense              = {}
  disable_rate_limit               = {}
  disable_ip_reputation            = {}
  disable_malicious_user_detection = {}
  domains                          = [var.domain]
  advertise_on_public_default_vip  = {}
  https {
    port = 443
    tls_parameters {
      no_mtls = {}
      tls_config {
        default_security = {}
      }
      dynamic "tls_certificates" {
        for_each = var.certificates
        content {
          blindfold = {
            id               = tls_certificates.value.id
            certificate_file = tls_certificates.value.certificate_file
            private_key_file = tls_certificates.value.private_key_file
          }
        }
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
```

</div>

## Configure

Supply the prerequisite fields in Customize examples. Download the files and review the saved plan.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CERT_FILE XCSH_CERT_ID XCSH_DOMAINNAME XCSH_KEY_FILE XCSH_LB_NAME XCSH_NAMESPACE XCSH_WORKDIR">

```bash
umask 077
configuration="$XCSH_WORKDIR/inline-server-tls"
mkdir -p "$configuration"
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_LB_NAME"
export TF_VAR_domain="$XCSH_DOMAINNAME"
TF_VAR_certificates="$(python3 -c 'import json,os; print(json.dumps([{"id":os.environ["XCSH_CERT_ID"],"certificate_file":os.environ["XCSH_CERT_FILE"],"private_key_file":os.environ["XCSH_KEY_FILE"]}]))')"
export TF_VAR_certificates
for file in main.tf variables.tf versions.tf; do
  curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/inline-server-tls/$file" --output "$configuration/$file"
done
terraform -chdir="$configuration" init -upgrade
terraform -chdir="$configuration" validate
terraform -chdir="$configuration" plan -out=create.plan
terraform -chdir="$configuration" show create.plan
shasum -a 256 "$configuration/create.plan"
```

</div>

Confirm the resource names, references, and ownership in the plan. Apply that reviewed plan.

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
  "$XCSH_API_URL/api/config/namespaces/$XCSH_NAMESPACE/http_loadbalancers/$TF_VAR_name?response_format=2" \
  --output "$configuration/example-readback.json"
terraform -chdir="$configuration" plan -detailed-exitcode
```

</div>

Expect HTTP `200`, the selected names and references, the encoded public chain, and `private_key.blindfold_secret_info.location` at every certificate node. No `blindfold` input or clear private key belongs in the API object. Expect exit `0` and **No changes**; exit `2` means changes and exit `1` means failure.

Configuration readback does not prove served TLS. Run the [hostname, trust, fingerprint, and response checks](../../verify/). Expect the identifying JSON response.

Run these checks only after attaching an advertised HTTPS consumer on port 443 with this certificate. Expect trusted hostname verification, identical fingerprints, and the application's expected status and response. A different protocol or port requires the corresponding consumer check.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CERT_FILE XCSH_DOMAINNAME">

```bash
openssl s_client -connect "$XCSH_DOMAINNAME:443" -servername "$XCSH_DOMAINNAME" -verify_hostname "$XCSH_DOMAINNAME" -verify_return_error -CAfile "$XCSH_CERT_FILE" -showcerts < /dev/null > "$configuration/served-handshake.pem"
openssl x509 -in "$XCSH_CERT_FILE" -noout -sha256 -fingerprint > "$configuration/expected-fingerprint"
openssl x509 -in "$configuration/served-handshake.pem" -noout -sha256 -fingerprint > "$configuration/served-fingerprint"
cmp "$configuration/expected-fingerprint" "$configuration/served-fingerprint"
curl --silent --show-error --fail --cacert "$XCSH_CERT_FILE" "https://$XCSH_DOMAINNAME/get" --output "$configuration/consumer-response" --write-out '%{http_code}\n'
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
