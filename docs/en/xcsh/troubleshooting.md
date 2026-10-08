---
title: Troubleshooting
description: Recover from input, context, deployment, and uncertain-write failures.
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
| Context mismatch or denied policy | Confirm the saved context, exported credentials, explicit namespace, and permission for the shared policy. See [context setup](../#before-you-begin). |
| Malformed or mismatched public documents | Retrieve a fresh paired set from the same tenant. Use one JSON/YAML document and unambiguous supported fields. |
| Wrong password or mismatched certificate/key | Correct the passphrase variable or select a matching pair. Use native certificate preparation to check the chain before deployment. |
| Existing output destination | Choose a new path in an existing private directory. Do not redirect onto an earlier artifact you still need. |

## Diagnose deployment and TLS failures

| Symptom | Action |
| --- | --- |
| Unchanged reapply becomes updated | Reuse the identical saved manifest. See [unchanged reapply](../create-certificates/#preview-and-apply). |
| Referenced-certificate algorithm change rejected | Retain the working certificate; create a separate certificate for the new algorithm and change the reference after validation. |
| API success but HTTPS not ready | Inspect private load balancer state, certificate state, allocated VIP, and propagation. Confirm hostname/SNI and CA trust. Do not disable TLS verification. |

An upstream outage can fail the configured application path while TLS verification still succeeds. Check the existing origin pool's reachability, verified TLS, SNI, and upstream Host separately from the client-facing certificate. For DNS failures, inspect client resolution and authoritative records; preserve the shared zone and unrelated records.

## Reconcile uncertain outcomes

Read the exact named resource after an uncertain write or cancellation. Compare its public chain and encrypted location privately, then verify the served fingerprint before deciding to retry. A matching readback can reconcile success; a failed or nonmatching read remains unresolved.

Combined Blindfold create/replace makes one mutation attempt and then a named read, including after an uncertain
response. It does not automatically retry a mutation. Keep submitted inputs and reports until the outcome is known.
See [report and cancellation behavior](../command-reference/#reports-exit-codes-and-cancellation). Inspect resource reports within the [private storage boundary](../#before-you-begin).

Generic transport can retry network failures and HTTP 408, 429, or 503 responses; the one-mutation guarantee applies to combined Blindfold create/replace. When retiring resources, only a named `not_found` proves absence; an API or authentication failure does not.
