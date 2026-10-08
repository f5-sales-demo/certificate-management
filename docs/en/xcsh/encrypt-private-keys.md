---
title: Encrypt private keys
description: Retrieve tenant public material and retain an encrypted private-key location.
sidebar:
  label: Encrypt private keys
  order: 1
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Encrypt an existing unprotected PEM private key before sending it to F5 Distributed Cloud. Use the [overview configuration](../#before-you-begin), `server1-key.pem`, and the private directory from that setup. Allow about five minutes; this task creates no tenant resource.

## Retrieve tenant public material

Retrieve a paired tenant public key and platform TLS secret policy:

```bash
xcsh blindfold public-key --context-name certificate-admin \
  --output-file tenant-public-key.json > public-key-report.json 2> public-key.err
xcsh blindfold policy --context-name certificate-admin \
  --policy shared/ves-io-allow-volterra \
  --output-file policy.json > policy-report.json 2> policy.err
```

These files default to snake_case JSON. They contain public encryption material and tenant identity, so keep them private. Both documents must identify the same canonical tenant. Refresh the pair when the tenant key or policy changes.

## Encrypt the existing key

Use both documents to encrypt offline and save the textual location:

```bash
xcsh blindfold encrypt --input server1-key.pem \
  --public-key tenant-public-key.json --policy-document policy.json \
  --encoding location --output-file key1.location \
  > encrypt1-report.json 2> encrypt1.err
jq -e '.status == "prepared"' encrypt1-report.json > /dev/null
```

`key1.location` contains `string:///` followed by the base64 envelope. Paired documents make encryption offline; omit `--context-name`. Raw encryption preserves bytes and does not interpret certificate content. For protected PEM, use [native certificate input handling](../input-workflows/#use-a-protected-pem-key).

## Retain the location

Copy the location unchanged into `spec.private_key.blindfold_secret_info.location`. Keep exactly one `string:///` prefix. Ciphertext remains a sensitive operational artifact.

Encryption uses fresh randomness. Encrypting the same key again produces different ciphertext, so preserve the saved location and manifest when you want an unchanged reapply. The [command reference](../command-reference/#native-encryption-envelope) describes the envelope and output encodings.

Continue to [Create certificates](../create-certificates/) with `chain1.pem` and `key1.location`, or use native preparation there to validate and encrypt the matching pair together.
