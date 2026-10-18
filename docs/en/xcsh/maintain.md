---
title: xcsh — Maintain
description: Maintain for the xcsh certificate workflow.
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

Supply renewed `<XCSH_RENEWED_CERT_FILE>` and matching `<XCSH_RENEWED_KEY_FILE>` with the same key algorithm for a referenced certificate. Prepare the replacement and inspect its preview:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE XCSH_CERT_NAME XCSH_RENEWED_CERT_FILE XCSH_RENEWED_KEY_FILE">

```bash
xcsh blindfold certificate --cert "$XCSH_RENEWED_CERT_FILE" --key "$XCSH_RENEWED_KEY_FILE" \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" --output-file certificate2.json \
  > certificate2-prepared.json 2> certificate2-prepared.err
xcsh apply -f certificate2.json -n "$XCSH_NAMESPACE" --dry-run client -o json \
  > certificate2-preview.json 2> certificate2-preview.err
```

</div>

Apply the replacement to the same name:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE">

```bash
xcsh apply -f certificate2.json -n "$XCSH_NAMESPACE" -o json \
  > certificate2-apply.json 2> certificate2-apply.err
```

</div>

Expect `updated`; verify the served certificate at your endpoint after propagation.
