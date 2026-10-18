---
title: Terraform — Verify
description: Verify for the Terraform certificate workflow.
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

Check trust, hostname, the served leaf fingerprint, HTTP status, and response content. Self-signed certificates require explicit trust; use your public chain as the trust asset.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_DOMAINNAME XCSH_WORKDIR XCSH_CERT_FILE XCSH_API_URL XCSH_API_TOKEN XCSH_NAMESPACE XCSH_LB_NAME XCSH_KEY_FILE">

```bash
openssl s_client -connect "$XCSH_DOMAINNAME:443" \
  -servername "$XCSH_DOMAINNAME" -verify_hostname "$XCSH_DOMAINNAME" \
  -verify_return_error -CAfile "$XCSH_CERT_FILE" -showcerts \
  < /dev/null > "$XCSH_WORKDIR/handshake.txt" \
  2> "$XCSH_WORKDIR/handshake.err"
openssl x509 -in "$XCSH_CERT_FILE" -noout -sha256 -fingerprint \
  > "$XCSH_WORKDIR/expected.sha256"
openssl x509 -in "$XCSH_WORKDIR/handshake.txt" -noout -sha256 -fingerprint \
  > "$XCSH_WORKDIR/served.sha256"
cmp "$XCSH_WORKDIR/expected.sha256" "$XCSH_WORKDIR/served.sha256"
curl --silent --show-error --fail --cacert "$XCSH_CERT_FILE" \
  "https://$XCSH_DOMAINNAME/get" --output "$XCSH_WORKDIR/response.json" \
  --write-out '%{http_code}\n'
python3 -c 'import json,sys; assert json.load(open(sys.argv[1])) == {"example":"terraform-certificate","native_blindfold":True}' \
  "$XCSH_WORKDIR/response.json"
terraform -chdir="$XCSH_WORKDIR/deployment" plan -detailed-exitcode
```

</div>

Expect matching fingerprints, HTTP `200`, the identifying JSON object, and exit `0` with **No changes** after a new Terraform process. Exit `2` means a change; exit `1` means an error. Allow propagation and retry verification if a replacement has not reached the serving edge.
