---
title: Command reference
description: Look up operations, flags, encodings, input limits, reports, and exit codes.
sidebar:
  label: Command reference
  order: 6
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Use `xcsh blindfold <operation> --help` or `xcsh request secrets <operation> --help` for operation-specific flags.

## Operations and defaults

| Command | Input | Default result |
| --- | --- | --- |
| `blindfold public-key` | Online tenant context; optional `--key-version` | snake_case JSON public-key document. |
| `blindfold policy` | Online context; `--policy` or `--namespace` with `--name` | snake_case JSON policy document; default `shared/ves-io-allow-volterra`. |
| `blindfold encrypt` | File or redirected stdin; online context or paired offline documents | Textual `string:///` location; no resource write. |
| `blindfold certificate` | `--name` and `--cert` with `--key`, or `--bundle` | Validated JSON certificate manifest; no resource write. |
| `blindfold create` | Certificate inputs and an absent resource name | Named create and readback; public report. |
| `blindfold replace` | Certificate inputs and an existing resource name | Named replacement and readback; public report. |
| `request secrets get-public-key` | Online context; optional `--key-version` | camelCase YAML public-key document. |
| `request secrets get-policy-document` | Online context; required `--name`, optional `--namespace` | camelCase YAML policy document; namespace defaults to `default`. Use explicit `shared` for the platform TLS policy. |
| `request secrets encrypt` | Same raw input choices as canonical encryption | Bare-base64 text; no resource write. |

These defaults describe output without an artifact flag. With `--output-file`, the artifact stays on disk and stdout becomes a public JSON report. Redirect even public reports if target identity or paths are sensitive.

### Create or replace in one command

Use `create` for an absent owned name or `replace` for an existing owned name when you do not need a saved manifest. These commands validate inputs, encrypt, attempt one mutation, and read the named certificate back. First preview with the same inputs and `--dry-run client`:

```bash
xcsh blindfold create --context-name certificate-admin \
  --cert chain1.pem --key server1-key.pem --name "$XCSH_CERT_NAME" \
  -n "$XCSH_NAMESPACE" --dry-run client --json \
  > combined-preview.json 2> combined-preview.err
```

Inspect `combined-preview.json` privately before creation:

```bash
xcsh blindfold create --context-name certificate-admin \
  --cert chain1.pem --key server1-key.pem --name "$XCSH_CERT_NAME" \
  -n "$XCSH_NAMESPACE" --json > combined-created.json 2> combined-created.err
```

For replacement, retain the [same-algorithm constraint](../verify-and-rotate/#rotate-with-renewed-inputs) and use renewed inputs:

```bash
xcsh blindfold replace --context-name certificate-admin \
  --cert chain2.pem --key server2-key.pem --name "$XCSH_CERT_NAME" \
  -n "$XCSH_NAMESPACE" --dry-run client --json \
  > combined-replace-preview.json 2> combined-replace-preview.err
```

Inspect `combined-replace-preview.json` privately before replacement:

```bash
xcsh blindfold replace --context-name certificate-admin \
  --cert chain2.pem --key server2-key.pem --name "$XCSH_CERT_NAME" \
  -n "$XCSH_NAMESPACE" --json > combined-replaced.json 2> combined-replaced.err
```

Replacement preserves writable metadata and certificate options from the existing replace form. After either command, [verify HTTPS](../verify-and-rotate/). For ambiguous results, [reconcile the named resource](../troubleshooting/#reconcile-uncertain-outcomes) before retrying.

### Use request-secrets commands

Retrieval defaults to camelCase YAML, and raw encryption defaults to bare base64. These commands use the same native context and encryption service:

```bash
xcsh request secrets get-public-key --context-name certificate-admin \
  --outfmt yaml --output-file public-key.yaml > request-key-report.json 2> request-key.err
xcsh request secrets get-policy-document --context-name certificate-admin \
  --namespace shared --name ves-io-allow-volterra --outfmt json \
  --output-file request-policy.json > request-policy-report.json 2> request-policy.err
xcsh request secrets encrypt --public-key public-key.yaml \
  --policy-document request-policy.json server1-key.pem \
  --encoding location --output-file request.location > request-report.json 2> request.err
```

For binary output, replace `--encoding location --output-file request.location` with `--outfile key.envelope` and choose new report filenames.

## Flags and output restrictions

| Flag | Applies to | Meaning and restrictions |
| --- | --- | --- |
| `--context-name NAME` | Online operations | Assert the current context; does not activate another context. Rejected for offline encryption. |
| `--output json\|yaml` | Public-material retrieval | Select document format; does not select ciphertext encoding. |
| `--outfmt json\|yaml` | Request-secrets commands | Select retrieval format. Accepted by request-secrets encryption without changing its encoding. Conflicts with `--output`. |
| `--key-version UINT32` | Both public-key retrieval commands | Values 0–4294967295. Zero selects the server default; a positive request must return that exact version without fallback. |
| `--policy NAMESPACE/NAME` | Canonical policy, raw encryption, certificate operations | Default `shared/ves-io-allow-volterra`. On canonical policy retrieval, conflicts with explicit `--namespace` or `--name`. |
| `-n`, `--namespace` | Policy retrieval or certificate operations | Select policy namespace or certificate namespace. Certificate namespace otherwise defaults to `XCSH_NAMESPACE`. |
| `--input FILE` | Raw encryption | Alternative to one positional filename or redirected stdin. |
| `--public-key FILE`, `--policy-document FILE` | Raw encryption | Must occur together; only supported by `encrypt`; select offline processing. |
| `--cert FILE`, `--key FILE`, `--bundle FILE` | Certificate preparation/create/replace | Choose separate PEM chain/key or a single-key PKCS#12 bundle. |
| `--passphrase-env NAME` | Certificate preparation/create/replace | Name of the environment variable containing the input-key or bundle passphrase. |
| `--encoding base64\|location` | Both raw encryption commands | Explicit text encoding; canonical default is `location`, request-secrets default is `base64`. |
| `--output-file FILE` | All operations | Store selected text/document/manifest atomically in a new mode-0600 file. Conflicts with `--json`. |
| `--outfile FILE` | Request-secrets raw encryption only | Store raw binary envelope atomically in a new mode-0600 file. Conflicts with explicit `--encoding`, `--output-file`, and `--json`. |
| `--json` | All operations | Print the public report without artifact material. Conflicts with `--output` and `--output-file`; encryption with only `--json` does not retain ciphertext. |
| `--result-file FILE` | All operations | Store a public JSON report in a new mode-0600 file. It must differ from the artifact path; allowed with binary `--outfile`. |
| `--dry-run client` | Certificate preparation/create/replace | Validate without a tenant write. Create/replace also inspect the target. Local artifact writes are still possible outside Plan Mode. |

All Blindfold artifact and report destinations must be new files in an existing writable directory. Existing
files and symlinks are rejected; there is no overwrite flag or output-directory routing. Use distinct
filenames on retries. Generic resource `--result-file` reports have a different implementation and can contain
complete manifests, diffs, resource data, and ciphertext; [common setup](../#before-you-begin) establishes private storage for those reports.

To select an explicit available key version from the retrieved document:

```bash
XCSH_KEY_VERSION="$(jq -er '.data.key_version' tenant-public-key.json)"
xcsh blindfold public-key --context-name certificate-admin \
  --key-version "$XCSH_KEY_VERSION" --output yaml --output-file versioned-public-key.yaml \
  > versioned-report.json 2> versioned.err
xcsh request secrets get-public-key --context-name certificate-admin \
  --key-version "$XCSH_KEY_VERSION" --outfmt json --output-file versioned-request-key.json \
  > versioned-request-report.json 2> versioned-request.err
unset XCSH_KEY_VERSION
```

## Supported inputs and limits

Raw encryption accepts one positional filename, `--input FILE`, `-` for redirected stdin, or redirected stdin with no filename. Do not combine positional input with `--input`; use `--` before a filename beginning with a dash. Missing interactive input fails immediately. Native certificate operations require file paths and retrieve public material online.

A textual location contains exactly one `string:///` prefix followed by base64 encrypted bytes. Bare-base64 text needs that prefix when used
as `spec.private_key.blindfold_secret_info.location`; trim its final newline first. Binary `--outfile` stores encrypted bytes directly and
leaves default stdout empty. The public chain field, `spec.certificate_url`, contains `string:///` plus base64 PEM; that field is encoding,
not encryption. xcsh exposes no decryption operation.

| Input | Contract |
| --- | --- |
| Certificate keys | Rivest-Shamir-Adleman (RSA) 2048–8192 bits; elliptic curve (EC) P-256 or P-384. Unsupported types and curves fail. |
| Certificate chain | PEM, leaf first, followed by issuers with matching names and valid signatures. Every supplied certificate must be currently valid. The leaf key must match the private key. |
| Protected input | Password-protected PEM and single-private-key PKCS#12, handled by native certificate operations. |
| Public documents | One JSON or YAML document with the required public fields; known camelCase and snake_case spellings accepted, including the API `data` wrapper. Agreeing aliases accepted; conflicting aliases, duplicate keys, multiple documents, malformed fields, or mismatched tenants rejected. |
| Raw secret | Binary-safe bounded native file or redirected stdin reads. Raw encryption does not interpret certificate content. |
| File input | At most 2 MiB per native input file; encoded limits below usually impose a smaller usable secret size. |
| Encoded output | Maximum 131072 bytes for the encrypted location and separately for the encoded certificate chain. There is no CLI size-limit override. |

## Reports, exit codes, and cancellation

Blindfold public reports contain status, operation, target, artifact paths, and applicable public certificate
metadata. They exclude encrypted payloads and private keys. `prepared` means local preparation succeeded.
`accepted` from combined create/replace means named readback matched both the submitted certificate and
encrypted key; `readiness` remains `unverified` until you check the serving load balancer.

| Exit code | Meaning |
| --- | --- |
| `0` | Operation completed successfully. |
| `1` | Operational failure, including invalid cryptographic material, API failure, or unresolved write outcome. |
| `2` | CLI usage error, such as conflicting output flags or missing paired documents. |
| `130` | Ctrl+C cancellation. |

Diagnostics go to standard error (stderr). Cancellation stops subsequent work, but a write already sent to the API can have succeeded. A failure after deployment, including artifact publication failure, does not prove the resource is absent.

Use the [overview](../#before-you-begin) for shared setup and [Troubleshooting](../troubleshooting/) to interpret failures.
