---
title: xcsh — Verify
description: Verify for the xcsh certificate workflow.
sidebar:
  label: Verify
  order: 4
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../configure/
  label: Configure
next:
  link: ../maintain/
  label: Maintain
---

## Verify steps

Verify your selected `<XCSH_DOMAINNAME>` using your local public certificate `<XCSH_CERT_FILE>`. For a self-signed demonstration, this chain is the trust asset; for a CA-issued certificate, supply its trusted issuer chain. Compare the served leaf with the first certificate in your local file.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_DOMAINNAME XCSH_CERT_FILE">

```bash
openssl s_client -connect "$XCSH_DOMAINNAME:443" \
  -servername "$XCSH_DOMAINNAME" -verify_hostname "$XCSH_DOMAINNAME" \
  -verify_return_error -CAfile "$XCSH_CERT_FILE" -showcerts < /dev/null \
  > reader-handshake.txt 2> reader-handshake.err
openssl x509 -in "$XCSH_CERT_FILE" -noout -sha256 -fingerprint > reader-expected.sha256
openssl x509 -in reader-handshake.txt -noout -sha256 -fingerprint > reader-served.sha256
cmp reader-expected.sha256 reader-served.sha256
curl --silent --show-error --fail --cacert "$XCSH_CERT_FILE" \
  "https://$XCSH_DOMAINNAME/get" --output reader-response.json --write-out '%{http_code}\n'
```

</div>

Expect matching fingerprints and your application's expected status and content. After renewal, select the renewed public certificate in the form before repeating verification.
