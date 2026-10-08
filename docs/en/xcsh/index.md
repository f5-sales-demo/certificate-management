---
title: xcsh
description: Prepare validated certificate manifests, apply them, and verify HTTPS with xcsh.
sidebar:
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Use xcsh to administer Transport Layer Security (TLS) certificates in F5 Distributed Cloud. Start with an existing certificate and matching key. Blindfold encrypts private keys locally; it does not issue certificates or renew them automatically.

## Before you begin

Allow about 20 minutes for first deployment and verification, plus propagation time. Use Bash, Python 3, jq, cURL, OpenSSL, and the latest [xcsh](https://f5-sales-demo.github.io/xcsh/). On macOS, put Homebrew OpenSSL on `PATH`.

Use an [authenticated saved context](https://f5-sales-demo.github.io/xcsh/en/f5-distributed-cloud/contexts-namespaces/) for your authorized
tenant. You need an existing approved namespace, permission to retrieve the tenant public key and `shared/ves-io-allow-volterra` policy, and
outbound API access on port 443. Creation and rotation also require certificate and load balancer administration permissions.

Use one Bash session and an existing owner-only directory outside Git. Replace the placeholders with your configuration. Inspect existing resources before reconciling the example names.

```bash
set -euo pipefail
umask 077
export XCSH_WORKDIR='<PRIVATE_ARTIFACT_DIRECTORY>'
export XCSH_SAVED_CONTEXT='<SAVED_CONTEXT_NAME>'
export XCSH_NAMESPACE='<APPROVED_NAMESPACE>'
export XCSH_CERT_NAME='example-tls'
export XCSH_LB_NAME='example-https'
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

Blindfold artifact and report destinations must be new files in an existing private directory. Choose distinct output names on
retries or another host. Retain operational artifacts while administering resources; follow your team's retention
policy. Directory deletion does not guarantee secure erasure on flash storage or backups. When leaving the session,
clear `XCSH_API_TOKEN`, `XCSH_API_URL`, and passphrase variables from its environment.

## Administration tasks

Follow [Create certificates](./create-certificates/) to prepare `certificate1.json`, preview and apply it, then reference it from an HTTPS load balancer. Continue to [Verify and rotate](./verify-and-rotate/) to verify HTTPS, prepare `certificate2.json`, apply it, and verify again.

| Supporting task | Outcome |
| --- | --- |
| [Encrypt private keys](./encrypt-private-keys/) | Retrieve public material and encrypt raw bytes without deploying a certificate. |
| [Input workflows](./input-workflows/) | Prepare a manifest from protected PEM, PKCS#12, or redirected input. |
| [Assistant workflow](./assistant-workflow/) | Prepare an artifact through a file-path tool request. |
| [Command reference](./command-reference/) | Look up all nine operations, flags, encodings, limits, and reports. |
| [Troubleshooting](./troubleshooting/) | Recover from input, context, deployment, and uncertain-write failures. |

## Live proof

The retained showcase is [certificate-management.f5-sales-demo.com/get](https://certificate-management.f5-sales-demo.com/get). It uses a self-signed certificate that ordinary browsers do not trust, expiring October 5, 2036. Download the [public trust certificate](../../assets/certificate-management.pem) and check its file SHA-256 before using it as an explicit trust anchor:

`16ae68023040b4c7f99484bf0308aa8702575f88d62f90b74a1f620a0bd6c1a3`

[Current verification evidence](../../assets/xcsh-showcase-acceptance.json) records strict TLS and HTTPS checks for this endpoint and the revised procedures. Use your own hostname, trust anchors, and application path when following the guide.
