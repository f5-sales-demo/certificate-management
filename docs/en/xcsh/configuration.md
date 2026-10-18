---
title: xcsh — Configuration
description: Configuration for the xcsh certificate workflow.
sidebar:
  label: Configuration
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../prerequisites/
  label: Prerequisites
next:
  link: ../configure/
  label: Configure
---

Supply a leaf-first public chain and matching private key. Native certificate preparation validates the pair and encrypts the normalized key. Use [Input variants](.././input-workflows/) for protected PEM, PKCS#12, and raw offline encryption.

## Public JSON

<div data-xcsh-context="json" data-xcsh-fields="XCSH_CERT_NAME XCSH_NAMESPACE">

```json
{"metadata":{"name":"<XCSH_CERT_NAME>","namespace":"<XCSH_NAMESPACE>"},"spec":{"certificate_url":"string:///<BASE64_PUBLIC_CHAIN>","private_key":{"blindfold_secret_info":{"location":"string:///<ENCRYPTED_KEY>"}}}}
```

</div>

This complete certificate configuration shows the resulting public fields. Preparation replaces the encoded-material placeholders; never apply placeholder ciphertext.

[Download public certificate JSON](../../../assets/configurations/xcsh-certificate.json).
