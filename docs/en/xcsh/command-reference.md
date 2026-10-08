---
title: Command reference
description: Blindfold operations, essential flags, encodings, limits, statuses, and recovery.
sidebar:
  label: Command reference
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Use `xcsh blindfold <operation> --help` or `xcsh request secrets <operation> --help` for full command help.

## Operations

| Command | Required input | Default result |
| --- | --- | --- |
| `blindfold public-key` | Authenticated tenant | snake_case JSON public-key document. |
| `blindfold policy` | Authenticated tenant | snake_case JSON policy; default `shared/ves-io-allow-volterra`. |
| `blindfold encrypt` | Raw file/stdin; authenticated tenant or paired public documents | `string:///` location; no tenant write. |
| `blindfold certificate` | Name, PEM chain/key or single-key PKCS#12 | Validated JSON manifest; no tenant write. |
| `blindfold create` | Certificate inputs and an absent owned name | One creation and named readback. |
| `blindfold replace` | Certificate inputs and an existing owned name | One replacement and named readback; preserves writable metadata and certificate options. |
| `request secrets get-public-key` | Authenticated tenant | camelCase YAML public-key document. |
| `request secrets get-policy-document` | Authenticated tenant and `--name` | camelCase YAML policy; namespace defaults to `default`. |
| `request secrets encrypt` | Raw file/stdin; authenticated tenant or paired public documents | Bare-base64 text; no tenant write. |

For the request-secrets TLS policy, specify `--namespace shared --name ves-io-allow-volterra`. Preview combined `create` or `replace` with `--dry-run client` before writing; for a referenced certificate, replacement requires the same key algorithm.

## Essential flags

| Flag | Use |
| --- | --- |
| `--context-name NAME` | Assert the current online context; does not switch it. Rejected offline. |
| `--policy NAMESPACE/NAME` | Policy for canonical retrieval/encryption or certificate operations; defaults to `shared/ves-io-allow-volterra`. Conflicts with explicit policy-retrieval `--namespace`/`--name`. |
| `--name NAME`, `-n NAMESPACE` | Certificate name/namespace, or policy retrieval target. Certificate namespace otherwise uses `XCSH_NAMESPACE`. |
| `--key-version UINT32` | Public-key retrieval: 0–4294967295; zero uses the server default, positive values require an exact returned version. |
| `--input FILE` | Raw encryption; alternative to one positional filename, `-`, or redirected stdin. |
| `--public-key FILE`, `--policy-document FILE` | Raw encryption only; required together for offline processing. |
| `--cert FILE`, `--key FILE`, `--bundle FILE` | Native certificate operations: PEM chain/key or PKCS#12, never both forms. |
| `--passphrase-env NAME` | Environment-variable name containing the protected-key or bundle password. |
| `--output json\|yaml`, `--outfmt json\|yaml` | Public-document format; `--outfmt` belongs to request-secrets and conflicts with `--output`. Neither selects ciphertext encoding. |
| `--encoding base64\|location` | Text encoding for raw encryption. |
| `--output-file FILE` | Save the artifact; stdout becomes a public JSON report. Conflicts with `--json`. |
| `--outfile FILE` | Request-secrets encryption: raw binary envelope; conflicts with explicit `--encoding`, `--output-file`, or `--json`. Default stdout is empty. |
| `--json` | Public report only; excludes artifact material and conflicts with `--output`/`--output-file`. Encryption without an artifact destination does not retain ciphertext. |
| `--result-file FILE` | Save a public JSON report separately from the artifact; also allowed with `--outfile`. |
| `--dry-run client` | Native certificate operations: validate without a tenant write; create/replace also inspect the target. |

Blindfold artifact/report files are atomic mode-0600 writes to new paths in an existing directory. Existing files and symlinks fail; choose fresh filenames. Generic resource reports may contain complete manifests, diffs, and ciphertext, so keep them private.

## Encodings and limits

A location contains one `string:///` prefix plus base64 encrypted bytes. Add that prefix to bare-base64 output, trimming the final newline, before using `spec.private_key.blindfold_secret_info.location`. Binary output contains the encrypted bytes directly. `spec.certificate_url` holds `string:///` plus base64 PEM encoding of the public chain. xcsh has no decryption operation.

| Input | Contract |
| --- | --- |
| Native certificate keys | RSA 2048–8192 bits; EC P-256 or P-384. |
| Certificate chain | PEM, leaf first, valid issuer names/signatures and validity dates; matching private key. |
| Protected inputs | Protected PEM or PKCS#12 with exactly one private key, handled by native certificate operations. |
| Public documents | One JSON/YAML document; known camelCase/snake_case fields and API `data` wrapper accepted. Conflicting aliases, duplicate keys, multiple documents, and mismatched tenants fail. |
| Raw input | Binary-safe file or redirected stdin; one positional input or `--input`, never both. Use `--` before dash-prefixed filenames. Interactive missing input fails. |
| File size | At most 2 MiB per native input file. |
| Encoded size | At most 131072 bytes each for the encrypted location and encoded certificate chain; no override. |

## Status and recovery

Blindfold reports exclude private keys and encrypted payloads. `prepared` confirms local preparation; combined create/replace returns `accepted` when named readback matches the submitted certificate and encrypted key. Its `readiness: unverified` requires endpoint verification. Generic `apply` returns `created`, `updated`, or `unchanged` as described in [Certificate use](../#certificate-use).

| Exit code | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | Operational failure: input validation, API failure, or unresolved write outcome. |
| `2` | Usage error: missing inputs or conflicting flags. |
| `130` | Ctrl+C cancellation. |

Read stderr, correct the input or authentication, and retry with fresh artifact paths. For uncertain create/replace outcomes, inspect the named resource before retrying: cancellation or a later failure does not undo an API write. A fingerprint mismatch requires checking the certificate reference and propagation before trusting the endpoint.
