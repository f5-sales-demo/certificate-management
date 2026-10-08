---
title: Troubleshooting
description: Diagnose input and context errors, TLS deployment failures, and uncertain writes.
sidebar:
  label: Troubleshooting
  order: 7
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Use your private manifests and reports from the [administration tasks](../). Keep the intended context, namespace, named resource, and served fingerprint together while diagnosing a failure.

## Resolve input and context failures

| Symptom | Action |
| --- | --- |
| Context mismatch or denied policy | Confirm the saved context, exported credentials, explicit namespace, and permission for the shared policy. `--context-name` asserts; it does not select. |
| Malformed or mismatched public documents | Retrieve a fresh paired set from the same tenant. Use one JSON/YAML document and unambiguous supported fields. |
| Wrong password or mismatched certificate/key | Correct the passphrase variable or select a matching pair. Use native certificate preparation to check the chain before deployment. |
| Existing output destination | Choose a new path in an existing private directory. Do not redirect onto an earlier artifact you still need. |

## Diagnose deployment and TLS failures

| Symptom | Action |
| --- | --- |
| Unchanged reapply becomes updated | Reuse the identical saved manifest. New encryption produces new randomized ciphertext. |
| Referenced-certificate algorithm change rejected | Retain the working certificate; create a separate certificate for the new algorithm and change the reference after validation. |
| API success but HTTPS not ready | Inspect private load balancer state, certificate state, allocated VIP, and propagation. Confirm hostname/SNI and CA trust. Do not disable TLS verification. |

An upstream outage can fail `/get` while TLS verification still succeeds. Check the existing origin pool's reachability, verified TLS, SNI, and upstream Host separately from the client-facing certificate. For DNS failures, inspect client resolution and authoritative records; preserve the shared zone and unrelated records.

## Reconcile uncertain outcomes

Read the exact named resource after an uncertain write or cancellation. Compare its public chain and encrypted location privately, then verify the served fingerprint before deciding to retry. A matching readback can reconcile success; a failed or nonmatching read remains unresolved.

Combined Blindfold create/replace makes one mutation attempt and then a named read, including after an uncertain
response. It does not automatically retry a mutation. Keep submitted inputs and reports until the outcome is known.
Cancellation stops subsequent work, but a write already sent can have succeeded. A deployment failure, including later
artifact publication failure, does not prove the resource is absent.

Generic resource reports can contain complete manifests, diffs, resource data, and ciphertext; inspect them privately. Generic transport can retry network failures and HTTP 408, 429, or 503 responses; the one-mutation guarantee applies to combined Blindfold create/replace. When retiring resources, only a named `not_found` proves absence; an API or authentication failure does not.

## References

- [xcsh v23.0.1 immutable release](https://github.com/f5-sales-demo/xcsh/releases/tag/v23.0.1)
- [Native encryption and certificate input implementation](https://github.com/f5-sales-demo/xcsh/blob/aadca560d252a50077772ab057913ac9e2e961bd/crates/pi-natives/src/blindfold.rs)
- [Shared Blindfold service](https://github.com/f5-sales-demo/xcsh/blob/aadca560d252a50077772ab057913ac9e2e961bd/packages/coding-agent/src/services/blindfold.ts)
- [CLI parsing and supported flags](https://github.com/f5-sales-demo/xcsh/blob/aadca560d252a50077772ab057913ac9e2e961bd/packages/coding-agent/src/commands/blindfold-args.ts)
- [Assistant tool parameters and guards](https://github.com/f5-sales-demo/xcsh/blob/aadca560d252a50077772ab057913ac9e2e961bd/packages/coding-agent/src/tools/xcsh-blindfold.ts)
- [Microsoft Writing Style Guide](https://learn.microsoft.com/en-us/style-guide/welcome/), [step-by-step procedures](https://learn.microsoft.com/en-us/style-guide/procedures-instructions/writing-step-by-step-instructions), and [code examples](https://learn.microsoft.com/en-us/style-guide/developer-content/code-examples)
