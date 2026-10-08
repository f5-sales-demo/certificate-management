---
title: Input workflows
description: Use protected PEM, PKCS#12, stdin, offline material, and request-secrets equivalents.
sidebar:
  label: Input workflows
  order: 4
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Choose an input workflow after [common setup](../#before-you-begin). The examples use existing files in your private directory and new output paths. Raw encryption takes bytes unchanged; native certificate operations interpret and validate certificate inputs. Allow about five minutes for these preparation-only examples.

## Use a protected PEM key

Supply an existing `protected-key.pem` matching `chain1.pem`. Read its passphrase through protected Bash input or your secret manager, without tracing. Pass only the environment-variable name to xcsh:

```bash
read -r -s -p 'Input key passphrase: ' TLS_INPUT_PASSWORD
printf '\n'
export TLS_INPUT_PASSWORD
xcsh blindfold certificate --context-name certificate-admin \
  --cert chain1.pem --key protected-key.pem --passphrase-env TLS_INPUT_PASSWORD \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" \
  --output-file protected-certificate.json > protected-report.json 2> protected.err
```

Use `certificate`, `create`, or `replace` with `--passphrase-env` for protected inputs. Raw encryption does not decrypt a protected PEM file and would encrypt the protected bytes instead of the normalized key.

## Use a single-key PKCS#12 bundle

Supply `server.p12`, containing one matching private key, leaf certificate, and issuing chain. Set `TLS_INPUT_PASSWORD` to the bundle password using protected input if it differs from the PEM password. Choose either `--bundle` or `--cert` with `--key`:

```bash
xcsh blindfold certificate --context-name certificate-admin \
  --bundle server.p12 --passphrase-env TLS_INPUT_PASSWORD \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" \
  --output-file bundle-certificate.json > bundle-report.json 2> bundle.err
unset TLS_INPUT_PASSWORD
```

Bundles with multiple private keys fail before deployment, including colliding key aliases. A wrong or unavailable passphrase also fails. Native preparation retrieves public material online; paired offline documents are supported only by raw encryption.

## Encrypt stdin or offline inputs

Use `server1-key.pem` and the paired documents from [Encrypt private keys](../encrypt-private-keys/). Canonical encryption accepts one positional filename, `--input FILE`, `-` for redirected standard input (stdin), or redirected stdin with no filename. Do not combine positional input with `--input`; use `--` before a filename beginning with a dash.

```bash
cat server1-key.pem | xcsh blindfold encrypt \
  --public-key tenant-public-key.json --policy-document policy.json \
  --encoding location --output-file stdin.location - \
  > stdin-report.json 2> stdin.err
xcsh blindfold encrypt --public-key tenant-public-key.json \
  --policy-document policy.json --encoding base64 --output-file bare-base64.txt \
  < server1-key.pem > bare-report.json 2> bare.err
```

Binary plaintext is preserved. Missing interactive input fails immediately. Offline encryption requires both documents and performs no context resolution, credential lookup, or network access. Keep paired documents together.

## Use request-secrets equivalents

These three operations share xcsh's native context and encryption service. Retrieval defaults to camelCase YAML, while encryption defaults to bare base64:

```bash
xcsh request secrets get-public-key --context-name certificate-admin \
  --outfmt yaml --output-file public-key.yaml > compat-public-report.json 2> compat-public.err
xcsh request secrets get-policy-document --context-name certificate-admin \
  --namespace shared --name ves-io-allow-volterra --outfmt json \
  --output-file compat-policy.json > compat-policy-report.json 2> compat-policy.err
xcsh request secrets encrypt --public-key public-key.yaml \
  --policy-document compat-policy.json server1-key.pem \
  --encoding location --output-file compat.location > compat-report.json 2> compat.err
xcsh request secrets encrypt --public-key public-key.yaml \
  --policy-document compat-policy.json server1-key.pem \
  --outfile key.envelope --result-file binary-report.json > binary.out 2> binary.err
```

`compat.location` already has its single `string:///` prefix. `key.envelope` contains raw binary envelope bytes; binary `--outfile` has empty default stdout. For bare-base64 text, trim the final newline and prepend exactly one `string:///` before using a manifest location. These commands are syntax equivalents; they do not change authentication.

Use the prepared artifact with [Create certificates](../create-certificates/), or inspect output restrictions in the [Command reference](../command-reference/).
