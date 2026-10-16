---
title: Unseal an application TLS key with Wingman
description: Follow encrypted key preparation, sidecar injection, in-memory unsealing, and trusted HTTPS verification.
sidebar:
  label: Wingman
  order: 4
---

Your application can serve Hypertext Transfer Protocol Secure (HTTPS) without mounting a plaintext private key. Wingman authorizes the workload, unseals its encrypted key, and lets the application keep the decrypted material in memory. Try the [live example](https://certificate-management-terraform.f5-sales-demo.com/wingman/get), then follow the workflow in your own environment.

## Prerequisites

Allow about 15 minutes after preparing your environment. You need F5 Distributed Cloud tenant
access, a namespace with a Wingman-enabled virtual Kubernetes (vK8s) workload, an
application-specific Secret Policy, xcsh, kubectl, jq, and matching Transport Layer Security (TLS)
certificate/key files in private storage. Supply an explicit scoped kubeconfig and context. Use
**Customize examples** to set your namespace, Wingman naming base, hostname, immutable application
image, and file paths; matching fields carry across the other certificate guides.

The [validation infrastructure runbook](./validation/) provisions this example's supporting policy, cluster, application, and disposable checks through Terraform plans. Complete it once if you need a working environment. Its ownership and teardown commands are operator support for this walkthrough. The steps below use that environment to demonstrate key preparation and application behavior.

Follow F5's [Wingman how-to](https://docs.cloud.f5.com/docs-v2/multi-cloud-network-connect/how-tos/secret-mgmt/pp-secrets-using-wingman) for the platform setup and its [API reference](https://docs.cloud.f5.com/docs-v2/platform/reference/wingman-api-reference) for protocol details.

## Prepare an encrypted key

Choose the policy that permits your application label, followed by deny-all. The supporting [naming contract](../../_data/wingman/contract.json) uses the same base across this walkthrough and the other certificate examples. Encrypt your matching private key under that policy, writing only the encrypted location to a private file.

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

Use the [cross-tool material update](./validation/#qualify-and-connect-the-existing-owner) to place that location in the runtime-owned ConfigMap. The application mounts the public certificate and encrypted locations at `/material`; the original key file stays outside the workload. Existing ciphertext encrypted under another policy cannot be substituted.

## Enable Wingman for your application

The injected sidecar uses the workload label to request authorization. This JSON fragment shows the
pod-template fields of the example Deployment. It is a fragment to compare with your workload, not a
standalone manifest to apply. The [application source](../../_data/wingman/app/main.go) and [runtime
specification](../../_data/wingman/runtime/main.tf) contain the complete implementation and mount
configuration.

<div data-xcsh-context="json" data-xcsh-fields="XCSH_WINGMAN_NAME XCSH_WINGMAN_IMAGE XCSH_DOMAINNAME">

```json
{
  "metadata": {
    "labels": {"app": "<XCSH_WINGMAN_NAME>-wingman"},
    "annotations": {"ves.io/wingman-injection-mode": "enable"}
  },
  "spec": {
    "containers": [{
      "name": "application",
      "image": "<XCSH_WINGMAN_IMAGE>",
      "env": [{"name": "TLS_HOSTNAME", "value": "<XCSH_DOMAINNAME>"}],
      "volumeMounts": [{"name": "material", "mountPath": "/material", "readOnly": true}]
    }]
  }
}
```

</div>

Inspect the deployed template without changing it:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_KUBECONFIG_FILE XCSH_KUBECONFIG_CONTEXT XCSH_NAMESPACE XCSH_WINGMAN_NAME">

```bash
kubectl --kubeconfig "$XCSH_KUBECONFIG_FILE" --context "$XCSH_KUBECONFIG_CONTEXT" \
  --namespace "$XCSH_NAMESPACE" get deployment "$XCSH_WINGMAN_NAME-wingman" \
  -o json | jq '.spec.template.metadata | {labels, annotations}'
```

</div>

The actual pod must contain both `application` and an injected Wingman container. Annotation presence alone does not prove injection; the disposable checks below inspect real pods.

## Unseal inside the application

Wingman's loopback API listens on port 8070. The application first requests `/status` and requires the response body to be `READY`; HTTP 200 alone is insufficient. It sends the encrypted location to `/secret/unseal` as a Blindfold request, decodes the Base64 response in memory, and validates the certificate/key pair, hostname, and validity period before listening on TLS port 8443.

<div data-xcsh-context="json" data-xcsh-fields="">

```json
{"type":"blindfold","location":"<ENCRYPTED_LOCATION>"}
```

</div>

This request shape is explanatory. Use the application implementation instead of printing a raw unseal response in a terminal: the response contains private key material. The [probe source](../../_data/wingman/app/probe.go) exercises the same in-memory path and emits only public fingerprints or denial status. Keep port 8070 local to the pod; publish only the application's TLS service.

Exercise that safe probe inside the running application container:

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

Wingman can use a self-signed application certificate. Upstream verification also depends on the
origin pool's trust input: the retained original `CA:FALSE` self-signed leaf was rejected as a root
certificate authority (CA). This demo therefore uses a separate CA-signed Wingman leaf with the
unchanged shared key. The original load-balancer certificates and endpoints remain intact. Supply
your own matching application chain and trust CA in a reader deployment.

## Verify

Run the [planned disposable checks](./validation/#plan-disposable-qualification-infrastructure)
against your actual sidecar. They require `READY`, trusted platform-issued client/server identity
chains, successful unseal of both provider- and xcsh-prepared locations, and HTTP 403 for an
unselected workload. These platform identities are separate from your application TLS certificate.
An expected negative result is `denied: true` with `http_status: 403`; an authorized result reports
your public `certificate_sha256`. A public endpoint response alone does not exercise fresh unseal or
denial.

Verify your public route using its configured trust certificate. For the retained demo, use the published [load-balancer trust certificate](../../assets/certificate-management.pem). Set `XCSH_CERT_FILE` to the certificate that validates your public endpoint, and `XCSH_RENEWED_CERT_FILE` to your Wingman application leaf chain.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_DOMAINNAME XCSH_CERT_FILE XCSH_RENEWED_CERT_FILE">

```bash
expected=$(openssl x509 -in "$XCSH_RENEWED_CERT_FILE" -outform DER | openssl dgst -sha256 -r | cut -d ' ' -f 1)
curl --silent --show-error --fail --cacert "$XCSH_CERT_FILE" \
  "https://$XCSH_DOMAINNAME/wingman/get" \
  | jq -e --arg fingerprint "$expected" \
    '.example == "wingman-certificate" and .certificate_sha256 == $fingerprint'
```

</div>

Expect `true`. The response reports the application's certificate fingerprint, while public TLS uses the load balancer's certificate. Verify backend TLS separately using the application trust CA and the same hostname, as described in [operator qualification](./validation/#qualify-and-connect-the-existing-owner).

The [original delivery record](../../assets/wingman-acceptance.json) and [current CLI
follow-up](../../assets/wingman-xcsh-23.5.2-requalification.json) preserve their qualified versions.
The [walkthrough qualification record](../../assets/wingman-human-walkthrough-qualification.json)
covers these instructions, planned probes, copied examples, and shared form values. Builder
qualification remains in the [operator record](./validation/).

## Clean up

Destroy your disposable qualification state through the [saved cleanup
plan](./validation/#destroy-and-verify-disposable-infrastructure), then verify Deployment, pod, and
ReplicaSet absence twice. Revoke and remove your scoped kubeconfig after all needed checks. If you
provisioned a reader environment, follow the [operator teardown
order](./validation/#clean-up-and-recovery) to remove its route and runtime before bootstrap.
Preserve the privately owned state and journals for recovery; never delete a retained demo or sweep
a namespace by prefix.
