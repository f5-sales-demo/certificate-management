---
title: TLS interception
sidebar:
  order: 8
---

## Prerequisites

Install the latest Terraform and provider releases. Set the [provider environment](../../#prerequisites) and keep private inputs and state outside Git. Copy this configuration into its own directory and state; never reuse another owner's name.

Supply a signing CA and matching key, a forward-proxy route, and client trust. Use the interception CA fields rather than a server leaf. Configuration verification does not qualify intercepted traffic.

## Configuration

The JSON below shows the complete public configuration resulting from native encryption, with encoded public chains and encrypted-key placeholders. API defaults and provider provenance may add fields. Never apply encoded-material placeholders. HCL includes the complete canonical root; download its files separately.

[Download JSON](../../../../assets/configurations/proxy-intercept.json).

<div data-xcsh-context="json" data-xcsh-fields="XCSH_LB_NAME XCSH_NAMESPACE">

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
      "do_not_advertise": {},
      "site_local_network": {},
      "no_forward_proxy_policy": {},
      "http_proxy": {
        "enable_http": {}
      },
      "tls_intercept": {
        "enable_for_all_domains": {},
        "volterra_trusted_ca": {},
        "custom_certificate": {
          "certificate_url": "string:///<BASE64_PUBLIC_CHAIN>",
          "private_key": {
            "blindfold_secret_info": {
              "location": "string:///<ENCRYPTED_KEY>"
            }
          }
        }
      }
    }
  }
]
```

</div>

<div data-xcsh-context="hcl" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL">

```hcl
resource "xcsh_proxy" "example" {
  name                    = var.name
  namespace               = data.xcsh_namespace.existing.name
  description             = var.description
  labels                  = { certificate-example = "terraform" }
  do_not_advertise        = {}
  site_local_network      = {}
  no_forward_proxy_policy = {}
  http_proxy {
    enable_http {

    }
  }
  tls_intercept {
    enable_for_all_domains = {}
    volterra_trusted_ca    = {}
    custom_certificate {
      blindfold = { id = "signing-ca", certificate_file = var.certificate_file, private_key_file = var.private_key_file }
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

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_INTERCEPTION_CA_FILE XCSH_INTERCEPTION_KEY_FILE XCSH_LB_NAME XCSH_NAMESPACE XCSH_WORKDIR">

```bash
umask 077
configuration="$XCSH_WORKDIR/proxy-intercept"
mkdir -p "$configuration"
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_LB_NAME"
export TF_VAR_certificate_file="$XCSH_INTERCEPTION_CA_FILE"
export TF_VAR_private_key_file="$XCSH_INTERCEPTION_KEY_FILE"
for file in main.tf variables.tf versions.tf; do
  curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/proxy-intercept/$file" --output "$configuration/$file"
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
  "$XCSH_API_URL/api/config/namespaces/$XCSH_NAMESPACE/proxys/$TF_VAR_name?response_format=2" \
  --output "$configuration/example-readback.json"
terraform -chdir="$configuration" plan -detailed-exitcode
```

</div>

Expect HTTP `200`, the selected names and references, the encoded public chain, and `private_key.blindfold_secret_info.location` at every certificate node. No `blindfold` input or clear private key belongs in the API object. Expect exit `0` and **No changes**; exit `2` means changes and exit `1` means failure.

Configuration readback does not prove served TLS. Use the advertised forward proxy from an authorized client trusting the signing CA. Verify the target hostname and the substituted leaf issuer, then verify the expected application response. This path has no served-traffic qualification receipt.

After configuring an authorized proxy route, inspect its substituted leaf and application response. Require the target hostname and your signing CA's issuer.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_INTERCEPTION_CA_FILE XCSH_ORIGIN_HOSTNAME">

```bash
read -r -p "Advertised proxy host:port: " proxy_address
openssl s_client -proxy "$proxy_address" -connect "$XCSH_ORIGIN_HOSTNAME:443" -servername "$XCSH_ORIGIN_HOSTNAME" -verify_hostname "$XCSH_ORIGIN_HOSTNAME" -verify_return_error -CAfile "$XCSH_INTERCEPTION_CA_FILE" -showcerts < /dev/null > "$configuration/intercepted-handshake.pem"
openssl x509 -in "$configuration/intercepted-handshake.pem" -noout -subject -issuer
curl --silent --show-error --fail --proxy "http://$proxy_address" --cacert "$XCSH_INTERCEPTION_CA_FILE" "https://$XCSH_ORIGIN_HOSTNAME/" --output "$configuration/intercepted-response"
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
