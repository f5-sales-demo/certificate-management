---
title: xcsh
description: Encrypt private keys with Blindfold, apply certificate manifests, and verify HTTPS.
sidebar:
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Use the latest [xcsh](https://f5-sales-demo.github.io/xcsh/) with an [authenticated environment](https://f5-sales-demo.github.io/xcsh/en/f5-distributed-cloud/contexts-namespaces/), existing certificate/key inputs, and your namespace in `XCSH_NAMESPACE`. Keep keys, encrypted artifacts, and resource reports in a private directory outside Git.

## Public material

The tenant public key and TLS secret policy provide the paired public material for local Blindfold encryption.

```bash
umask 077
xcsh blindfold public-key --output-file tenant-public-key.json \
  > public-key-report.json 2> public-key.err
xcsh blindfold policy --policy shared/ves-io-allow-volterra \
  --output-file policy.json > policy-report.json 2> policy.err
```

Expect two JSON documents for the same tenant; retrieve a fresh pair when its public key or policy changes.

## Private-key encryption

Encrypt the existing `server1-key.pem` using both files; paired documents select offline encryption.

```bash
xcsh blindfold encrypt --input server1-key.pem \
  --public-key tenant-public-key.json --policy-document policy.json \
  --encoding location --output-file key1.location \
  > encrypt1-report.json 2> encrypt1.err
```

Expect `prepared`; `key1.location` contains the `string:///` location used in `spec.private_key.blindfold_secret_info.location`.

## Certificate use

Native preparation independently validates the certificate/key pair and chain, retrieves public material, and encrypts the normalized key. Supply leaf-first `chain1.pem` and matching `server1-key.pem`; choose an owned certificate name for `XCSH_CERT_NAME`. See [Input variants](./input-workflows/) for protected inputs.

```bash
xcsh blindfold certificate --cert chain1.pem --key server1-key.pem \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" --output-file certificate1.json \
  > certificate1-prepared.json 2> certificate1-prepared.err
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" --dry-run client -o json \
  > certificate1-preview.json 2> certificate1-preview.err
```

Expect `prepared` and a preview without a tenant write. Inspect `certificate1-preview.json`, then apply and reapply the identical saved manifest:

```bash
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" -o json \
  > certificate1-apply.json 2> certificate1-apply.err
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" -o json \
  > certificate1-reapply.json 2> certificate1-reapply.err
```

Expect `created` for a missing name, `updated` for changed configuration, and `unchanged` on identical reapply. Retain the saved manifest: preparing it again produces new randomized ciphertext.

Supply renewed `chain2.pem` and matching `server2-key.pem` with the same key algorithm for a referenced certificate. Prepare the replacement and inspect its preview:

```bash
xcsh blindfold certificate --cert chain2.pem --key server2-key.pem \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" --output-file certificate2.json \
  > certificate2-prepared.json 2> certificate2-prepared.err
xcsh apply -f certificate2.json -n "$XCSH_NAMESPACE" --dry-run client -o json \
  > certificate2-preview.json 2> certificate2-preview.err
```

Apply the replacement to the same name:

```bash
xcsh apply -f certificate2.json -n "$XCSH_NAMESPACE" -o json \
  > certificate2-apply.json 2> certificate2-apply.err
```

Expect `updated`; verify the served certificate at your endpoint after propagation.

## Proof

The existing [showcase endpoint](https://certificate-management.f5-sales-demo.com/get) uses a self-signed certificate. Download its [public trust certificate](../../assets/certificate-management.pem), verify trust and hostname, and compare the served leaf fingerprint:

```bash
curl --silent --show-error --fail \
  https://f5-sales-demo.github.io/certificate-management/assets/certificate-management.pem \
  --output showcase-trust.pem
openssl s_client -connect certificate-management.f5-sales-demo.com:443 \
  -servername certificate-management.f5-sales-demo.com \
  -verify_hostname certificate-management.f5-sales-demo.com -verify_return_error \
  -CAfile showcase-trust.pem -showcerts < /dev/null \
  > showcase-handshake.txt 2> showcase-handshake.err
openssl x509 -in showcase-trust.pem -noout -sha256 -fingerprint > expected.sha256
openssl x509 -in showcase-handshake.txt -noout -sha256 -fingerprint > served.sha256
cmp expected.sha256 served.sha256
curl --silent --show-error --fail --cacert showcase-trust.pem \
  https://certificate-management.f5-sales-demo.com/get \
  --output showcase-response.json --write-out '%{http_code}\n'
```

Expect matching fingerprints and HTTP `200` with a JSON response. [Current evidence](../../assets/xcsh-showcase-acceptance.json) records the verified commands and endpoint checks; [Command reference](./command-reference/) lists flags, limits, and recovery guidance.
