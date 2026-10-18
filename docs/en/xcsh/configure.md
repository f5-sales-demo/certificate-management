---
title: xcsh — Configure
description: Configure for the xcsh certificate workflow.
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

### Prepare local inputs

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR">

```bash
umask 077
mkdir -p "$XCSH_WORKDIR"
chmod 700 "$XCSH_WORKDIR"
cd "$XCSH_WORKDIR"
```

</div>

Native preparation independently validates the certificate/key pair and chain, retrieves public material, and encrypts the normalized key. Supply leaf-first `<XCSH_CERT_FILE>` and matching `<XCSH_KEY_FILE>`; choose an owned certificate name for `XCSH_CERT_NAME`. See [Input variants](.././input-workflows/) for protected inputs.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE XCSH_CERT_NAME XCSH_CERT_FILE XCSH_KEY_FILE">

```bash
xcsh blindfold certificate --cert "$XCSH_CERT_FILE" --key "$XCSH_KEY_FILE" \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" --output-file certificate1.json \
  > certificate1-prepared.json 2> certificate1-prepared.err
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" --dry-run client -o json \
  > certificate1-preview.json 2> certificate1-preview.err
```

</div>

Expect `prepared` and a preview without a tenant write. Inspect `certificate1-preview.json`, then apply and reapply the identical saved manifest:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE">

```bash
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" -o json \
  > certificate1-apply.json 2> certificate1-apply.err
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" -o json \
  > certificate1-reapply.json 2> certificate1-reapply.err
```

</div>

Expect `created` for a missing name, `updated` for changed configuration, and `unchanged` on identical reapply. Retain the saved manifest: preparing it again produces new randomized ciphertext.
