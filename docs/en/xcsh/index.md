---
title: xcsh
description: Encrypt private keys, administer certificates, and verify HTTPS with xcsh.
sidebar:
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Use xcsh to encrypt Transport Layer Security (TLS) private keys locally and administer certificates in F5 Distributed Cloud. Start with an existing certificate and matching key. Blindfold prepares encrypted inputs; it does not issue certificates or renew them automatically.

## Before you begin

Allow about 20 minutes for first deployment and verification, plus propagation time. You need Bash, Python 3, jq, cURL, OpenSSL 3, and [immutable xcsh v23.0.1](https://github.com/f5-sales-demo/xcsh/releases/tag/v23.0.1). On macOS, put Homebrew OpenSSL on `PATH`. These examples require the certificate comparison fix in v23.0.1.

Use an authenticated saved global context for your authorized tenant; follow [context
setup](https://f5-sales-demo.github.io/xcsh/en/f5-distributed-cloud/contexts-namespaces/). You need an existing approved
namespace and permission to retrieve the tenant public key and `shared/ves-io-allow-volterra` policy, and administer
certificates and HTTPS load balancers. You also need an existing origin pool, an owned hostname, and outbound API and
endpoint access on port 443.

Prepare these files in an existing owner-only directory outside Git:

| File | Input you supply |
| --- | --- |
| `chain1.pem`, `server1-key.pem` | Current PEM certificate chain, leaf first, and matching unprotected key. |
| `chain2.pem`, `server2-key.pem` | Existing renewed certificate chain and matching replacement key, when rotating. |
| `trust1.pem`, `trust2.pem` | Approved trust anchors for the current and replacement certificate. For a self-signed certificate, use that public certificate itself. |
| `protected-key.pem` or `server.p12` | Optional protected PEM key or single-key PKCS#12 bundle for [input workflows](./input-workflows/). |

Use the same Bash session and directory across tasks. Replace the placeholders with your own configuration. Resource names below illustrate project-owned names; inspect any existing resource before reconciling it.

```bash
set -euo pipefail
umask 077
export XCSH_WORKDIR='<PRIVATE_ARTIFACT_DIRECTORY>'
export XCSH_SAVED_CONTEXT='<SAVED_CONTEXT_NAME>'
export XCSH_NAMESPACE='<APPROVED_NAMESPACE>'
export XCSH_CERT_NAME='example-tls'
export XCSH_LB_NAME='example-https'
export XCSH_ORIGIN_POOL_NAME='<EXISTING_ORIGIN_POOL_NAME>'
export XCSH_ORIGIN_NAMESPACE="$XCSH_NAMESPACE"
export XCSH_DOMAINNAME='app.example.com'
export XCSH_UPSTREAM_HOST='origin.example.com'
cd "$XCSH_WORKDIR"
chmod 700 "$XCSH_WORKDIR"
```

Link the saved context into this directory. Clear inherited API overrides, then export a private credential snapshot so generic resource commands and Blindfold use the same target.

```bash
unset XCSH_API_URL XCSH_API_TOKEN XCSH_CONTEXT_NAME
xcsh context link certificate-admin "$XCSH_SAVED_CONTEXT" \
  --source local --json > context-link.json 2> context-link.err
xcsh context export "$XCSH_SAVED_CONTEXT" --include-token \
  > context-private.json 2> context-export.err
jq -e '.contexts | length == 1' context-private.json > /dev/null
export XCSH_API_URL="$(jq -er '.contexts[0].apiUrl' context-private.json)"
export XCSH_API_TOKEN="$(jq -er '.contexts[0].apiToken' context-private.json)"
export XCSH_CONTEXT_NAME=certificate-admin
```

The snapshot contains credentials. Keep the environment, keys, manifests, ciphertext, tenant documents, and raw reports private; do not enable shell tracing. `--context-name certificate-admin` asserts the linked context; it does not switch contexts. Generic resource commands use the exported API credentials and explicit namespace.

Artifact and report destinations must be new files in an existing private directory. Choose distinct output names on
retries or another host. Retain operational artifacts while administering resources; follow your team's retention
policy. Directory deletion does not guarantee secure erasure on flash storage or backups. When leaving the session,
clear `XCSH_API_TOKEN`, `XCSH_API_URL`, and passphrase variables from its environment.

## Administration tasks

| Task | Outcome |
| --- | --- |
| [Encrypt private keys](./encrypt-private-keys/) | Retrieve paired public material and retain an encrypted location. |
| [Create certificates](./create-certificates/) | Prepare or construct a manifest, apply it, and reference it from an HTTPS load balancer. |
| [Verify and rotate](./verify-and-rotate/) | Check the served certificate, replace it with renewed inputs, and optionally retire owned resources. |
| [Input workflows](./input-workflows/) | Use protected PEM, PKCS#12, stdin, offline processing, or request-secrets commands. |
| [Assistant workflow](./assistant-workflow/) | Prepare private artifacts through file-path tool requests. |
| [Command reference](./command-reference/) | Find all nine operations, flags, input contracts, envelope details, and reports. |
| [Troubleshooting](./troubleshooting/) | Reconcile input, context, deployment, and uncertain-write failures. |

Earlier article links remain available here:

- <span id="prerequisites"></span>[Prerequisites](#before-you-begin).
- <span id="walkthrough"></span>[Walkthrough](./create-certificates/#validate-apply-and-reapply).
- <span id="prepare-a-private-working-directory"></span>[Prepare a private working directory](#before-you-begin).
- <span id="generate-a-lab-certificate"></span>[Generate a lab certificate](#before-you-begin).
- <span id="retrieve-public-material-and-encrypt-the-key"></span>[Retrieve public material and encrypt the key](./encrypt-private-keys/#retrieve-tenant-public-material).
- <span id="construct-and-apply-the-certificate-manifest"></span>[Construct and apply the certificate manifest](./create-certificates/#construct-structured-json).
- <span id="deploy-an-https-load-balancer"></span>[Deploy an HTTPS load balancer](./create-certificates/#reference-an-existing-origin-pool).
- <span id="rotate-the-certificate"></span>[Rotate the certificate](./verify-and-rotate/#rotate-with-renewed-inputs).
- <span id="clean-up-the-lab"></span>[Clean up the lab](./verify-and-rotate/#retire-owned-resources-optionally).
- <span id="input-variants"></span>[Input variants](./input-workflows/#use-a-protected-pem-key).
- <span id="prepare-a-manifest-with-native-certificate-validation"></span>[Prepare a manifest with native certificate validation](./create-certificates/#prepare-a-validated-certificate).
- <span id="use-a-protected-pem-key"></span>[Use a protected PEM key](./input-workflows/#use-a-protected-pem-key).
- <span id="use-a-single-key-pkcs12-bundle"></span>[Use a single-key PKCS#12 bundle](./input-workflows/#use-a-single-key-pkcs12-bundle).
- <span id="encrypt-redirected-stdin-or-paired-offline-documents"></span>[Encrypt redirected stdin or paired offline documents](./input-workflows/#encrypt-stdin-or-offline-inputs).
- <span id="use-the-request-secrets-command-surface"></span>[Use the request-secrets command surface](./input-workflows/#use-request-secrets-equivalents).
- <span id="create-or-replace-with-combined-commands"></span>[Create or replace with combined commands](./create-certificates/#combined-creation).
- <span id="assistant-workflow"></span>[Assistant workflow](./assistant-workflow/#request-preparation-by-file-path).
- <span id="command-reference"></span>[Command reference](./command-reference/#operations-and-defaults).
- <span id="operations-and-defaults"></span>[Operations and defaults](./command-reference/#operations-and-defaults).
- <span id="flags-and-output-restrictions"></span>[Flags and output restrictions](./command-reference/#flags-and-output-restrictions).
- <span id="supported-inputs-and-limits"></span>[Supported inputs and limits](./command-reference/#supported-inputs-and-limits).
- <span id="native-encryption-envelope"></span>[Native encryption envelope](./command-reference/#native-encryption-envelope).
- <span id="reports-exit-codes-and-cancellation"></span>[Reports, exit codes, and cancellation](./command-reference/#reports-exit-codes-and-cancellation).
- <span id="troubleshooting"></span>[Troubleshooting](./troubleshooting/#resolve-input-and-context-failures).
- <span id="references"></span>[References](./troubleshooting/#references).

## Live proof

The owner retains an HTTPS showcase at
[certificate-management.f5-sales-demo.com/get](https://certificate-management.f5-sales-demo.com/get). It references a
DNS origin pool for HTTPBin over verified upstream TLS, with matching Server Name Indication (SNI) and Host header. A
project-owned HTTP companion redirects to HTTPS and maintains the F5-managed DNS record in the existing shared zone.
HTTPBin is an external dependency; an upstream outage can fail the HTTP check while certificate checks still pass.

The showcase uses an intentionally self-signed RSA-2048 server certificate valid for 3650 days. Ordinary browsers do not
trust it. Download the [public verification certificate](../../assets/certificate-management.pem) and verify its file
SHA-256 against the [sanitized receipt](../../assets/xcsh-showcase-acceptance.json) before using it as an explicit trust
anchor. The receipt records both deployment fingerprints, expiry, command results, retained ownership, and the
source-page hashes. It is a measured result for this endpoint, not configuration for your environment.

Public certificate file SHA-256: `16ae68023040b4c7f99484bf0308aa8702575f88d62f90b74a1f620a0bd6c1a3`.

[Strict TLS verification](./verify-and-rotate/#verify-strict-tls) checks hostname, explicit trust, served SHA-256
fingerprint, and HTTPS response. No public certificate authority enrollment or scheduled renewal is configured. The
final rotated certificate and endpoint remain deployed; [resource
retirement](./verify-and-rotate/#retire-owned-resources-optionally) is optional administration. [Earlier
acceptance](../../assets/xcsh-certificate-acceptance.json) remains historical evidence for the former temporary lab.
