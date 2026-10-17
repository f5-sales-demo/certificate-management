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

### Configuration

Supply `<XCSH_CERT_FILE>` and matching `<XCSH_PROTECTED_KEY_FILE>`; pass the name of the environment variable holding the input passphrase.

### Configure

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

Expect `prepared`; native preparation decrypts and normalizes the key before encryption. [Preview and apply](../#configure) the saved manifest using its filename.

### Verify

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE">

```bash
xcsh apply -f protected-certificate.json -n "$XCSH_NAMESPACE" --dry-run client -o json
xcsh apply -f protected-certificate.json -n "$XCSH_NAMESPACE" -o json
xcsh apply -f protected-certificate.json -n "$XCSH_NAMESPACE" -o json
```

</div>

Review the preview before applying. Expect `created` for a new resource and `unchanged` on identical reapply. Check encrypted readback and, after attaching the certificate to an HTTPS service, [verify served TLS](../#verify).

## PKCS#12

### Configuration

Supply `<XCSH_P12_FILE>` containing one private key, its matching leaf certificate, and issuing chain.

### Configure

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

Expect `prepared`; an incorrect password or multiple private keys fails. [Preview and apply](../#configure) `bundle-certificate.json`.

### Verify

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE">

```bash
xcsh apply -f bundle-certificate.json -n "$XCSH_NAMESPACE" --dry-run client -o json
xcsh apply -f bundle-certificate.json -n "$XCSH_NAMESPACE" -o json
xcsh apply -f bundle-certificate.json -n "$XCSH_NAMESPACE" -o json
```

</div>

Review the preview before applying. Expect `created` for a new resource and `unchanged` on identical reapply. Check encrypted readback and, after attaching the certificate to an HTTPS service, [verify served TLS](../#verify).

## Raw and offline

### Configuration

The tenant public key and TLS secret policy provide the paired public material for local Blindfold encryption.

<div data-xcsh-context="shell" data-xcsh-fields="">

```bash
umask 077
xcsh blindfold public-key --output-file tenant-public-key.json \
  > public-key-report.json 2> public-key.err
xcsh blindfold policy --policy shared/ves-io-allow-volterra \
  --output-file policy.json > policy-report.json 2> policy.err
```

</div>

Expect two JSON documents for the same tenant; retrieve a fresh pair when its public key or policy changes.

### Configure

Encrypt the existing `<XCSH_KEY_FILE>` using both files; paired documents select offline encryption.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_KEY_FILE">

```bash
xcsh blindfold encrypt --input "$XCSH_KEY_FILE" \
  --public-key tenant-public-key.json --policy-document policy.json \
  --encoding location --output-file key1.location \
  > encrypt1-report.json 2> encrypt1.err
```

</div>

Expect `prepared`; `key1.location` contains the `string:///` location used in `spec.private_key.blindfold_secret_info.location`.

Use the [paired public files](#raw-and-offline) to encrypt redirected raw key bytes offline.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_KEY_FILE">

```bash
xcsh blindfold encrypt --public-key tenant-public-key.json \
  --policy-document policy.json --encoding location --output-file stdin.location - \
  < "$XCSH_KEY_FILE" > stdin-report.json 2> stdin.err
```

</div>

Expect `prepared` and a `string:///` location. Raw encryption preserves input bytes; [native certificate preparation](../#configure) validates and normalizes certificate inputs.

### Verify

<div data-xcsh-context="shell" data-xcsh-fields="">

```bash
python3 -c 'from pathlib import Path; import base64; value=Path("stdin.location").read_text().strip(); assert value.startswith("string:///"); assert base64.b64decode(value[10:],validate=True)'
```

</div>

Expect a nonempty encoded envelope. This checks its format; raw encryption does not validate a certificate/key pair or prove TLS serving. Use native certificate preparation for certificate manifests.
