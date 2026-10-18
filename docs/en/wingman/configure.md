---
title: Wingman — Configure
description: Configure for the Wingman certificate workflow.
sidebar:
  label: Configure
  order: 3
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../configuration/
  label: Configuration
next:
  link: ../verify/
  label: Verify
---

## Configure steps

### Prepare an encrypted key

Choose the policy that permits your application label, followed by deny-all. The supporting [naming contract](../../../_data/wingman/contract.json) uses the same base across this walkthrough and the other certificate examples. Encrypt your matching private key under that policy, writing only the encrypted location to a private file.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_API_URL XCSH_API_TOKEN XCSH_WORKDIR XCSH_NAMESPACE XCSH_WINGMAN_NAME XCSH_KEY_FILE">

```bash
umask 077
policy=$(jq -r --arg namespace "$XCSH_NAMESPACE" --arg name "$XCSH_WINGMAN_NAME" \
  '$namespace + "/" + $name + .suffixes.policy' "$XCSH_WORKDIR/wingman/contract.json")
xcsh blindfold encrypt "$XCSH_KEY_FILE" \
  --policy "$policy" --encoding location \
  --output-file "$XCSH_WORKDIR/wingman/xcsh-location"
```

</div>

Use the [cross-tool material update](.././validation/#connect-the-existing-owner) to place that location in the runtime-owned ConfigMap. The application mounts the public certificate and encrypted locations at `/material`; the original key file stays outside the workload. Existing ciphertext encrypted under another policy cannot be substituted.

### Inspect sidecar injection

The runtime [Terraform configuration](../../../_data/wingman/runtime/main.tf) owns the Deployment, ConfigMap, and Service. Its pod template requests injection and selects the label authorized by the Secret Policy. The complete resulting Kubernetes configuration appears under [Configuration](../configuration/).

Inspect the deployed template without changing it:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_KUBECONFIG_FILE XCSH_KUBECONFIG_CONTEXT XCSH_NAMESPACE XCSH_WINGMAN_NAME">

```bash
kubectl --kubeconfig "$XCSH_KUBECONFIG_FILE" --context "$XCSH_KUBECONFIG_CONTEXT" \
  --namespace "$XCSH_NAMESPACE" get deployment "$XCSH_WINGMAN_NAME-wingman" \
  -o json | jq '.spec.template.metadata | {labels, annotations}'
```

</div>

The actual pod must contain both `application` and an injected Wingman container. Annotation presence alone does not prove injection; the disposable checks below inspect real pods.

### Unseal inside the application

Wingman's loopback API listens on port 8070. The application first requests `/status` and requires the response body to be `READY`; HTTP 200 alone is insufficient. It sends the encrypted location to `/secret/unseal` as a Blindfold request, decodes the base64 response in memory, and validates the certificate/key pair, hostname, and validity period before listening on TLS port 8443.

See the [Blindfold request shape](../configuration/#blindfold-request) before invoking the in-memory probe.

This request shape is explanatory. Keep the unseal response in application memory; do not print it in a terminal because it contains private key material. The [probe source](../../../_data/wingman/app/probe.go) uses the same in-memory path and emits only public fingerprints or denial status. Keep port 8070 local to the pod; publish only the application's TLS service.

Run the probe inside the running application container:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_KUBECONFIG_FILE XCSH_KUBECONFIG_CONTEXT XCSH_NAMESPACE XCSH_WINGMAN_NAME">

```bash
pod=$(kubectl --kubeconfig "$XCSH_KUBECONFIG_FILE" --context "$XCSH_KUBECONFIG_CONTEXT" \
  --namespace "$XCSH_NAMESPACE" get pods -l "app=$XCSH_WINGMAN_NAME-wingman" -o json \
  | jq -er '.items | map(select(.metadata.deletionTimestamp == null and .metadata.labels["qualification-run"] == null)) | if length == 1 then .[0].metadata.name else error("Expected one application pod") end')
kubectl --kubeconfig "$XCSH_KUBECONFIG_FILE" --context "$XCSH_KUBECONFIG_CONTEXT" \
  --namespace "$XCSH_NAMESPACE" exec "$pod" -c application -- /wingman-app probe-authorized
```

</div>

Expect an application certificate fingerprint and trusted client/server identity fingerprints. No private key appears in the output. Select exactly one retained application pod; a cardinality error requires inspection rather than choosing an arbitrary pod.

Use a matching application chain and trusted origin CA. Configure the public load-balancer certificate separately. The origin trust CA must be a signing CA; a `CA:FALSE` application leaf cannot serve as its root trust input.
