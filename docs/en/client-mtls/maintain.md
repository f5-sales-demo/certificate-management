---
title: Client mTLS — Maintain
description: Maintain for the Client mTLS certificate workflow.
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

Renew by issuing another client under the same CA with a new issuance name. It has a new serial and fingerprint; both
old and renewed certificates remain valid until explicit revocation.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CLIENT_CA_DIR XCSH_CLIENT_CRL_REVISION XCSH_CLIENT_NAME XCSH_WORKDIR">

```bash
python3 "$XCSH_WORKDIR/client_pki.py" issue "$XCSH_CLIENT_CA_DIR" --client "$XCSH_CLIENT_NAME-renewed"
python3 "$XCSH_WORKDIR/client_pki.py" revoke "$XCSH_CLIENT_CA_DIR" --client "$XCSH_CLIENT_NAME"
python3 "$XCSH_WORKDIR/client_pki.py" crl "$XCSH_CLIENT_CA_DIR" --revision "$XCSH_CLIENT_CRL_REVISION-next"
```

</div>

Add the newly signed CRL to `crl_revisions` and publish and verify its exact HTTP path through a fresh reviewed plan.
The CRL documents local revocation only. With fresh connections, verify the old and renewed clients still work at the
edge while their CA remains trusted. Renewal and local revocation do not invalidate an individual client at this
Regional Edge listener.

## Rotate CA trust

For CA rotation, initialize a separate private CA database and client. Concatenate the two public CA certificates into
the trusted bundle. You may publish both issuers' signed PEM CRLs as a public bundle; verify each signature and validity
window independently. The edge does not consume this CRL bundle. Preserve `xcsh_trusted_ca_list.client[0]` identity
while adding new trust. Prove both clients work during overlap, then remove old CA trust through a reviewed update and
prove old clients fail while new clients work. Retain prior public revisions until the transition is verified.
