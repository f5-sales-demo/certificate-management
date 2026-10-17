---
title: Inputs and lifecycle
description: Protected certificate inputs, write-only versioning, stable IDs, rotation, drift, and import.
sidebar:
  order: 2
---

Native Blindfold preparation validates the matching key and leaf-first certificate chain, normalizes material, and encrypts the private key. Use the [file-input walkthrough](../) for the main deployment. Keep every private input outside Git with directory mode `0700` and file mode `0600`.

## Input choices

The bundle input field `XCSH_P12_FILE` also configures provider authentication. The input commands remove it from the Terraform process environment after copying the bundle path or contents to a dedicated input variable, so API token authentication stays independent.

Use file inputs for unprotected PEM in the [certificate workflow](../). The alternatives below prepare the same public configuration shown there. `sensitive` hides display; only ephemeral write-only variables prevent private inputs from entering plans and state. Never put keys or bundles in ordinary variables.

### Protected PEM

Use a separate directory and state, an existing namespace, and an exclusively owned certificate name. This complete HCL owns only the named certificate. Attach it to a separately owned HTTPS consumer for served verification.

<div data-xcsh-context="hcl" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL XCSH_TLS_INPUT_PASSWORD">

```hcl
resource "xcsh_certificate" "server" {
  name        = var.name
  namespace   = data.xcsh_namespace.existing.name
  description = var.description
  labels      = { certificate-example = "terraform" }
  blindfold   = { certificate_file = var.certificate_file, private_key_file = var.private_key_file, passphrase_env = "XCSH_TLS_INPUT_PASSWORD" }
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

Supply the selected input and review the saved plan.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CERT_FILE XCSH_LB_NAME XCSH_NAMESPACE XCSH_P12_FILE XCSH_PROTECTED_KEY_FILE XCSH_TLS_INPUT_PASSWORD XCSH_WORKDIR">

```bash
umask 077
configuration="$XCSH_WORKDIR/input-protected-pem"
mkdir -p "$configuration"
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_LB_NAME"
if [ -z "${XCSH_TLS_INPUT_PASSWORD:-}" ]; then
  printf "Input passphrase: "
  IFS= read -r -s XCSH_TLS_INPUT_PASSWORD
  printf "\n"
fi
export XCSH_TLS_INPUT_PASSWORD
export TF_VAR_certificate_file="$XCSH_CERT_FILE"
export TF_VAR_private_key_file="$XCSH_PROTECTED_KEY_FILE"
for file in main.tf variables.tf versions.tf; do
  curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/input-variants/protected-pem/$file" --output "$configuration/$file"
done
env -u XCSH_P12_FILE terraform -chdir="$configuration" init -upgrade
env -u XCSH_P12_FILE terraform -chdir="$configuration" validate
env -u XCSH_P12_FILE terraform -chdir="$configuration" plan -out=input.plan
env -u XCSH_P12_FILE terraform -chdir="$configuration" show input.plan
shasum -a 256 "$configuration/input.plan"
```

</div>

Apply the reviewed plan and verify encrypted readback.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL XCSH_NAMESPACE XCSH_P12_FILE XCSH_TLS_INPUT_PASSWORD">

```bash
env -u XCSH_P12_FILE terraform -chdir="$configuration" apply input.plan
env -u XCSH_P12_FILE terraform -chdir="$configuration" plan -detailed-exitcode
curl --silent --show-error --fail --header "Authorization: APIToken $XCSH_API_TOKEN" \
  "$XCSH_API_URL/api/config/namespaces/$XCSH_NAMESPACE/certificates/$TF_VAR_name?response_format=2" \
  --output "$configuration/readback.json"
unset XCSH_TLS_INPUT_PASSWORD TF_VAR_private_key TF_VAR_pkcs12_base64 TF_VAR_passphrase
```

</div>

Expect HTTP `200`, an encoded public chain, and an encrypted private-key location. Expect **No changes** and exit `0` in a new process. This result does not prove served TLS. Write-only inputs require the same ephemeral values at saved-plan apply and a new material version when inputs change. Keep secrets exported until verification finishes, then unset them.

### PKCS#12

Use a separate directory and state, an existing namespace, and an exclusively owned certificate name. This complete HCL owns only the named certificate. Attach it to a separately owned HTTPS consumer for served verification.

<div data-xcsh-context="hcl" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL XCSH_TLS_INPUT_PASSWORD">

```hcl
resource "xcsh_certificate" "server" {
  name        = var.name
  namespace   = data.xcsh_namespace.existing.name
  description = var.description
  labels      = { certificate-example = "terraform" }
  blindfold   = { pkcs12_file = var.pkcs12_file, passphrase_env = "XCSH_TLS_INPUT_PASSWORD" }
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

variable "description" {
  type        = string
  description = "Operator-editable resource description."
  default     = "Native Terraform Blindfold certificate example"
}

data "xcsh_namespace" "existing" {
  name = var.namespace
}
variable "pkcs12_file" {
  type = string
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

Supply the selected input and review the saved plan.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_LB_NAME XCSH_NAMESPACE XCSH_P12_FILE XCSH_TLS_INPUT_PASSWORD XCSH_WORKDIR">

```bash
umask 077
configuration="$XCSH_WORKDIR/input-pkcs12"
mkdir -p "$configuration"
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_LB_NAME"
if [ -z "${XCSH_TLS_INPUT_PASSWORD:-}" ]; then
  printf "Input passphrase: "
  IFS= read -r -s XCSH_TLS_INPUT_PASSWORD
  printf "\n"
fi
export XCSH_TLS_INPUT_PASSWORD
export TF_VAR_pkcs12_file="$XCSH_P12_FILE"
for file in main.tf variables.tf versions.tf; do
  curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/input-variants/pkcs12/$file" --output "$configuration/$file"
done
env -u XCSH_P12_FILE terraform -chdir="$configuration" init -upgrade
env -u XCSH_P12_FILE terraform -chdir="$configuration" validate
env -u XCSH_P12_FILE terraform -chdir="$configuration" plan -out=input.plan
env -u XCSH_P12_FILE terraform -chdir="$configuration" show input.plan
shasum -a 256 "$configuration/input.plan"
```

</div>

Apply the reviewed plan and verify encrypted readback.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL XCSH_NAMESPACE XCSH_P12_FILE XCSH_TLS_INPUT_PASSWORD">

```bash
env -u XCSH_P12_FILE terraform -chdir="$configuration" apply input.plan
env -u XCSH_P12_FILE terraform -chdir="$configuration" plan -detailed-exitcode
curl --silent --show-error --fail --header "Authorization: APIToken $XCSH_API_TOKEN" \
  "$XCSH_API_URL/api/config/namespaces/$XCSH_NAMESPACE/certificates/$TF_VAR_name?response_format=2" \
  --output "$configuration/readback.json"
unset XCSH_TLS_INPUT_PASSWORD TF_VAR_private_key TF_VAR_pkcs12_base64 TF_VAR_passphrase
```

</div>

Expect HTTP `200`, an encoded public chain, and an encrypted private-key location. Expect **No changes** and exit `0` in a new process. This result does not prove served TLS. Write-only inputs require the same ephemeral values at saved-plan apply and a new material version when inputs change. Keep secrets exported until verification finishes, then unset them.

### Write-only PEM

Use a separate directory and state, an existing namespace, and an exclusively owned certificate name. This complete HCL owns only the named certificate. Attach it to a separately owned HTTPS consumer for served verification.

<div data-xcsh-context="hcl" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL">

```hcl
resource "xcsh_certificate" "server" {
  name        = var.name
  namespace   = data.xcsh_namespace.existing.name
  description = var.description
  labels      = { certificate-example = "terraform" }
  blindfold   = { certificate_file = var.certificate_file, private_key_wo = var.private_key, material_version = "1" }
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

variable "description" {
  type        = string
  description = "Operator-editable resource description."
  default     = "Native Terraform Blindfold certificate example"
}

data "xcsh_namespace" "existing" {
  name = var.namespace
}
variable "private_key" {
  type      = string
  sensitive = true
  ephemeral = true
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

Supply the selected input and review the saved plan.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CERT_FILE XCSH_KEY_FILE XCSH_LB_NAME XCSH_MATERIAL_VERSION XCSH_NAMESPACE XCSH_P12_FILE XCSH_WORKDIR">

```bash
umask 077
configuration="$XCSH_WORKDIR/input-write-only-pem"
mkdir -p "$configuration"
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_LB_NAME"
export TF_VAR_certificate_file="$XCSH_CERT_FILE"
TF_VAR_private_key="$(cat "$XCSH_KEY_FILE")"
export TF_VAR_private_key
export XCSH_MATERIAL_VERSION
for file in main.tf variables.tf versions.tf; do
  curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/input-variants/write-only-pem/$file" --output "$configuration/$file"
done
python3 -c 'import json,os,re,sys; from pathlib import Path; p=Path(sys.argv[1]); p.write_text(re.sub(r"material_version\s*=\s*"+re.escape(json.dumps("1")), lambda _: "material_version = "+json.dumps(os.environ["XCSH_MATERIAL_VERSION"]), p.read_text()))' "$configuration/main.tf"
env -u XCSH_P12_FILE terraform -chdir="$configuration" init -upgrade
env -u XCSH_P12_FILE terraform -chdir="$configuration" validate
env -u XCSH_P12_FILE terraform -chdir="$configuration" plan -out=input.plan
env -u XCSH_P12_FILE terraform -chdir="$configuration" show input.plan
shasum -a 256 "$configuration/input.plan"
```

</div>

Apply the reviewed plan and verify encrypted readback.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL XCSH_NAMESPACE XCSH_P12_FILE XCSH_TLS_INPUT_PASSWORD">

```bash
env -u XCSH_P12_FILE terraform -chdir="$configuration" apply input.plan
env -u XCSH_P12_FILE terraform -chdir="$configuration" plan -detailed-exitcode
curl --silent --show-error --fail --header "Authorization: APIToken $XCSH_API_TOKEN" \
  "$XCSH_API_URL/api/config/namespaces/$XCSH_NAMESPACE/certificates/$TF_VAR_name?response_format=2" \
  --output "$configuration/readback.json"
unset XCSH_TLS_INPUT_PASSWORD TF_VAR_private_key TF_VAR_pkcs12_base64 TF_VAR_passphrase
```

</div>

Expect HTTP `200`, an encoded public chain, and an encrypted private-key location. Expect **No changes** and exit `0` in a new process. This result does not prove served TLS. Write-only inputs require the same ephemeral values at saved-plan apply and a new material version when inputs change. Keep secrets exported until verification finishes, then unset them.

### Write-only PKCS#12

Use a separate directory and state, an existing namespace, and an exclusively owned certificate name. This complete HCL owns only the named certificate. Attach it to a separately owned HTTPS consumer for served verification.

<div data-xcsh-context="hcl" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL">

```hcl
resource "xcsh_certificate" "server" {
  name        = var.name
  namespace   = data.xcsh_namespace.existing.name
  description = var.description
  labels      = { certificate-example = "terraform" }
  blindfold   = { pkcs12_wo = var.pkcs12_base64, passphrase_wo = var.passphrase, material_version = "1" }
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

variable "description" {
  type        = string
  description = "Operator-editable resource description."
  default     = "Native Terraform Blindfold certificate example"
}

data "xcsh_namespace" "existing" {
  name = var.namespace
}
variable "pkcs12_base64" {
  type      = string
  sensitive = true
  ephemeral = true
}
variable "passphrase" {
  type      = string
  sensitive = true
  ephemeral = true
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

Supply the selected input and review the saved plan.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_LB_NAME XCSH_MATERIAL_VERSION XCSH_NAMESPACE XCSH_P12_FILE XCSH_TLS_INPUT_PASSWORD XCSH_WORKDIR">

```bash
umask 077
configuration="$XCSH_WORKDIR/input-write-only-pkcs12"
mkdir -p "$configuration"
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_LB_NAME"
if [ -z "${XCSH_TLS_INPUT_PASSWORD:-}" ]; then
  printf "Input passphrase: "
  IFS= read -r -s XCSH_TLS_INPUT_PASSWORD
  printf "\n"
fi
export XCSH_TLS_INPUT_PASSWORD
TF_VAR_pkcs12_base64="$(openssl base64 -A -in "$XCSH_P12_FILE")"
export TF_VAR_pkcs12_base64
export TF_VAR_passphrase="$XCSH_TLS_INPUT_PASSWORD"
export XCSH_MATERIAL_VERSION
for file in main.tf variables.tf versions.tf; do
  curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/input-variants/write-only-pkcs12/$file" --output "$configuration/$file"
done
python3 -c 'import json,os,re,sys; from pathlib import Path; p=Path(sys.argv[1]); p.write_text(re.sub(r"material_version\s*=\s*"+re.escape(json.dumps("1")), lambda _: "material_version = "+json.dumps(os.environ["XCSH_MATERIAL_VERSION"]), p.read_text()))' "$configuration/main.tf"
env -u XCSH_P12_FILE terraform -chdir="$configuration" init -upgrade
env -u XCSH_P12_FILE terraform -chdir="$configuration" validate
env -u XCSH_P12_FILE terraform -chdir="$configuration" plan -out=input.plan
env -u XCSH_P12_FILE terraform -chdir="$configuration" show input.plan
shasum -a 256 "$configuration/input.plan"
```

</div>

Apply the reviewed plan and verify encrypted readback.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL XCSH_NAMESPACE XCSH_P12_FILE XCSH_TLS_INPUT_PASSWORD">

```bash
env -u XCSH_P12_FILE terraform -chdir="$configuration" apply input.plan
env -u XCSH_P12_FILE terraform -chdir="$configuration" plan -detailed-exitcode
curl --silent --show-error --fail --header "Authorization: APIToken $XCSH_API_TOKEN" \
  "$XCSH_API_URL/api/config/namespaces/$XCSH_NAMESPACE/certificates/$TF_VAR_name?response_format=2" \
  --output "$configuration/readback.json"
unset XCSH_TLS_INPUT_PASSWORD TF_VAR_private_key TF_VAR_pkcs12_base64 TF_VAR_passphrase
```

</div>

Expect HTTP `200`, an encoded public chain, and an encrypted private-key location. Expect **No changes** and exit `0` in a new process. This result does not prove served TLS. Write-only inputs require the same ephemeral values at saved-plan apply and a new material version when inputs change. Keep secrets exported until verification finishes, then unset them.

## Stable inline identities

Every inline certificate needs a unique `blindfold.id` in its certificate list. [Inline server
HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/inline-server-tls) accepts an ordered list of stable IDs and file
paths. Keep an ID attached to the same logical certificate when inserting, reordering, or removing other entries. The provider preserves unchanged
encrypted output and maps provenance by ID, rather than by list position. The tenant API rejected two RSA entries in the same server list with HTTP 400.
A mixed list with one RSA and one EC entry supports insertion, reordering, and removal. Respect the consumer’s algorithm/list constraints. Duplicate or missing
IDs are invalid. Give a replacement logical certificate
a new ID if its role changes.

Use `<XCSH_CERT_ID>` for the logical identity in a local inline fragment; the published example's structural resource labels remain fixed:

<div data-xcsh-context="hcl" data-xcsh-fields="XCSH_CERT_ID XCSH_CERT_FILE XCSH_KEY_FILE">

```hcl
blindfold = {
  id               = "<XCSH_CERT_ID>"
  certificate_file = "<XCSH_CERT_FILE>"
  private_key_file = "<XCSH_KEY_FILE>"
}
```

</div>

## Policy and context rotation

The default policy is `shared/ves-io-allow-volterra`. Set `blindfold.policy` only when choosing an authorized policy. The provider compares normalized public material, the encryption context, and retained encrypted output. Equivalent PEM formatting or relocated files reuse ciphertext; metadata edits do not re-encrypt the key.

Changing the selected policy, its canonical document, or the tenant public key changes the context digest and requires fresh encryption once, followed
by an empty plan. Selected-policy and in-place policy-document rotation have live evidence. Isolated live tenant public encryption-key rotation
remains unqualified. Do not claim it from a policy test.

## Saved plans

File paths appear in plans, while file contents are read by the provider. Keep the pair available and unchanged between plan and apply. If either file
changes, abandon the old plan and create a fresh plan for both inputs. A saved plan does not make externally mutable files immutable. Write-only
values require a changed `material_version` and renewed ephemeral input at apply.

Protect saved plans, state, backups, logs, and API readbacks as private artifacts. Review full replace-form API reads with `response_format=2` privately: the private key must use `blindfold_secret_info.location`, with matching `f5-sales-demo.com/blindfold` provenance. A ciphertext value alone does not prove serving or idempotence.

## Drift and import

Run a normal refreshed plan after remote metadata, encrypted location, or provenance changes. Retained private source files allow reconciliation; investigate unexpected changes before applying. Do not delete provenance manually to force an update.

Import a resource only into its exclusive owner state using the provider’s `namespace/name` identifier. Import retrieves public configuration and
encrypted material; it cannot recover the private key or passphrase. Restore the original private files or provide new authorized material before
native preparation can renew the certificate. Never adopt an xcsh-owned resource into the Terraform owner state.

## RSA and EC cutovers

Renew a referenced certificate with the same key algorithm. For a Rivest–Shamir–Adleman (RSA) to elliptic-curve (EC) change, prepare a separate named
certificate, update consumer references in a reviewed apply, qualify trust/hostname/fingerprint and traffic, then retire the old name. XC can reject
algorithm changes on an existing referenced certificate. Inline lists may hold both algorithms with distinct stable IDs; qualify negotiation and
serving for each intended client before retiring an entry.

## Interception signing CA

Transport Layer Security (TLS) interception signs new leaf certificates. Generate a separate signing certificate authority (CA) and distribute only its public trust certificate to authorized clients. A `CA:false` server certificate cannot act as this CA.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_INTERCEPTION_CA_FILE XCSH_INTERCEPTION_KEY_FILE">

```bash
umask 077
mkdir -p "$(dirname "$XCSH_INTERCEPTION_CA_FILE")" "$(dirname "$XCSH_INTERCEPTION_KEY_FILE")"
openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 3650 \
  -subj '/CN=Example interception CA' \
  -addext 'basicConstraints=critical,CA:true,pathlen:0' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign' \
  -keyout "$XCSH_INTERCEPTION_KEY_FILE" \
  -out "$XCSH_INTERCEPTION_CA_FILE"
```

</div>

Map the signing CA files in a separate state for interception:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_INTERCEPTION_CA_FILE XCSH_INTERCEPTION_KEY_FILE">

```bash
export TF_VAR_certificate_file="$XCSH_INTERCEPTION_CA_FILE"
export TF_VAR_private_key_file="$XCSH_INTERCEPTION_KEY_FILE"
```

</div>

Supply these CA files to the [proxy interception
example](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/proxy-intercept). It is not advertised by default. Serving
interception requires a forward-proxy route and client trust prerequisites; the matrix’s configuration lifecycle result does not claim intercepted
traffic acceptance.
