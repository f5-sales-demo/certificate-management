---
title: Input variants
description: Prepare certificates from protected PEM or PKCS#12 and encrypt raw stdin.
sidebar:
  label: Input variants
  order: 1
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Choose the input form for your existing certificate and key; use new artifact filenames on retries.

## Protected PEM

Supply `chain1.pem` and matching `protected-key.pem`; pass the name of the environment variable holding the input passphrase.

```bash
read -r -s -p 'Input key passphrase: ' TLS_INPUT_PASSWORD
printf '\n'
export TLS_INPUT_PASSWORD
xcsh blindfold certificate --cert chain1.pem --key protected-key.pem \
  --passphrase-env TLS_INPUT_PASSWORD --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" \
  --output-file protected-certificate.json > protected-report.json 2> protected.err
unset TLS_INPUT_PASSWORD
```

Expect `prepared`; native preparation decrypts and normalizes the key before encryption. [Preview and apply](../#certificate-use) the saved manifest using its filename.

## PKCS#12

Supply `server.p12` containing one private key, its matching leaf certificate, and issuing chain.

```bash
read -r -s -p 'Bundle password: ' TLS_INPUT_PASSWORD
printf '\n'
export TLS_INPUT_PASSWORD
xcsh blindfold certificate --bundle server.p12 --passphrase-env TLS_INPUT_PASSWORD \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" \
  --output-file bundle-certificate.json > bundle-report.json 2> bundle.err
unset TLS_INPUT_PASSWORD
```

Expect `prepared`; an incorrect password or multiple private keys fails. [Preview and apply](../#certificate-use) `bundle-certificate.json`.

## Raw stdin

Use the [paired public files](../#public-material) to encrypt redirected raw key bytes offline.

```bash
xcsh blindfold encrypt --public-key tenant-public-key.json \
  --policy-document policy.json --encoding location --output-file stdin.location - \
  < server1-key.pem > stdin-report.json 2> stdin.err
```

Expect `prepared` and a `string:///` location. Raw encryption preserves input bytes; [native certificate preparation](../#certificate-use) validates and normalizes certificate inputs.
