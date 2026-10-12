---
title: Terraform
description: Prepare certificate keys with native Blindfold and deploy HTTPS using Terraform.
sidebar:
  label: Terraform
  order: 3
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Deploy a named certificate and HTTPS load balancer with native provider encryption. The HTTP companion maintains managed Domain Name System (DNS) records and redirects requests to HTTPS. A built-in JavaScript Object Notation (JSON) response identifies the example; you need no origin service or xcsh installation.

## Prerequisites

Allow about 20 minutes plus certificate propagation. Install Terraform **1.11 or later**; this walkthrough is qualified with **1.16.3** and
**`f5-sales-demo/xcsh` 15.7.2**. Provide an existing namespace, certificate permissions, load-balancer capacity, and a hostname in a tenant-managed
DNS zone. Terraform reads the namespace as a data source and never owns it.

Set `XCSH_API_URL` to your tenant console URL and `XCSH_API_TOKEN` to a session credential. These are **provider environment settings**, independent of the xcsh command-line interface (CLI). Keep credentials out of HashiCorp Configuration Language (HCL), variable files, plans, and shell history. Enter the token without echo:

```bash
export XCSH_API_URL='https://example-corp.console.ves.volterra.io'
read -r -s XCSH_API_TOKEN
export XCSH_API_TOKEN
```

[HCL source](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/named-certificate) is authoritative. Use a dedicated private working directory and state for each example. Review the [certificate surfaces](./certificate-surfaces/) before selecting a prerequisite-bound configuration.

## Local certificate inputs

Select an existing leaf-first Privacy Enhanced Mail (PEM) chain and matching key, or generate demo material outside Git. The following recipe creates
a Rivest–Shamir–Adleman (RSA) 2048-bit self-signed server certificate valid for 3650 days. Replace these synthetic hostnames with the names you own.
OpenSSL generates inputs; the provider prepares and encrypts them without calling OpenSSL, xcsh, or vesctl.

```bash
umask 077
export XCSH_WORKDIR="$HOME/.local/state/terraform-certificate-example"
mkdir -p "$XCSH_WORKDIR/material" "$XCSH_WORKDIR/deployment"
chmod 700 "$XCSH_WORKDIR" "$XCSH_WORKDIR/material" "$XCSH_WORKDIR/deployment"
export XCSH_DOMAINNAME='tls.example.com'
export XCSH_COMPANION_DOMAINNAME='cli-tls.example.com'
openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 3650 \
  -subj "/CN=$XCSH_DOMAINNAME" \
  -addext 'basicConstraints=critical,CA:false' \
  -addext 'keyUsage=critical,digitalSignature,keyEncipherment' \
  -addext 'extendedKeyUsage=serverAuth' \
  -addext "subjectAltName=DNS:$XCSH_DOMAINNAME,DNS:$XCSH_COMPANION_DOMAINNAME" \
  -keyout "$XCSH_WORKDIR/material/server-key.pem" \
  -out "$XCSH_WORKDIR/material/server.pem"
export TF_VAR_certificate_file="$XCSH_WORKDIR/material/server.pem"
export TF_VAR_private_key_file="$XCSH_WORKDIR/material/server-key.pem"
export TF_VAR_namespace='demo-app'
export TF_VAR_name='example-tls'
export TF_VAR_domain="$XCSH_DOMAINNAME"
```

Use these same local files in a separately owned xcsh example if needed. Each tool must manage its own XC resource name and references. Shared material does not imply shared resource ownership. Interception requires a separate signing certificate authority (CA); use the [CA recipe](./input-lifecycle/#interception-signing-ca).

## Review a saved plan

Copy the pinned configuration into the private deployment directory. The provider uses `blindfold.certificate_file` and `blindfold.private_key_file`,
retrieves the tenant public key and default `shared/ves-io-allow-volterra` policy, and computes the encrypted key location. Leave `certificate_url`,
`private_key`, and `blindfold.encrypted_location` unset.

```bash
for file in versions.tf variables.tf main.tf outputs.tf; do
  curl --silent --show-error --fail \
    "https://f5-sales-demo.github.io/certificate-management/_data/terraform/named-certificate/$file" \
    --output "$XCSH_WORKDIR/deployment/$file"
done
terraform -chdir="$XCSH_WORKDIR/deployment" init
terraform -chdir="$XCSH_WORKDIR/deployment" validate
terraform -chdir="$XCSH_WORKDIR/deployment" plan \
  -out="$XCSH_WORKDIR/deployment/create.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" show \
  "$XCSH_WORKDIR/deployment/create.plan"
```

Expect one named certificate, one HTTPS load balancer, one HTTP DNS companion, and a namespace read. Confirm the names, hostname, references, and
ownership before applying. Protect the dependency lock file, saved plans, state, and logs. They contain encrypted material and local paths. Read
[saved-plan input changes](./input-lifecycle/#saved-plans) before changing files after planning.

## Apply native preparation

```bash
terraform -chdir="$XCSH_WORKDIR/deployment" apply \
  "$XCSH_WORKDIR/deployment/create.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" output
```

Expect endpoint, SHA-256 certificate fingerprint, expiration, and encryption-context digest outputs. The provider does not expose plaintext private keys. The companion owns only this hostname’s managed DNS association; the configuration does not replace the tenant DNS zone.

## Verify

Check trust, hostname, the served leaf fingerprint, HTTP status, and response content. Self-signed demo certificates require explicit trust; use your public chain as the trust asset.

```bash
openssl s_client -connect "$XCSH_DOMAINNAME:443" \
  -servername "$XCSH_DOMAINNAME" -verify_hostname "$XCSH_DOMAINNAME" \
  -verify_return_error -CAfile "$TF_VAR_certificate_file" -showcerts \
  < /dev/null > "$XCSH_WORKDIR/handshake.txt" \
  2> "$XCSH_WORKDIR/handshake.err"
openssl x509 -in "$TF_VAR_certificate_file" -noout -sha256 -fingerprint \
  > "$XCSH_WORKDIR/expected.sha256"
openssl x509 -in "$XCSH_WORKDIR/handshake.txt" -noout -sha256 -fingerprint \
  > "$XCSH_WORKDIR/served.sha256"
cmp "$XCSH_WORKDIR/expected.sha256" "$XCSH_WORKDIR/served.sha256"
curl --silent --show-error --fail --cacert "$TF_VAR_certificate_file" \
  "https://$XCSH_DOMAINNAME/get" --output "$XCSH_WORKDIR/response.json" \
  --write-out '%{http_code}\n'
python3 -c 'import json,sys; assert json.load(open(sys.argv[1])) == {"example":"terraform-certificate","native_blindfold":True}' \
  "$XCSH_WORKDIR/response.json"
terraform -chdir="$XCSH_WORKDIR/deployment" plan -detailed-exitcode
```

Expect matching fingerprints, HTTP `200`, the identifying JSON object, and exit `0` with **No changes** after a new Terraform process. Exit `2` means a change; exit `1` means an error. Allow propagation and retry verification if a replacement has not reached the serving edge.

The retained [Terraform endpoint](https://certificate-management-terraform.f5-sales-demo.com/get) and [xcsh
endpoint](https://certificate-management.f5-sales-demo.com/get) serve the same [public trust certificate](../../assets/certificate-management.pem).
[Showcase evidence](../../assets/terraform-showcase-acceptance.json) records its own measured gates. The [surface matrix](./certificate-surfaces/)
separates historical lifecycle evidence from served TLS evidence. Provider issue
[#2539](https://github.com/f5-sales-demo/terraform-provider-xcsh/issues/2539) tracks broader scheduled acceptance failures separately.

## Renew

Keep the key algorithm unchanged when renewing a referenced certificate. Retain the old pair privately for rollback. Generate or obtain new matching material, validate it, then replace both configured inputs before making a new saved plan.

```bash
terraform -chdir="$XCSH_WORKDIR/deployment" plan \
  -out="$XCSH_WORKDIR/deployment/renew.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" show \
  "$XCSH_WORKDIR/deployment/renew.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" apply \
  "$XCSH_WORKDIR/deployment/renew.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" plan -detailed-exitcode
```

Expect one material update followed by exit `0`. Repeat the strict verification commands using the new trust certificate and compare the served
fingerprint. If xcsh uses the same inputs, rotate its separately owned certificate once after Terraform verification, preserving its metadata,
options, name, and references. Keep its previous saved manifest privately.

## Clean up

Run cleanup only when you choose to retire your Terraform deployment. Review the saved destruction plan: it must contain only resources owned by this state, with no namespace or xcsh resource deletion.

```bash
terraform -chdir="$XCSH_WORKDIR/deployment" plan -destroy \
  -out="$XCSH_WORKDIR/deployment/destroy.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" show \
  "$XCSH_WORKDIR/deployment/destroy.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" apply \
  "$XCSH_WORKDIR/deployment/destroy.plan"
unset XCSH_API_TOKEN
```

The published showcase remains retained in private owner state. See the [input and lifecycle reference](./input-lifecycle/) for protected files, write-only values, import, drift, and key-algorithm cutovers.
