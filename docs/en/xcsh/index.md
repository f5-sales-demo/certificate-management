---
title: xcsh
description: Encrypt private keys with Blindfold, apply certificate manifests, and verify HTTPS.
sidebar:
  label: xcsh
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Use the latest [xcsh](https://f5-sales-demo.github.io/xcsh/) with an [authenticated environment](https://f5-sales-demo.github.io/xcsh/en/f5-distributed-cloud/contexts-namespaces/), existing certificate/key inputs, and your namespace in `XCSH_NAMESPACE`. Keep keys, encrypted artifacts, and resource reports in a private directory outside Git.

For native Terraform preparation without the xcsh CLI, see the [Terraform walkthrough](../terraform/). Both retained endpoints serve the same public trust certificate; each tool owns separate resources.

## Private working directory

Use Customize examples to select `<XCSH_WORKDIR>`, certificate paths, namespace, and an exclusively owned certificate name. Paths are literal absolute paths outside Git; the form accepts paths, never key or bundle contents. Authenticate xcsh through its existing context before these commands; the form does not switch that context. Keep this working directory separate from Terraform state.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR">

```bash
umask 077
mkdir -p "$XCSH_WORKDIR"
chmod 700 "$XCSH_WORKDIR"
cd "$XCSH_WORKDIR"
```

</div>

## Public material

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

## Private-key encryption

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

## Certificate use

Native preparation independently validates the certificate/key pair and chain, retrieves public material, and encrypts the normalized key. Supply leaf-first `<XCSH_CERT_FILE>` and matching `<XCSH_KEY_FILE>`; choose an owned certificate name for `XCSH_CERT_NAME`. See [Input variants](./input-workflows/) for protected inputs.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE XCSH_CERT_NAME XCSH_CERT_FILE XCSH_KEY_FILE">

```bash
xcsh blindfold certificate --cert "$XCSH_CERT_FILE" --key "$XCSH_KEY_FILE" \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" --output-file certificate1.json \
  > certificate1-prepared.json 2> certificate1-prepared.err
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" --dry-run client -o json \
  > certificate1-preview.json 2> certificate1-preview.err
```

</div>

Expect `prepared` and a preview without a tenant write. Inspect `certificate1-preview.json`, then apply and reapply the identical saved manifest:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE">

```bash
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" -o json \
  > certificate1-apply.json 2> certificate1-apply.err
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" -o json \
  > certificate1-reapply.json 2> certificate1-reapply.err
```

</div>

Expect `created` for a missing name, `updated` for changed configuration, and `unchanged` on identical reapply. Retain the saved manifest: preparing it again produces new randomized ciphertext.

Supply renewed `<XCSH_RENEWED_CERT_FILE>` and matching `<XCSH_RENEWED_KEY_FILE>` with the same key algorithm for a referenced certificate. Prepare the replacement and inspect its preview:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE XCSH_CERT_NAME XCSH_RENEWED_CERT_FILE XCSH_RENEWED_KEY_FILE">

```bash
xcsh blindfold certificate --cert "$XCSH_RENEWED_CERT_FILE" --key "$XCSH_RENEWED_KEY_FILE" \
  --name "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" --output-file certificate2.json \
  > certificate2-prepared.json 2> certificate2-prepared.err
xcsh apply -f certificate2.json -n "$XCSH_NAMESPACE" --dry-run client -o json \
  > certificate2-preview.json 2> certificate2-preview.err
```

</div>

Apply the replacement to the same name:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE">

```bash
xcsh apply -f certificate2.json -n "$XCSH_NAMESPACE" -o json \
  > certificate2-apply.json 2> certificate2-apply.err
```

</div>

Expect `updated`; verify the served certificate at your endpoint after propagation.

## Proof

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

<div data-personalize="off">

## Retained showcase

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

Expect matching fingerprints and HTTP `200` with a JSON response. [Shared certificate evidence](../../assets/terraform-showcase-acceptance.json)
records the current shared-certificate rotation and endpoint checks; [historical xcsh acceptance](../../assets/xcsh-showcase-acceptance.json) retains
the earlier command measurements; [Command reference](./command-reference/) lists flags, limits, and recovery guidance.

</div>
