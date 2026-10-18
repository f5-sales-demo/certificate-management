---
title: Client mTLS — Configure
description: Configure for the Client mTLS certificate workflow.
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

## Download the shared configuration

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

Initialize a new private synthetic CA directory once, then issue a client certificate with `clientAuth`. Set Client CA
file to `ca.pem`, Client certificate/key files to `clients/<client>/certificate.pem` and `key.pem`, and Client CRL file
to `crls/<revision>.pem` under that directory.

## Create client material

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

## Review the saved plan

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CLIENT_CA_FILE XCSH_CLIENT_CRL_FILE XCSH_CLIENT_CRL_REVISION">

```bash
python3 - "$configuration/client.auto.tfvars.json" "$XCSH_CLIENT_CA_FILE" "$XCSH_CLIENT_CRL_FILE" "$XCSH_CLIENT_CRL_REVISION" <<'PY'
import json
import os
import sys
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

Deploy the qualified Wingman image first. Publish the exact public CRL route and verify its bytes and signature, then
enable optional client trust and the ordered Service Policy with `no_crl`. No XC CRL object is created. Review and hash
fresh saved plans and reject unrelated changes or retained-resource replacement. Finish with a full zero-change plan.

Apply the reviewed plan:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR">

```bash
terraform -chdir="$configuration" apply client.plan
```

</div>

The policy denies POST, PUT and PATCH on exact `/mtls/write` when XFCC is absent, then allows other traffic.
Qualification must prove the edge sanitizes client-supplied XFCC before policy evaluation. The origin parser alone
cannot establish edge trust. A header bypass fails acceptance and requires rollback.
