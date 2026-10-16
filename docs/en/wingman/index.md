---
title: Wingman runtime
description: Authorize an application to unseal its TLS key through an injected Wingman sidecar.
sidebar:
  label: Wingman
  order: 4
---

Wingman lets the application unseal its TLS key inside a vK8s pod. The application serves an
identifiable HTTPS response and its public certificate fingerprint at `/wingman/get`. It mounts
only a public certificate and encrypted locations; the decrypted key stays in memory.

The retained [Wingman HTTPS endpoint](https://certificate-management-terraform.f5-sales-demo.com/wingman/get)
is qualified against the current published artifacts. Fresh probes unsealed Terraform- and
xcsh-prepared ciphertext, and an unselected pod received HTTP 403. A runtime restart produced fresh
trusted platform identities while preserving the application certificate and both existing endpoints.
The [delivery record](../../assets/wingman-acceptance.json) captures versions, digests, ownership,
empty plans, cleanup, credential revocation, and preserved first-run failures. A public health
response does not replace fresh unseal qualification.

The [builder 1.11.1 requalification record](../../assets/wingman-builder-1.11.1-requalification.json)
verifies the current documentation image. The earlier
[builder 1.11.0 record](../../assets/wingman-builder-requalification.json) remains available.
The [xcsh 23.5.2 follow-up record](../../assets/wingman-xcsh-23.5.2-requalification.json)
records the current CLI artifact, copied encryption command, fresh live unseal, HTTP 403 denial,
empty plans, and credential revocation. The application image, providers, certificates, shared key,
and resource ownership remain unchanged. Earlier records preserve their qualified versions.

Use F5's [Wingman how-to](https://docs.cloud.f5.com/docs-v2/multi-cloud-network-connect/how-tos/secret-mgmt/pp-secrets-using-wingman)
and [API reference](https://docs.cloud.f5.com/docs-v2/platform/reference/wingman-api-reference) for
concepts and protocol details. This page describes ownership, deployment order, and verification.

## Ownership and topology

[The naming contract](../../_data/wingman/contract.json) drives both Terraform roots and the
opt-in route. Bootstrap selects exactly one existing Toronto RE by the observed site label; verify
the selector and effective vK8s quota before applying. No new appliance or cloud infrastructure is
part of this demo. Application TLS material and platform-issued pod identities have separate roles.

| State or owner | Owned resources |
| --- | --- |
| Existing xcsh deployment | Existing certificate, load balancers, and origin pool |
| Existing Terraform deployment | Existing certificate and load balancers; optional Wingman pool and route |
| Bootstrap | Secret Policy, single-site virtual site, and vK8s |
| Runtime | Wingman certificate object, Deployment, Service, and encrypted-material ConfigMap |

The retained namespace and naming base are explicitly supplied as `certificate-management`. The reusable contract defaults to `demo-app` and assigns
`-wingman-policy`, `-wingman-sites`, and `-wingman` suffixes. Select an independent base for a
reader deployment. Keep both retained certificate/key files and their ciphertext unchanged. Wingman uses a separate
CA-signed application certificate with the original shared public key. Its private key remains the
existing matching key. Do not adopt existing objects into either new state.

Wingman also works with self-signed application certificates; the real runtime qualification passed
with the original certificate. The origin pool rejected that certificate as its root CA trust input
because it has `CA:FALSE`. The retained topology therefore uses a separate demo root CA and a
CA-signed Wingman leaf. The [public CA](../../assets/wingman-ca.pem) and
[Wingman certificate chain](../../assets/wingman-certificate.pem) contain no private keys. Reader
deployments must supply their own matching certificate chain and trust CA.

## Freeze sources and artifacts

Use a verified source checkout or [download the scaffold](https://github.com/f5-sales-demo/certificate-management/tree/main/wingman).
Preserve `wingman/contract.json` beside `bootstrap/` and `runtime/`. Keep state and session credentials
outside Git with directory mode 0700 and file mode 0600. Install Python 3, Terraform 1.11 or later,
kubectl, and jq. Bootstrap and runtime pin the qualified xcsh provider 15.9.0. Runtime pins Kubernetes provider 3.3.0.

Choose `<XCSH_WINGMAN_NAME>`, `<XCSH_WINGMAN_SITE_SELECTOR>`, `<XCSH_KUBECONFIG_FILE>`, and
`<XCSH_KUBECONFIG_CONTEXT>` independently. Unknown identities remain placeholders. Supply the
published image by digest as `<XCSH_WINGMAN_IMAGE>`; a floating image tag is rejected.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR">

```bash
umask 077
mkdir -p "$XCSH_WORKDIR/wingman/bootstrap" "$XCSH_WORKDIR/wingman/runtime"
for root in bootstrap runtime; do
  for file in main.tf versions.tf; do
    curl --silent --show-error --fail \
      "https://f5-sales-demo.github.io/certificate-management/_data/wingman/$root/$file" \
      --output "$XCSH_WORKDIR/wingman/$root/$file"
  done
done
curl --silent --show-error --fail \
  'https://f5-sales-demo.github.io/certificate-management/_data/wingman/runtime/variables.tf' \
  --output "$XCSH_WORKDIR/wingman/runtime/variables.tf"
for file in contract.json qualify.py kubeconfig.py; do
  curl --silent --show-error --fail \
    "https://f5-sales-demo.github.io/certificate-management/_data/wingman/$file" \
    --output "$XCSH_WORKDIR/wingman/$file"
done
curl --silent --show-error --fail \
  'https://f5-sales-demo.github.io/certificate-management/_data/scripts/resolve_current_artifacts.py' \
  --output "$XCSH_WORKDIR/wingman/resolve_current_artifacts.py"
python3 "$XCSH_WORKDIR/wingman/resolve_current_artifacts.py" --wingman \
  --output "$XCSH_WORKDIR/wingman/artifacts.json" \
  --install "$XCSH_WORKDIR/wingman/tools"
export PATH="$XCSH_WORKDIR/wingman/tools:$PATH"
export TF_CLI_CONFIG_FILE="$XCSH_WORKDIR/wingman/tools/frozen.tfrc"
```

</div>

Run artifact resolution from the verified source checkout. Freeze its commit alongside the provider,
Kubernetes provider, xcsh, Terraform, builder, and application image. Use the resulting private
provider installation configuration. Review the version pins and save provider lockfiles. Recheck
publications with `--check --wingman` before delivery; repeat affected qualification after any change.
Image CI triggers on application changes, while receipt updates preserve the same image identity.

## Bootstrap, then runtime

Provide `XCSH_API_URL` and `XCSH_API_TOKEN` in the process environment, as in the
[Terraform prerequisites](../terraform/#prerequisites). No CLI is required for Terraform encryption.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE XCSH_WINGMAN_NAME XCSH_WINGMAN_SITE_SELECTOR XCSH_WORKDIR">

```bash
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_WINGMAN_NAME"
export TF_VAR_site_selector="$XCSH_WINGMAN_SITE_SELECTOR"
terraform -chdir="$XCSH_WORKDIR/wingman/bootstrap" init
terraform -chdir="$XCSH_WORKDIR/wingman/bootstrap" validate
terraform -chdir="$XCSH_WORKDIR/wingman/bootstrap" plan -out=bootstrap.plan
terraform -chdir="$XCSH_WORKDIR/wingman/bootstrap" show bootstrap.plan
terraform -chdir="$XCSH_WORKDIR/wingman/bootstrap" apply bootstrap.plan
terraform -chdir="$XCSH_WORKDIR/wingman/bootstrap" plan -detailed-exitcode
vk8s=$(terraform -chdir="$XCSH_WORKDIR/wingman/bootstrap" output -raw vk8s_name)
python3 "$XCSH_WORKDIR/wingman/kubeconfig.py" issue \
  --namespace "$XCSH_NAMESPACE" --vk8s "$vk8s" \
  --private-directory "$XCSH_WORKDIR/wingman/session"
```

</div>

Require an empty follow-up plan. `kubeconfig.py` issues a one-day credential scoped to the new vK8s
and writes it only to the session directory. Select that file and an explicit context; verify the
context's namespace and cluster before runtime. Preserve the credential journal after ambiguous
issuance; do not reissue merely because a response failed.

The policy uses a selector-bound ALLOW followed by DENY-all, allows F5XC infrastructure decryption,
and requests a 30-second decrypt cache. The published CRUD schema does not expose an algorithm
write field; the provider verifies `algo: FIRST_MATCH` using the full policy readback. Qualify the runtime
allow and denial behavior before retaining the deployment.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_KUBECONFIG_FILE XCSH_KUBECONFIG_CONTEXT XCSH_WINGMAN_IMAGE XCSH_RENEWED_CERT_FILE XCSH_KEY_FILE XCSH_DOMAINNAME XCSH_WORKDIR">

```bash
export TF_VAR_kubeconfig_file="$XCSH_KUBECONFIG_FILE"
export TF_VAR_kubeconfig_context="$XCSH_KUBECONFIG_CONTEXT"
export TF_VAR_application_image="$XCSH_WINGMAN_IMAGE"
export TF_VAR_certificate_file="$XCSH_RENEWED_CERT_FILE"
export TF_VAR_private_key_file="$XCSH_KEY_FILE"
export TF_VAR_domain="$XCSH_DOMAINNAME"
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" init
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" validate
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" plan -out=runtime.plan
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" show runtime.plan
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" apply runtime.plan
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" plan -detailed-exitcode
```

</div>

Runtime prepares a separate Wingman-policy encrypted location. It never plans encryption before
bootstrap exists. The application requires the status body `READY`, calls `/secret/unseal`, decodes
the returned base64, verifies the key/certificate pair, and listens on TLS port 8443. The Service
publishes only 8443. Readiness requires Wingman's current status; API error bodies and key material
are never returned or logged.

## Qualify and connect the existing owner

Create a second encrypted location with the same Wingman policy using the frozen xcsh artifact.
This is an optional cross-tool qualification step, separate from the Terraform runtime dependency.
Set its private file path as `TF_VAR_xcsh_encrypted_location_file` and apply the runtime-owned ConfigMap
update. Existing ciphertext must stay unchanged.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_NAMESPACE XCSH_WINGMAN_NAME XCSH_KEY_FILE">

```bash
policy=$(terraform -chdir="$XCSH_WORKDIR/wingman/bootstrap" output -raw policy)
xcsh blindfold encrypt "$XCSH_KEY_FILE" \
  --policy "$policy" --encoding location \
  --output-file "$XCSH_WORKDIR/wingman/xcsh-location"
export TF_VAR_xcsh_encrypted_location_file="$XCSH_WORKDIR/wingman/xcsh-location"
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" plan -out=cross-tool.plan
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" show cross-tool.plan
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" apply cross-tool.plan
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" plan -detailed-exitcode
```

</div>

`qualify.py` creates three disposable Deployments whose generated pods use real injection: one for each authorized encrypted
location and one unselected pod that must receive HTTP 403. Probe mode validates both platform
identity chains and the application key pair, emitting only public fingerprints and denial status.
It allows up to ten minutes for pod startup, then gives each running probe a fixed three-minute
execution deadline. The application retains its two-minute startup limit and bounded API requests.
It collects completed current or previous container logs across a restart, preserves nonempty invalid
output as a failure, and never invokes another probe to recover logs. It journals exact Deployment
and pod UIDs before cleanup, deletes with UID preconditions, and verifies absence twice.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_KUBECONFIG_FILE XCSH_KUBECONFIG_CONTEXT XCSH_NAMESPACE XCSH_WINGMAN_NAME XCSH_WINGMAN_IMAGE XCSH_DOMAINNAME">

```bash
fingerprint=$(terraform -chdir="$XCSH_WORKDIR/wingman/runtime" output -raw certificate_fingerprint)
python3 "$XCSH_WORKDIR/wingman/qualify.py" \
  --kubeconfig "$XCSH_KUBECONFIG_FILE" --context "$XCSH_KUBECONFIG_CONTEXT" \
  --namespace "$XCSH_NAMESPACE" --name "$XCSH_WINGMAN_NAME" \
  --image "$XCSH_WINGMAN_IMAGE" --domain "$XCSH_DOMAINNAME" \
  --fingerprint "$fingerprint" --private-directory "$XCSH_WORKDIR/wingman/probes"
```

</div>

Next verify backend TLS through a private port-forward with the Wingman root CA and existing
hostname. Restart the runtime pod through its exact UID and repeat the probes; require fresh platform
identity hashes and unchanged application fingerprint. Keep each probe run's directory distinct.
Only then enable the route in the **existing Terraform owner state** using runtime's `owner_integration`
output and an explicit `wingman_contract_file` path. The opt-in `wingman` variable defaults to null.
The existing `/get` route, certificate addresses, HTTP redirect, and DNS owner remain in that state.

Use the existing private `deployment/` directory from the named-certificate guide. Review the full
plan: it must create one Wingman pool and add one HTTPS route, with no certificate or HTTP changes.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR XCSH_LB_NAME XCSH_NAMESPACE XCSH_DOMAINNAME XCSH_CERT_FILE XCSH_KEY_FILE XCSH_ORIGIN_CA_FILE">

```bash
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_LB_NAME"
export TF_VAR_domain="$XCSH_DOMAINNAME"
export TF_VAR_certificate_file="$XCSH_CERT_FILE"
export TF_VAR_private_key_file="$XCSH_KEY_FILE"
curl --silent --show-error --fail \
  "https://f5-sales-demo.github.io/certificate-management/_data/terraform/named-certificate/wingman.tf" \
  --output "$XCSH_WORKDIR/deployment/wingman.tf"
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" output -json owner_integration \
  > "$XCSH_WORKDIR/wingman/owner-integration.json"
jq -n --slurpfile wingman "$XCSH_WORKDIR/wingman/owner-integration.json" \
  --arg contract "$XCSH_WORKDIR/wingman/contract.json" \
  --arg ca "$XCSH_ORIGIN_CA_FILE" \
  '{wingman: ($wingman[0] + {trusted_ca_file: $ca}), wingman_contract_file: $contract}' \
  > "$XCSH_WORKDIR/deployment/wingman.auto.tfvars.json"
terraform -chdir="$XCSH_WORKDIR/deployment" plan -out=wingman.plan
terraform -chdir="$XCSH_WORKDIR/deployment" show wingman.plan
terraform -chdir="$XCSH_WORKDIR/deployment" apply wingman.plan
terraform -chdir="$XCSH_WORKDIR/deployment" plan -detailed-exitcode
```

</div>

The new pool uses vK8s service discovery, SNI for the existing hostname, and the Wingman root CA
as its trust input. Set `XCSH_RENEWED_CERT_FILE` to the Wingman leaf chain and
`XCSH_ORIGIN_CA_FILE` to its root CA; keep `XCSH_CERT_FILE` pointed at the original public load-balancer
certificate. Require backend TLS verification and the public Wingman marker. Its response fingerprint
must equal the backend Wingman leaf fingerprint; public TLS must retain the original certificate. Also verify
both original `/get` responses, both redirects, and empty plans in all three Terraform states.
Credential-free CI checks schemas and public health separately from fresh live unseal evidence.
Wingman is reported separately from the existing 25-node certificate matrix and its 16 qualified lifecycles.

## Rollback and recovery

The retained origin pool declares `PROTOCOL_TCP` explicitly. The first CA-trusted pool create
succeeded in F5, but Terraform reported an inconsistent result when the API supplied that default.
Recovery verified the created pool UID and spec, cleared only its Terraform taint, and applied a new
route-only plan. The pool was preserved. Keep the failed apply evidence; never replay its saved plan.

Set the existing owner's `wingman` input back to null, review the plan, and apply it to remove only
the Wingman route and pool. Verify both original endpoints and redirects. Then destroy runtime,
revoke its journaled kubeconfig, and remove bootstrap consumers in dependency order. Read policy
`marked_for_delete` and `deletion_time` as observed lifecycle facts; a pending tombstone is not absence.
Do not send a second DELETE to a marked policy or assume same-name recreation restores its old policy ID.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR">

```bash
python3 "$XCSH_WORKDIR/wingman/kubeconfig.py" revoke \
  --private-directory "$XCSH_WORKDIR/wingman/session"
```

</div>

Resume interrupted probe cleanup with `qualify.py --cleanup-only`, the same private directory,
explicit kubeconfig/context, and namespace. This mode verifies owned absence twice without creating
new probes.

Preserve private state, encrypted provenance, and cleanup journals after any failure. Verify exact
UIDs and the run label before recovering disposable probes; never use prefix sweeps or delete the
retained namespace. Public as-built receipts may contain versions, digests, status, and public
fingerprints. Keys, kubeconfig data, tokens, raw plans, and raw API responses stay private.
