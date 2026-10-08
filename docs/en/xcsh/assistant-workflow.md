---
title: Assistant workflow
description: Prepare private artifacts through file-path requests with consistent context.
sidebar:
  label: Assistant workflow
  order: 5
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Use the [overview setup](../#before-you-begin), private input files, and the environment that launches xcsh. Allow about five minutes for preparation.

The `xcsh_blindfold` assistant tool uses the same native service. Ask it to use file paths; do not paste keys, credentials, passphrases, tenant documents, or encrypted payloads into chat. Preparation operations require an artifact destination, and tool results contain public reports rather than ciphertext.

## Request preparation by file path

For example, ask the assistant to execute this tool request, replacing the reserved file paths with your private files:

```json
{
  "operation": "certificate",
  "cert": "/private/example-certificate/chain1.pem",
  "key": "/private/example-certificate/protected-key.pem",
  "passphraseEnv": "TLS_INPUT_PASSWORD",
  "name": "example-tls",
  "namespace": "demo-app",
  "contextName": "certificate-admin",
  "outputFile": "/private/example-certificate/assistant-certificate.json",
  "resultFile": "/private/example-certificate/assistant-report.json"
}
```

After preparation, set `XCSH_CERT_MANIFEST` to the returned manifest path and follow [Preview and apply](../create-certificates/#preview-and-apply).

## Protect passphrases and artifacts

Set the passphrase variable in the environment that launches xcsh before starting the assistant. The tool receives only the variable name. A prepared report can include a public fingerprint, algorithm, expiry, target, and artifact paths. It omits the plaintext key, password, API token, and ciphertext. Target identity and paths can still be private.

## Keep context and operation consistent

Use the [shared command semantics](../command-reference/#operations-and-defaults) for `public-key`, `policy`, `encrypt`, `certificate`, `create`, and `replace`. For raw encryption, supply `input` and `outputFile` paths; the assistant does not accept stdin. Paired `publicKey` and `policyDocument` paths select [offline encryption](../encrypt-private-keys/#retrieve-tenant-public-material).

Other accepted parameters are `namespace`, `policy`, `passphraseEnv`, `contextName`, and `resultFile`. They map to their hyphenated CLI flags. The tool does not accept `keyVersion`, `encoding`, `outfile`, `outfmt`, raw inline material, or request-secrets operation names.

Session file-access controls apply to input and destination paths. A context, credential, or namespace change
stops the operation; retry only after confirming the intended context.

## Respect Plan Mode restrictions

Plan Mode blocks deployments and
artifact writes, including preparation with `outputFile` and reports with `resultFile`. Retrieval without an
artifact destination can return a public report in Plan Mode; it does not expose the document in the tool
result.

After authorized deployment, [verify HTTPS](../verify-and-rotate/).
