---
title: Terraform — Maintain
description: Maintain for the Terraform certificate workflow.
sidebar:
  label: Maintain
  order: 5
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../verify/
  label: Verify
next:
  link: ../remove/
  label: Remove
---

## Maintain steps

Keep the key algorithm unchanged when renewing a referenced certificate. Retain the old pair privately for rollback. Generate or obtain new matching material, validate it, then replace both configured inputs before making a new saved plan.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_RENEWED_CERT_FILE XCSH_RENEWED_KEY_FILE XCSH_API_URL XCSH_API_TOKEN XCSH_NAMESPACE XCSH_LB_NAME XCSH_DOMAINNAME">

```bash
export TF_VAR_certificate_file="$XCSH_RENEWED_CERT_FILE"
export TF_VAR_private_key_file="$XCSH_RENEWED_KEY_FILE"
terraform -chdir="$XCSH_WORKDIR/deployment" plan \
  -out="$XCSH_WORKDIR/deployment/renew.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" show \
  "$XCSH_WORKDIR/deployment/renew.plan"
shasum -a 256 "$XCSH_WORKDIR/deployment/renew.plan"
```

</div>

## Apply the reviewed plan

Confirm the exact owned resources and saved-plan hash before running the apply command.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_RENEWED_CERT_FILE XCSH_RENEWED_KEY_FILE XCSH_API_URL XCSH_API_TOKEN XCSH_NAMESPACE XCSH_LB_NAME XCSH_DOMAINNAME">

```bash
terraform -chdir="$XCSH_WORKDIR/deployment" apply \
  "$XCSH_WORKDIR/deployment/renew.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" plan -detailed-exitcode
```

</div>

Expect one material update followed by exit `0`. Select the renewed certificate and key as `<XCSH_CERT_FILE>` and `<XCSH_KEY_FILE>` in Customize examples before repeating the strict verification commands and compare the served
fingerprint. If xcsh uses the same inputs, rotate its separately owned certificate once after Terraform verification, preserving its metadata,
options, name, and references. Keep its previous saved manifest privately.
