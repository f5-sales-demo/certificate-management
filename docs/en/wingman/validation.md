---
title: Infrastructure
description: Authorize an application to unseal its TLS key through an injected Wingman sidecar.
sidebar:
  label: Infrastructure
  order: 2
---

Provision the policy, virtual site, vK8s, application, and TLS service with separate Terraform states. Complete [Key unsealing](../) to verify application behavior. Keep historical artifact observations in the [qualification records](../../../assets/wingman-acceptance.json).

## Prerequisites

Install Python 3, the latest Terraform release, kubectl, and jq. You need tenant API access, an existing namespace, and a verified regional-edge site selector with sufficient vK8s quota. Keep matching application certificate and key files in private storage. Set the [provider environment](../../terraform/#prerequisites) before planning.

## Configuration

[The naming contract](../../../_data/wingman/contract.json) drives bootstrap and runtime Terraform roots and the
opt-in route. Bootstrap selects exactly one existing Toronto RE by the observed site label; verify
the selector and effective vK8s quota before applying. Bootstrap creates no appliance or cloud infrastructure. Application TLS material and platform-issued pod identities have separate roles.

| State or owner | Owned resources |
| --- | --- |
| Existing xcsh deployment | Existing certificate, load balancers, and origin pool |
| Existing Terraform deployment | Existing certificate and load balancers; optional Wingman pool and route |
| Bootstrap | Secret Policy, single-site virtual site, and vK8s |
| Runtime | Wingman certificate object, Deployment, Service, and encrypted-material ConfigMap |
| Qualification | Three disposable probe Deployments in a separate state; no retained resources |

Choose an independent naming base for a new deployment. Preserve existing owner states and certificate material. The application chain must match its key; the origin trust input must be a signing CA. Keep the application chain, origin CA, and public endpoint certificate in their separate fields.

## Configure

### Download the configuration

Use a verified source checkout or [download the configuration](https://github.com/f5-sales-demo/certificate-management/tree/main/wingman).
Preserve `wingman/contract.json` beside `bootstrap/`, `runtime/`, and `qualification/`. Keep state and session credentials
outside Git with directory mode 0700 and file mode 0600. Use the latest published providers with `init -upgrade`.

Choose `<XCSH_WINGMAN_NAME>`, `<XCSH_WINGMAN_SITE_SELECTOR>`, `<XCSH_KUBECONFIG_FILE>`, and
`<XCSH_KUBECONFIG_CONTEXT>` independently. Unknown identities remain placeholders. Supply the
governed `:latest` image or an immutable digest as `<XCSH_WINGMAN_IMAGE>`. Record the resolved pod image ID in verification evidence.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR">

```bash
umask 077
mkdir -p "$XCSH_WORKDIR/wingman/bootstrap" "$XCSH_WORKDIR/wingman/runtime" "$XCSH_WORKDIR/wingman/qualification"
for root in bootstrap runtime qualification; do
  for file in main.tf versions.tf; do
    curl --silent --show-error --fail \
      "https://f5-sales-demo.github.io/certificate-management/_data/wingman/$root/$file" \
      --output "$XCSH_WORKDIR/wingman/$root/$file"
  done
done
for root in runtime qualification; do
  curl --silent --show-error --fail \
    "https://f5-sales-demo.github.io/certificate-management/_data/wingman/$root/variables.tf" \
    --output "$XCSH_WORKDIR/wingman/$root/variables.tf"
done
for file in contract.json qualify.py kubeconfig.py resolve_image.py; do
  curl --silent --show-error --fail \
    "https://f5-sales-demo.github.io/certificate-management/_data/wingman/$file" \
    --output "$XCSH_WORKDIR/wingman/$file"
done

```

</div>

The selected `latest` image is resolved from the public registry to a verified immutable digest during planning. Review that digest in the saved plan; a later `init -upgrade` and fresh plan can select a newer publication.
Keep the downloaded files together and preserve dependency lockfiles after `init -upgrade`. Record installed versions and pod image IDs in private verification evidence. Resolve publications again when repeating acceptance after an artifact changes.

### Create bootstrap and runtime

Provide `XCSH_API_URL` and `XCSH_API_TOKEN` in the process environment, as in the
[Terraform prerequisites](../../terraform/#prerequisites). No CLI is required for Terraform encryption.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE XCSH_WINGMAN_NAME XCSH_WINGMAN_SITE_SELECTOR XCSH_WORKDIR">

```bash
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_WINGMAN_NAME"
export TF_VAR_site_selector="$XCSH_WINGMAN_SITE_SELECTOR"
terraform -chdir="$XCSH_WORKDIR/wingman/bootstrap" init -upgrade
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

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_KUBECONFIG_FILE XCSH_KUBECONFIG_CONTEXT XCSH_WINGMAN_IMAGE XCSH_APPLICATION_CERT_FILE XCSH_KEY_FILE XCSH_DOMAINNAME XCSH_WORKDIR">

```bash
export TF_VAR_kubeconfig_file="$XCSH_KUBECONFIG_FILE"
export TF_VAR_kubeconfig_context="$XCSH_KUBECONFIG_CONTEXT"
export TF_VAR_application_image="$XCSH_WINGMAN_IMAGE"
export TF_VAR_certificate_file="$XCSH_APPLICATION_CERT_FILE"
export TF_VAR_private_key_file="$XCSH_KEY_FILE"
export TF_VAR_domain="$XCSH_DOMAINNAME"
terraform -chdir="$XCSH_WORKDIR/wingman/runtime" init -upgrade
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

### Connect the existing owner

Create a second encrypted location with the same Wingman policy using the latest xcsh release.
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

Run the [planned unseal and denial checks](../#plan-disposable-qualification-infrastructure) before enabling the route. The qualification state owns those disposable probes; the observer cannot create them.

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
as its trust input. Set `XCSH_APPLICATION_CERT_FILE` to the Wingman leaf chain and
`XCSH_ORIGIN_CA_FILE` to its root CA; keep `XCSH_CERT_FILE` pointed at the original public load-balancer
certificate. Require backend TLS verification and the public Wingman marker. Its response fingerprint
must equal the backend Wingman leaf fingerprint; public TLS must retain the original certificate. Also verify
both original `/get` responses, both redirects, and empty plans in all three Terraform states.
Credential-free CI checks schemas and public health separately from fresh live unseal evidence.
Wingman is reported separately from the existing 25-node certificate matrix and its 16 qualified lifecycles.

## Verify

Follow the [walkthrough verification](../#verify) using the actual copied commands. Require fresh
authorized unseal, denied HTTP 403, preserved TLS material and existing endpoints, and empty
follow-up plans. Publish only sanitized results in a new receipt; preserve historical receipts. The
[walkthrough qualification record](../../../assets/wingman-human-walkthrough-qualification.json)
records this validation separately.

## Remove

### Recover interrupted changes

Set the existing owner's `wingman` input back to null, review the plan, and apply it to remove only
the Wingman route and pool. Verify both original endpoints and redirects. Then review and apply a saved runtime destroy plan, followed by a saved bootstrap destroy plan. Keep the scoped kubeconfig active until runtime and all disposable consumers are verified absent, then revoke it. Remove bootstrap consumers in dependency order. Read policy
`marked_for_delete` and `deletion_time` as observed lifecycle facts; a pending tombstone is not absence.
Do not send a second DELETE to a marked policy or assume same-name recreation restores its old policy ID.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_WORKDIR">

```bash
python3 "$XCSH_WORKDIR/wingman/kubeconfig.py" revoke \
  --private-directory "$XCSH_WORKDIR/wingman/session"
```

</div>

For Terraform-owned probes, resume using the same state, inventory, and observation journal, review
a fresh destroy plan, then use `--verify-cleanup`. If apply failed before inventory export,
reconcile exact state/remote identities first and recover the inventory; do not blindly replay the
old plan. The legacy `--cleanup-only` mode retains exact-UID deletion for earlier imperative-run
journals only and refuses Terraform-owned journals.

Preserve private state, encrypted provenance, and cleanup journals after any failure. Verify exact
UIDs and the run label before recovering disposable probes; never use prefix sweeps or delete the
retained namespace. Public as-built receipts may contain versions, digests, status, and public
fingerprints. Keys, kubeconfig data, tokens, raw plans, and raw API responses stay private.
