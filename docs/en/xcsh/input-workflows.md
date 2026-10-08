---
title: Input workflows
description: Prepare manifests from protected PEM, PKCS#12, or stdin; encrypt raw inputs offline.
sidebar:
  label: Input workflows
  order: 4
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Complete [common setup](../#before-you-begin), then choose one input. Each native certificate example prepares a saved manifest without deployment. Use new artifact paths on retries. Allow about five minutes for preparation.

## Use a protected PEM key

Supply current `chain1.pem` and a matching `protected-key.pem`. Read the passphrase through protected Bash input or your secret manager. Pass its environment-variable name to xcsh:

```bash
read -r -s -p 'Input key passphrase: ' TLS_INPUT_PASSWORD
printf '\n'
export TLS_INPUT_PASSWORD
xcsh blindfold certificate --context-name certificate-admin \
  --cert chain1.pem --key protected-key.pem --passphrase-env TLS_INPUT_PASSWORD \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" \
  --output-file protected-certificate.json > protected-report.json 2> protected.err
unset TLS_INPUT_PASSWORD
jq -e '.status == "prepared"' protected-report.json > /dev/null
export XCSH_CERT_MANIFEST=protected-certificate.json
```

Continue to [Preview and apply](../create-certificates/#preview-and-apply) with this manifest. Native operations decrypt and normalize the protected key before encryption. Raw encryption preserves protected bytes and does not perform that conversion.

## Use a single-key PKCS#12 bundle

Supply `server.p12` containing one private key, its matching leaf certificate, and issuing chain. Read its password independently of the PEM example:

```bash
read -r -s -p 'Bundle password: ' TLS_INPUT_PASSWORD
printf '\n'
export TLS_INPUT_PASSWORD
xcsh blindfold certificate --context-name certificate-admin \
  --bundle server.p12 --passphrase-env TLS_INPUT_PASSWORD \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" \
  --output-file bundle-certificate.json > bundle-report.json 2> bundle.err
unset TLS_INPUT_PASSWORD
jq -e '.status == "prepared"' bundle-report.json > /dev/null
export XCSH_CERT_MANIFEST=bundle-certificate.json
```

Continue to [Preview and apply](../create-certificates/#preview-and-apply). Bundles with multiple private keys, including colliding key aliases, fail before deployment. A wrong or unavailable passphrase also fails. Choose `--bundle` or separate `--cert` and `--key` inputs, never both.

## Use redirected input

Native certificate preparation uses file paths. If your input arrives on standard input (stdin), save it in a new private file, then prepare the manifest. This example expects an unprotected key matching existing `chain1.pem` on redirected stdin:

```bash
( set -o noclobber; cat > stdin-key.pem )
xcsh blindfold certificate --context-name certificate-admin \
  --cert chain1.pem --key stdin-key.pem --name "$XCSH_CERT_NAME" \
  -n "$XCSH_NAMESPACE" --output-file stdin-certificate.json \
  > stdin-certificate-report.json 2> stdin-certificate.err
jq -e '.status == "prepared"' stdin-certificate-report.json > /dev/null
export XCSH_CERT_MANIFEST=stdin-certificate.json
```

Run this block with your key source redirected to it; do not enter the key interactively. Continue to [Preview and apply](../create-certificates/#preview-and-apply). Keep the saved input within the [private storage boundary](../#before-you-begin).

## Encrypt raw stdin or offline inputs

Raw encryption supports binary bytes and redirected stdin directly. Retrieve both documents using [Encrypt private keys](../encrypt-private-keys/#retrieve-tenant-public-material), then choose a text encoding:

```bash
xcsh blindfold encrypt --public-key tenant-public-key.json \
  --policy-document policy.json --encoding location --output-file stdin.location - \
  < server1-key.pem > stdin-report.json 2> stdin.err
xcsh blindfold encrypt --public-key tenant-public-key.json \
  --policy-document policy.json --encoding base64 --output-file bare-base64.txt \
  < server1-key.pem > bare-report.json 2> bare.err
```

These outputs contain encrypted bytes, not validated certificate manifests. Use native preparation above when administering certificates. See [input contracts and encodings](../command-reference/#supported-inputs-and-limits) for raw input choices, and [request-secrets commands](../command-reference/#operations-and-defaults) for the supported alternate command surface.
