---
title: Client mTLS — Verify
description: Verify for the Client mTLS certificate workflow.
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

Use a new cURL process and unique challenge for every probe. Keep server verification enabled. Match the response
challenge and `forwarded_client_certificate_sha256` to the client leaf fingerprint; `origin_server_certificate_sha256`
identifies the Wingman server certificate separately. Synthetic acknowledgments store and echo no submitted data.

## Verify trusted requests

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CLIENT_CA_FILE XCSH_CLIENT_CERT_FILE XCSH_CLIENT_CRL_FILE XCSH_CLIENT_CRL_REVISION XCSH_CLIENT_KEY_FILE XCSH_DOMAINNAME XCSH_WORKDIR">

```bash
configuration="$XCSH_WORKDIR/deployment"
challenge=$(openssl rand -hex 16)
curl --silent --show-error --fail "https://$XCSH_DOMAINNAME/mtls/identity?challenge=$challenge"
openssl x509 -in "$XCSH_CLIENT_CERT_FILE" -noout -fingerprint -sha256
for method in POST PUT PATCH; do
  challenge=$(openssl rand -hex 16)
  curl --silent --show-error --fail --cert "$XCSH_CLIENT_CERT_FILE" --key "$XCSH_CLIENT_KEY_FILE" \
    --request "$method" "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
  curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' \
    --request "$method" "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
done
curl --silent --show-error --fail "http://$XCSH_DOMAINNAME/mtls/crl/$XCSH_CLIENT_CRL_REVISION.pem" --output "$XCSH_WORKDIR/downloaded-crl.pem"
cmp "$XCSH_CLIENT_CRL_FILE" "$XCSH_WORKDIR/downloaded-crl.pem"
openssl crl -in "$XCSH_WORKDIR/downloaded-crl.pem" -noout -verify -CAfile "$XCSH_CLIENT_CA_FILE"
openssl crl -in "$XCSH_WORKDIR/downloaded-crl.pem" -noout -issuer -lastupdate -nextupdate -text
terraform -chdir="$configuration" output -json client_mtls_inventory
terraform -chdir="$configuration" plan -detailed-exitcode
```

</div>

## Reject forged client identity

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_DOMAINNAME">

```bash
for method in POST PUT PATCH; do
  for value in 'Hash=forged' 'Cert="%zz"' 'Hash=one;Hash=two'; do
    challenge=$(openssl rand -hex 16)
    curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' \
      --request "$method" --header "X-Forwarded-Client-Cert: $value" \
      "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
  done
  challenge=$(openssl rand -hex 16)
  curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' \
    --request "$method" --header 'X-Forwarded-Client-Cert: Hash=one' \
    --header 'X-Forwarded-Client-Cert: Hash=two' \
    "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
done
```

</div>

Expect public identity HTTP 200 with an empty client fingerprint, trusted writes HTTP 200, and certificate-free or
forged-header writes HTTP 403. Require duplicate and malformed header denial, including a copied complete valid XFCC
value presented without a client certificate. Presented untrusted and expired certificates must fail TLS before the
handler returns a challenge. With `no_crl`, a locally revoked certificate remains accepted by the edge until it expires
or its issuing CA loses trust. Prove and record that behavior explicitly; do not claim edge revocation.

Recheck `/get`, `/wingman/get`, all HTTP redirects outside the exact CRL paths, server fingerprints, retained resource
IDs and Default pool responses. Repeat Wingman injection, READY, authorized unseal, denial, identity chain, TLS,
restart, cleanup and credential revocation after publishing its changed image. Record client acceptance separately from
the historical certificate matrix.
