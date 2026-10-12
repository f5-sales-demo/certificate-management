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

Supply `<XCSH_CERT_FILE>` and matching `<XCSH_PROTECTED_KEY_FILE>`; pass the name of the environment variable holding the input passphrase.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE XCSH_CERT_NAME XCSH_CERT_FILE XCSH_PROTECTED_KEY_FILE XCSH_TLS_INPUT_PASSWORD">

```bash
if [ -z "${XCSH_TLS_INPUT_PASSWORD:-}" ]; then
  read -r -s -p 'Input key passphrase: ' XCSH_TLS_INPUT_PASSWORD
  printf '\n'
fi
export XCSH_TLS_INPUT_PASSWORD
xcsh blindfold certificate --cert "$XCSH_CERT_FILE" --key "$XCSH_PROTECTED_KEY_FILE" \
  --passphrase-env XCSH_TLS_INPUT_PASSWORD --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" \
  --output-file protected-certificate.json > protected-report.json 2> protected.err
unset XCSH_TLS_INPUT_PASSWORD
```

</div>

Expect `prepared`; native preparation decrypts and normalizes the key before encryption. [Preview and apply](../#certificate-use) the saved manifest using its filename.

## PKCS#12

Supply `<XCSH_P12_FILE>` containing one private key, its matching leaf certificate, and issuing chain.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE XCSH_CERT_NAME XCSH_P12_FILE XCSH_TLS_INPUT_PASSWORD">

```bash
if [ -z "${XCSH_TLS_INPUT_PASSWORD:-}" ]; then
  read -r -s -p 'Bundle password: ' XCSH_TLS_INPUT_PASSWORD
  printf '\n'
fi
export XCSH_TLS_INPUT_PASSWORD
xcsh blindfold certificate --bundle "$XCSH_P12_FILE" --passphrase-env XCSH_TLS_INPUT_PASSWORD \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" \
  --output-file bundle-certificate.json > bundle-report.json 2> bundle.err
unset XCSH_TLS_INPUT_PASSWORD
```

</div>

Expect `prepared`; an incorrect password or multiple private keys fails. [Preview and apply](../#certificate-use) `bundle-certificate.json`.

## Raw stdin

Use the [paired public files](../#public-material) to encrypt redirected raw key bytes offline.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_KEY_FILE">

```bash
xcsh blindfold encrypt --public-key tenant-public-key.json \
  --policy-document policy.json --encoding location --output-file stdin.location - \
  < "$XCSH_KEY_FILE" > stdin-report.json 2> stdin.err
```

</div>

Expect `prepared` and a `string:///` location. Raw encryption preserves input bytes; [native certificate preparation](../#certificate-use) validates and normalizes certificate inputs.
