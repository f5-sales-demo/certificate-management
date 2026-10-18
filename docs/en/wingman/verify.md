---
title: Wingman — Verify
description: Verify for the Wingman certificate workflow.
sidebar:
  label: Verify
  order: 4
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../configure/
  label: Configure
next:
  link: ../maintain/
  label: Maintain
---

## Verify steps

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

Run the [planned disposable checks](#plan-disposable-qualification-infrastructure)
against your actual sidecar. They require `READY`, trusted platform-issued client/server identity
chains, successful unseal of both provider- and xcsh-prepared locations, and HTTP 403 for an
unselected workload. These platform identities are separate from your application TLS certificate.
An expected negative result is `denied: true` with `http_status: 403`; an authorized result reports
your public `certificate_sha256`. A public endpoint response alone does not verify fresh unseal or
denial.

Verify your public route using its configured trust certificate. For the published endpoint, use the [load-balancer trust certificate](../../../assets/certificate-management.pem). Set `XCSH_CERT_FILE` to the certificate that validates your public endpoint, and `XCSH_APPLICATION_CERT_FILE` to your Wingman application leaf chain.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_DOMAINNAME XCSH_CERT_FILE XCSH_APPLICATION_CERT_FILE">

```bash
expected=$(openssl x509 -in "$XCSH_APPLICATION_CERT_FILE" -outform DER | openssl dgst -sha256 -r | cut -d ' ' -f 1)
curl --silent --show-error --fail --cacert "$XCSH_CERT_FILE" \
  "https://$XCSH_DOMAINNAME/wingman/get" \
  | jq -e --arg fingerprint "$expected" \
    '.example == "wingman-certificate" and .certificate_sha256 == $fingerprint'
```

</div>

Expect `true`. The response reports the application's certificate fingerprint, while public TLS uses the load balancer's certificate. Verify backend TLS separately using the application trust CA and the same hostname, as described in [operator qualification](.././validation/#connect-the-existing-owner).

The [original delivery record](../../../assets/wingman-acceptance.json) and [current CLI
follow-up](../../../assets/wingman-xcsh-23.5.2-requalification.json) preserve their qualified versions.
The [walkthrough qualification record](../../../assets/wingman-human-walkthrough-qualification.json)
covers these instructions, planned probes, copied examples, and shared form values. Builder
qualification remains in the [operator record](.././validation/).
