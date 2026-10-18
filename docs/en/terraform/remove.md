---
title: Terraform — Remove
description: Remove for the Terraform certificate workflow.
sidebar:
  label: Remove
  order: 6
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../maintain/
  label: Maintain
next:
  link: ../
  label: Overview
---

## Remove steps

Run cleanup only when you choose to retire your Terraform deployment. Review the saved destruction plan: it must contain only resources owned by this state, with no namespace or xcsh resource deletion.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_API_TOKEN XCSH_WORKDIR XCSH_API_URL XCSH_NAMESPACE XCSH_LB_NAME XCSH_DOMAINNAME XCSH_CERT_FILE XCSH_KEY_FILE">

```bash
terraform -chdir="$XCSH_WORKDIR/deployment" plan -destroy \
  -out="$XCSH_WORKDIR/deployment/destroy.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" show \
  "$XCSH_WORKDIR/deployment/destroy.plan"
terraform -chdir="$XCSH_WORKDIR/deployment" apply \
  "$XCSH_WORKDIR/deployment/destroy.plan"
unset XCSH_API_TOKEN
```

</div>

See the [input and lifecycle reference](.././input-lifecycle/) for protected files, write-only values, import, drift, and key-algorithm cutovers.
