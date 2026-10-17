---
title: Wingman
description: Follow encrypted key preparation, sidecar injection, in-memory unsealing, and trusted HTTPS verification.
sidebar:
  label: Key unsealing
  order: 4
---

Your application can serve Hypertext Transfer Protocol Secure (HTTPS) without mounting a plaintext private key. Wingman authorizes the workload, unseals its encrypted key, and lets the application keep the decrypted material in memory. Try the [live example](https://certificate-management-terraform.f5-sales-demo.com/wingman/get), then follow the workflow in your own environment.

## Prerequisites

You need F5 Distributed Cloud tenant
access, a namespace with a Wingman-enabled virtual Kubernetes (vK8s) workload, an
application-specific Secret Policy, xcsh, kubectl, jq, and matching Transport Layer Security (TLS)
certificate/key files in private storage. Supply an explicit scoped kubeconfig and context. Use
**Customize examples** to set your namespace, Wingman naming base, hostname, application
image, and file paths; matching fields carry across the other certificate guides.

The [infrastructure runbook](./validation/) provisions this example's supporting policy, cluster, application, and disposable checks through Terraform plans. Complete it once if you need a working environment. Its ownership and teardown commands are operator support for this walkthrough. The steps below use that environment to demonstrate key preparation and application behavior.

Follow F5's [Wingman how-to](https://docs.cloud.f5.com/docs-v2/multi-cloud-network-connect/how-tos/secret-mgmt/pp-secrets-using-wingman) for the platform setup and its [API reference](https://docs.cloud.f5.com/docs-v2/platform/reference/wingman-api-reference) for protocol details.

## Configuration

Set `XCSH_APPLICATION_CERT_FILE` to the application leaf-first chain, `XCSH_CERT_FILE` to public endpoint trust, and `XCSH_ORIGIN_CA_FILE` to origin root trust. Use the governed latest image or an immutable digest.
Terraform resolves the selection to a verified immutable image during planning; inspect that digest before applying the saved plan. The runtime ConfigMap contains only the public chain and encrypted locations.
Terraform creates it before this Deployment; do not apply this JSON separately to a Terraform-owned resource.

<div data-xcsh-context="json" data-xcsh-fields="XCSH_DOMAINNAME XCSH_NAMESPACE XCSH_WINGMAN_NAME">

```json
{
  "apiVersion": "apps/v1",
  "kind": "Deployment",
  "metadata": {
    "name": "<XCSH_WINGMAN_NAME>-wingman",
    "namespace": "<XCSH_NAMESPACE>",
    "labels": {
      "app": "<XCSH_WINGMAN_NAME>-wingman"
    }
  },
  "spec": {
    "replicas": 1,
    "selector": {
      "matchLabels": {
        "app": "<XCSH_WINGMAN_NAME>-wingman"
      }
    },
    "template": {
      "metadata": {
        "labels": {
          "app": "<XCSH_WINGMAN_NAME>-wingman"
        },
        "annotations": {
          "ves.io/wingman-injection-mode": "enable",
          "certificate-management/material-sha256": "<MATERIAL_SHA256>"
        }
      },
      "spec": {
        "containers": [
          {
            "name": "application",
            "image": "ghcr.io/f5-sales-demo/certificate-management-wingman@sha256:<RESOLVED_IMAGE_DIGEST>",
            "imagePullPolicy": "Always",
            "ports": [
              {
                "name": "https",
                "containerPort": 8443
              }
            ],
            "env": [
              {
                "name": "TLS_HOSTNAME",
                "value": "<XCSH_DOMAINNAME>"
              }
            ],
            "resources": {
              "requests": {
                "cpu": "50m",
                "memory": "32Mi"
              },
              "limits": {
                "cpu": "250m",
                "memory": "128Mi"
              }
            },
            "securityContext": {
              "runAsNonRoot": true,
              "allowPrivilegeEscalation": false,
              "readOnlyRootFilesystem": true,
              "capabilities": {
                "drop": ["ALL"]
              }
            },
            "volumeMounts": [
              {
                "name": "material",
                "mountPath": "/material",
                "readOnly": true
              }
            ],
            "startupProbe": {
              "httpGet": {
                "path": "/readyz",
                "port": "https",
                "scheme": "HTTPS"
              },
              "periodSeconds": 5,
              "timeoutSeconds": 6,
              "failureThreshold": 30
            },
            "livenessProbe": {
              "tcpSocket": {
                "port": "https"
              },
              "periodSeconds": 10,
              "failureThreshold": 3
            },
            "readinessProbe": {
              "httpGet": {
                "path": "/readyz",
                "port": "https",
                "scheme": "HTTPS"
              },
              "periodSeconds": 5,
              "timeoutSeconds": 6
            }
          }
        ],
        "volumes": [
          {
            "name": "material",
            "configMap": {
              "name": "<XCSH_WINGMAN_NAME>-wingman-material"
            }
          }
        ]
      }
    }
  }
}
```

</div>

## Configure

### Prepare an encrypted key

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

Use the [cross-tool material update](./validation/#connect-the-existing-owner) to place that location in the runtime-owned ConfigMap. The application mounts the public certificate and encrypted locations at `/material`; the original key file stays outside the workload. Existing ciphertext encrypted under another policy cannot be substituted.

### Inspect sidecar injection

The runtime [Terraform configuration](../../_data/wingman/runtime/main.tf) owns the Deployment, ConfigMap, and Service. Its pod template requests injection and selects the label authorized by the Secret Policy. The complete resulting Kubernetes configuration appears under [Configuration](#configuration).

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

Use a matching application chain and trusted origin CA. Configure the public load-balancer certificate separately. The origin trust CA must be a signing CA; a `CA:FALSE` application leaf cannot serve as its root trust input.

## Verify

### Plan disposable qualification infrastructure

The qualification root owns three disposable Deployments: one for each authorized encrypted location
and one unselected workload that must receive HTTP 403. It reads the runtime ConfigMap without
owning it. Use Deployments because observed Job-generated pods disable injection. Save each run in
its own state directory. No plaintext key or credential payload enters its variables or state; the
provider reads an explicit private kubeconfig path.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_KUBECONFIG_FILE XCSH_KUBECONFIG_CONTEXT XCSH_NAMESPACE XCSH_WINGMAN_NAME XCSH_WINGMAN_IMAGE XCSH_DOMAINNAME">

```bash
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_WINGMAN_NAME"
export TF_VAR_kubeconfig_file="$XCSH_KUBECONFIG_FILE"
export TF_VAR_kubeconfig_context="$XCSH_KUBECONFIG_CONTEXT"
export TF_VAR_application_image="$XCSH_WINGMAN_IMAGE"
export TF_VAR_domain="$XCSH_DOMAINNAME"
export TF_VAR_run_id="wingman-q-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')"
probe_root="$XCSH_WORKDIR/wingman/$TF_VAR_run_id"
mkdir "$probe_root"
cp "$XCSH_WORKDIR/wingman/qualification/"*.tf "$probe_root/"
terraform -chdir="$probe_root" init -upgrade
terraform -chdir="$probe_root" validate
terraform -chdir="$probe_root" plan -out=probes.plan
terraform -chdir="$probe_root" show probes.plan
shasum -a 256 "$probe_root/probes.plan"
```

</div>

Review the saved plan: exactly three new probe Deployments, with the selected application label on
the first two and a different label on the denied probe. No Service, policy, certificate, or
retained Deployment changes belong in this plan. Keep the run ID and directory for interrupted
recovery; do not create another run to hide a failure. Hashes identify the reviewed private plan;
never publish its contents.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_KUBECONFIG_FILE XCSH_KUBECONFIG_CONTEXT XCSH_NAMESPACE XCSH_WINGMAN_NAME XCSH_WINGMAN_IMAGE XCSH_DOMAINNAME">

```bash
probe_root="$XCSH_WORKDIR/wingman/$TF_VAR_run_id"
terraform -chdir="$probe_root" apply probes.plan
terraform -chdir="$probe_root" output -json probe_inventory > "$probe_root/inventory.json"
terraform -chdir="$probe_root" plan -detailed-exitcode
fingerprint=$(terraform -chdir="$XCSH_WORKDIR/wingman/runtime" output -raw certificate_fingerprint)
python3 "$XCSH_WORKDIR/wingman/qualify.py" \
  --inventory "$probe_root/inventory.json" \
  --kubeconfig "$XCSH_KUBECONFIG_FILE" --context "$XCSH_KUBECONFIG_CONTEXT" \
  --namespace "$XCSH_NAMESPACE" --name "$XCSH_WINGMAN_NAME" \
  --image "$XCSH_WINGMAN_IMAGE" --domain "$XCSH_DOMAINNAME" \
  --fingerprint "$fingerprint" --private-directory "$probe_root/observations"
```

</div>

`qualify.py` observes the exact Deployment UIDs exported by Terraform and journals generated pod
UIDs. It never creates resources in this mode. Probe mode validates real `READY`, both platform
identity chains, and the application key pair, emitting only public fingerprints or denial status.
Startup has a ten-minute bound and running probes have a fixed three-minute bound. Completed current
or previous logs are read without re-running the probe; malformed nonempty output remains a failure.
A failed observation still requires cleanup through the qualification state.

### Destroy and verify disposable infrastructure

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

Run the [planned disposable checks](#plan-disposable-qualification-infrastructure)
against your actual sidecar. They require `READY`, trusted platform-issued client/server identity
chains, successful unseal of both provider- and xcsh-prepared locations, and HTTP 403 for an
unselected workload. These platform identities are separate from your application TLS certificate.
An expected negative result is `denied: true` with `http_status: 403`; an authorized result reports
your public `certificate_sha256`. A public endpoint response alone does not exercise fresh unseal or
denial.

Verify your public route using its configured trust certificate. For the retained demo, use the published [load-balancer trust certificate](../../assets/certificate-management.pem). Set `XCSH_CERT_FILE` to the certificate that validates your public endpoint, and `XCSH_APPLICATION_CERT_FILE` to your Wingman application leaf chain.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_DOMAINNAME XCSH_CERT_FILE XCSH_APPLICATION_CERT_FILE">

```bash
expected=$(openssl x509 -in "$XCSH_APPLICATION_CERT_FILE" -outform DER | openssl dgst -sha256 -r | cut -d ' ' -f 1)
curl --silent --show-error --fail --cacert "$XCSH_CERT_FILE" \
  "https://$XCSH_DOMAINNAME/wingman/get" \
  | jq -e --arg fingerprint "$expected" \
    '.example == "wingman-certificate" and .certificate_sha256 == $fingerprint'
```

</div>

Expect `true`. The response reports the application's certificate fingerprint, while public TLS uses the load balancer's certificate. Verify backend TLS separately using the application trust CA and the same hostname, as described in [operator qualification](./validation/#connect-the-existing-owner).

The [original delivery record](../../assets/wingman-acceptance.json) and [current CLI
follow-up](../../assets/wingman-xcsh-23.5.2-requalification.json) preserve their qualified versions.
The [walkthrough qualification record](../../assets/wingman-human-walkthrough-qualification.json)
covers these instructions, planned probes, copied examples, and shared form values. Builder
qualification remains in the [operator record](./validation/).

## Remove

Destroy your disposable qualification state through the [saved cleanup
plan](#destroy-and-verify-disposable-infrastructure), then verify Deployment, pod, and
ReplicaSet absence twice. Revoke and remove your scoped kubeconfig after all needed checks. If you
provisioned a reader environment, follow the [operator teardown
order](./validation/#remove) to remove its route and runtime before bootstrap.
Preserve the privately owned state and journals for recovery; never delete a retained demo or sweep
a namespace by prefix.
