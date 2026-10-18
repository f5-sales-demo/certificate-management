---
title: xcsh — Remove
description: Remove for the xcsh certificate workflow.
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

Detach dependent consumers before removing your exclusively owned certificate through xcsh. Confirm the exact resource and namespace, check `xcsh delete --help` for the current resource deletion interface, and verify named API absence. Retain private manifests for recovery. Never remove Terraform-owned or retained demonstration resources.

For infrastructure retirement, follow [Terraform Remove](../../terraform/remove/) in its independently owned state. Removing a certificate manifest does not tear down its consumers.

## Review and remove the owned certificate

After detaching references, preview the exact certificate name in your authenticated xcsh context. Inspect the saved report before deleting that same name.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE XCSH_CERT_NAME XCSH_WORKDIR">

```bash
umask 077
xcsh delete certificates "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" --dry-run client -o json \
  > "$XCSH_WORKDIR/certificate-remove-preview.json"
xcsh delete certificates "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" -o json \
  > "$XCSH_WORKDIR/certificate-remove.json"
```

</div>

## Verify named absence

Use the same tenant and namespace as the authenticated context. Require an authenticated API response showing that the named certificate is absent; authorization failures and transport errors remain failures.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_API_URL XCSH_API_TOKEN XCSH_NAMESPACE XCSH_CERT_NAME XCSH_WORKDIR">

```bash
status=$(curl --silent --show-error --header "Authorization: APIToken $XCSH_API_TOKEN" \
  "$XCSH_API_URL/api/config/namespaces/$XCSH_NAMESPACE/certificates/$XCSH_CERT_NAME" \
  --output "$XCSH_WORKDIR/certificate-remove-readback.json" --write-out '%{http_code}')
test "$status" = 404
```

</div>

Expect exit `0` from the absence assertion. Preserve the private reports and manifests for recovery; retire unused session credentials when all checks finish.
