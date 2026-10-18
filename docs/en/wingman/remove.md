---
title: Wingman — Remove
description: Remove for the Wingman certificate workflow.
sidebar:
  label: Remove
  order: 6
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../maintain/
  label: Maintain
next:
  link: ../
  label: Overview
---

## Remove steps
## Destroy and verify disposable infrastructure

Resume the exact `TF_VAR_run_id`, private state directory, inventory, and observation journal created in Verify. Keep the shell environment from that run; never generate a new run ID for removal.

Check exact live ownership before planning and again before applying destruction. Stop if any UID changes; inspect the private state and journal rather than deleting a replacement. Do not run concurrent writers against these disposable names.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_KUBECONFIG_FILE XCSH_KUBECONFIG_CONTEXT XCSH_NAMESPACE">

```bash
probe_root="$XCSH_WORKDIR/wingman/$TF_VAR_run_id"
python3 "$XCSH_WORKDIR/wingman/qualify.py" --verify-owned \
  --inventory "$probe_root/inventory.json" --private-directory "$probe_root/observations" \
  --kubeconfig "$XCSH_KUBECONFIG_FILE" --context "$XCSH_KUBECONFIG_CONTEXT" \
  --namespace "$XCSH_NAMESPACE"
terraform -chdir="$probe_root" plan -destroy -out=cleanup.plan
terraform -chdir="$probe_root" show cleanup.plan
shasum -a 256 "$probe_root/cleanup.plan"
python3 "$XCSH_WORKDIR/wingman/qualify.py" --verify-owned \
  --inventory "$probe_root/inventory.json" --private-directory "$probe_root/observations" \
  --kubeconfig "$XCSH_KUBECONFIG_FILE" --context "$XCSH_KUBECONFIG_CONTEXT" \
  --namespace "$XCSH_NAMESPACE"
terraform -chdir="$probe_root" apply cleanup.plan
python3 "$XCSH_WORKDIR/wingman/qualify.py" --verify-cleanup \
  --inventory "$probe_root/inventory.json" --private-directory "$probe_root/observations" \
  --kubeconfig "$XCSH_KUBECONFIG_FILE" --context "$XCSH_KUBECONFIG_CONTEXT" \
  --namespace "$XCSH_NAMESPACE"
```

</div>

Require successful Kubernetes reads showing no named Deployments and no run-labelled pods or ReplicaSets twice. Permission or transport errors do not count as absence. The empty create-state follow-up plan is checked before destroy; after destroy the state must contain no resources. Keep failed plan/apply evidence and reconcile state before making a fresh recovery plan.

Destroy your disposable qualification state through the [saved cleanup
plan](#destroy-and-verify-disposable-infrastructure), then verify Deployment, pod, and
ReplicaSet absence twice. Revoke and remove your scoped kubeconfig after all needed checks. If you
provisioned a reader environment, follow the [operator teardown
order](.././validation/#remove) to remove its route and runtime before bootstrap.
Preserve the privately owned state and journals for recovery; never delete a retained deployment or sweep
a namespace by prefix.
