---
title: Terraform — Configure
description: Configure for the Terraform certificate workflow.
sidebar:
  label: Configure
  order: 3
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../configuration/
  label: Configuration
next:
  link: ../verify/
  label: Verify
---

## Configure steps

## Prepare local inputs

Select an existing leaf-first Privacy Enhanced Mail (PEM) chain and matching key, or create self-signed material outside Git. The following recipe creates
a Rivest–Shamir–Adleman (RSA) 2048-bit self-signed server certificate valid for 3650 days. Select `<XCSH_WORKDIR>`, `<XCSH_CERT_FILE>`, and `<XCSH_KEY_FILE>` as absolute paths outside Git. Create the parent directories for those files first. Replace `<XCSH_DOMAINNAME>` and `<XCSH_COMPANION_DOMAINNAME>` with names you own.
OpenSSL generates inputs; the provider prepares and encrypts them without calling OpenSSL, xcsh, or vesctl.

Use these same local files in a separately owned xcsh example if needed. Each tool must manage its own XC resource name and references. Shared material does not imply shared resource ownership. Interception requires a separate signing certificate authority (CA); use the [CA recipe](.././input-lifecycle/#interception-signing-ca).

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

## Prepare local inputs

Select an existing leaf-first Privacy Enhanced Mail (PEM) chain and matching key, or create self-signed material outside Git. The following recipe creates
a Rivest–Shamir–Adleman (RSA) 2048-bit self-signed server certificate valid for 3650 days. Select `<XCSH_WORKDIR>`, `<XCSH_CERT_FILE>`, and `<XCSH_KEY_FILE>` as absolute paths outside Git. Create the parent directories for those files first. Replace `<XCSH_DOMAINNAME>` and `<XCSH_COMPANION_DOMAINNAME>` with names you own.
OpenSSL generates inputs; the provider prepares and encrypts them without calling OpenSSL, xcsh, or vesctl.

Use these same local files in a separately owned xcsh example if needed. Each tool must manage its own XC resource name and references. Shared material does not imply shared resource ownership. Interception requires a separate signing certificate authority (CA); use the [CA recipe](.././input-lifecycle/#interception-signing-ca).

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

## Review a saved plan

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
mkdir -p "$XCSH_WORKDIR/http-origin-mtls" "$XCSH_WORKDIR/wingman"
for file in main.tf variables.tf versions.tf outputs.tf dns.tf; do
  curl --silent --show-error --fail \
    "https://f5-sales-demo.github.io/certificate-management/_data/terraform/http-origin-mtls/$file" \
    --output "$XCSH_WORKDIR/http-origin-mtls/$file"
done
curl --silent --show-error --fail \
  "https://f5-sales-demo.github.io/certificate-management/_data/wingman/contract.json" \
  --output "$XCSH_WORKDIR/wingman/contract.json"
terraform -chdir="$XCSH_WORKDIR/deployment" init -upgrade
terraform -chdir="$XCSH_WORKDIR/deployment" validate
terraform -chdir="$XCSH_WORKDIR/deployment" plan \
  -out="$XCSH_WORKDIR/deployment/create.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" show \
  "$XCSH_WORKDIR/deployment/create.plan"
shasum -a 256 "$XCSH_WORKDIR/deployment/create.plan"
```

</div>

Hash the reviewed plan with `shasum -a 256 "$XCSH_WORKDIR/deployment/create.plan"`. Expect one named certificate, one HTTPS load balancer, one HTTP DNS companion, and a namespace read. Confirm the names, hostname, references, and
ownership before applying. Protect the dependency lockfile, saved plans, state, and logs. They contain encrypted material and local paths. Read
[saved-plan input changes](.././input-lifecycle/#saved-plans) before changing files after planning.

## Apply the configuration

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_API_URL XCSH_API_TOKEN XCSH_NAMESPACE XCSH_LB_NAME XCSH_DOMAINNAME XCSH_CERT_FILE XCSH_KEY_FILE">

```bash
terraform -chdir="$XCSH_WORKDIR/deployment" apply \
  "$XCSH_WORKDIR/deployment/create.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" output
```

</div>

Expect endpoint, SHA-256 certificate fingerprint, expiration, and encryption-context digest outputs. The provider does not expose plaintext private keys. The companion owns only this hostname’s managed DNS association; the configuration does not replace the tenant DNS zone.
