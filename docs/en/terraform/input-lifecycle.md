---
title: Inputs and lifecycle
description: Protected certificate inputs, write-only versioning, stable IDs, rotation, drift, and import.
sidebar:
  order: 2
---

Native Blindfold preparation validates the matching key and leaf-first certificate chain, normalizes material, and encrypts the private key. Use the [file-input walkthrough](../) for the main deployment. Keep every private input outside Git with directory mode `0700` and file mode `0600`.

## Input choices

| Input | Configuration | Handling |
| --- | --- | --- |
| Unprotected PEM | `certificate_file` plus `private_key_file` | Provider reads files directly; only paths and public/encrypted results enter state. |
| Protected PEM | File inputs plus `passphrase_env` | Value names an environment variable containing the passphrase; its value is not stored. |
| PKCS #12 (P12) | `pkcs12_file` plus `passphrase_env` if protected | Provider decodes the bundle natively; do not configure separate PEM inputs. |
| Write-only PEM key | `certificate_pem` plus `private_key_wo` and `material_version` | Terraform 1.11+ ephemeral sensitive variable; secret is null in plan/state. |
| Write-only P12 | `pkcs12_wo`, optional `passphrase_wo`, and `material_version` | Supply the bundle as base64 through ephemeral sensitive variables. |

`certificate_pem` is public material. Never put a plaintext key or bundle into ordinary variables, `file()` attributes, outputs, or legacy `clear_secret_info`. `sensitive = true` hides a value from display but does not prevent storage.

Enter a protected-file passphrase without echo, export it only for the session, and set `blindfold.passphrase_env = "XCSH_TLS_INPUT_PASSWORD"`. Unset it after Terraform exits. Avoid command-line passphrase arguments.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_TLS_INPUT_PASSWORD">

```bash
if [ -z "${XCSH_TLS_INPUT_PASSWORD:-}" ]; then
  read -r -s -p 'Input passphrase: ' XCSH_TLS_INPUT_PASSWORD
  printf '\n'
fi
export XCSH_TLS_INPUT_PASSWORD
```

</div>

These schema-checked fragments illustrate write-only input wiring; they are not complete deployment configurations:

For a protected PEM input, map its path to the existing variable and add `passphrase_env = "XCSH_TLS_INPUT_PASSWORD"` to that resource's `blindfold` object. Keep the passphrase in the environment until both planning and applying finish, then unset it. The variable name is fixed; the passphrase value never enters HCL.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CERT_FILE XCSH_PROTECTED_KEY_FILE">

```bash
export TF_VAR_certificate_file="$XCSH_CERT_FILE"
export TF_VAR_private_key_file="$XCSH_PROTECTED_KEY_FILE"
```

</div>

For a P12 variant in a separate private configuration, declare a string variable `pkcs12_file` and replace the PEM selectors with this object:

<div data-xcsh-context="hcl" data-xcsh-fields="">

```hcl
blindfold = {
  pkcs12_file    = var.pkcs12_file
  passphrase_env = "XCSH_TLS_INPUT_PASSWORD"
}
```

</div>

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_P12_FILE">

```bash
export TF_VAR_pkcs12_file="$XCSH_P12_FILE"
```

</div>

<div data-xcsh-context="hcl" data-xcsh-fields="">

```hcl
variable "private_key" {
  type      = string
  sensitive = true
  ephemeral = true
}
variable "material_version" {
  type = string
}
# Inside xcsh_certificate, or an inline certificate with a stable id:
# blindfold = {
#   certificate_pem = file(var.certificate_file)
#   private_key_wo  = var.private_key
#   material_version = var.material_version
# }
```

</div>

Map the write-only version to its native variable. To supply a write-only PEM key, read its file into the declared ephemeral sensitive variable in the shell; never save it in a variable file:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_MATERIAL_VERSION XCSH_KEY_FILE">

```bash
export TF_VAR_material_version="$XCSH_MATERIAL_VERSION"
TF_VAR_private_key="$(cat "$XCSH_KEY_FILE")"
export TF_VAR_private_key
```

</div>

For P12, use `pkcs12_wo = var.pkcs12_base64` and `passphrase_wo = var.passphrase` with both variables declared `sensitive` and `ephemeral`. Remove
other key/certificate input selectors. Increase `material_version` whenever a write-only input changes; Terraform cannot derive a change from a value
it deliberately does not persist. Reusing a version is a declaration that the material is unchanged. Supply ephemeral values again when applying a
saved plan.

## Stable inline identities

Every inline certificate needs a unique `blindfold.id` in its certificate list. [Inline server
HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/inline-server-tls) accepts an ordered list of stable IDs and file
paths. Keep an ID attached to the same logical certificate when inserting, reordering, or removing other entries. The provider preserves unchanged
encrypted output and maps provenance by ID, rather than by list position. The demo API rejected two RSA entries in the same server list with HTTP 400.
The qualified insertion/reorder/removal test uses one RSA and one EC entry. Respect the consumer’s algorithm/list constraints. Duplicate or missing
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
native preparation can renew the certificate. Never adopt an xcsh-owned resource into the Terraform showcase state.

## RSA and EC cutovers

Renew a referenced certificate with the same key algorithm. For a Rivest–Shamir–Adleman (RSA) to elliptic-curve (EC) change, prepare a separate named
certificate, update consumer references in a reviewed apply, qualify trust/hostname/fingerprint and traffic, then retire the old name. XC can reject
algorithm changes on an existing referenced certificate. Inline lists may hold both algorithms with distinct stable IDs; qualify negotiation and
serving for each intended client before retiring an entry.

## Interception signing CA

Transport Layer Security (TLS) interception signs new leaf certificates. Generate a separate signing certificate authority (CA) and distribute only its public trust certificate to authorized clients. The showcase’s `CA:false` server certificate cannot act as this CA.

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
