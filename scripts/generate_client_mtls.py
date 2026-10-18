# /// script
# dependencies = ["python-hcl2==7.3.1"]
# ///
"""Generate client mTLS documentation and public policy JSON from canonical HCL."""

# ruff: noqa: S608 -- Markdown command generation; no SQL execution.
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

import hcl2

ROOT = Path(__file__).resolve().parents[1]
PROSE_WRAP_THRESHOLD = 180


def generate(
    schema: dict,
    public: Callable[[dict, dict], dict],
    public_json: Callable[[Any], str],
    fence: Callable[[str, str], str],
) -> None:
    # Complete canonical guide rendering holds inputs and sections together.
    # pylint: disable=too-many-locals
    """Render the six-stage client workflow and its exact source downloads."""
    directory = ROOT / "terraform/named-certificate"
    source = hcl2.loads((directory / "client-mtls.tf").read_text())
    policy = next(
        item["xcsh_service_policy"]["client_write"]
        for item in source["resource"]
        if "xcsh_service_policy" in item
    )
    policy.pop("count")
    # Name interpolation has a distinct role from the server certificate.
    policy["name"] = "<XCSH_LB_NAME>-client-write"
    rendered = public(policy, schema["xcsh_service_policy"]["block"])
    metadata = {key: rendered.pop(key) for key in ["name", "namespace"]}
    config = {
        "trusted_ca_list": {
            "metadata": {
                "name": "<XCSH_LB_NAME>-client-ca",
                "namespace": "<XCSH_NAMESPACE>",
            },
            "spec": {"trusted_ca_url": "string:///<BASE64_CLIENT_CA_BUNDLE>"},
        },
        "service_policy": {"metadata": metadata, "spec": rendered},
        "https_tls_cert_params_extension": {
            "use_mtls": {
                "trusted_ca": {
                    "name": "<XCSH_LB_NAME>-client-ca",
                    "namespace": "<XCSH_NAMESPACE>",
                },
                "client_certificate_optional": True,
                "no_crl": {},
                "xfcc_options": {"xfcc_header_elements": ["XFCC_CERT", "XFCC_CHAIN"]},
            }
        },
    }
    json_text = public_json(config)
    (ROOT / "docs/assets/configurations/client-mtls.json").write_text(json_text)
    commands = '''umask 077
configuration="$XCSH_WORKDIR/named-certificate"
python3 "$XCSH_WORKDIR/client_pki.py" init "$XCSH_CLIENT_CA_DIR"
python3 "$XCSH_WORKDIR/client_pki.py" issue "$XCSH_CLIENT_CA_DIR" --client "$XCSH_CLIENT_NAME"
python3 "$XCSH_WORKDIR/client_pki.py" crl "$XCSH_CLIENT_CA_DIR" --revision "$XCSH_CLIENT_CRL_REVISION"
openssl verify -purpose sslclient -CAfile "$XCSH_CLIENT_CA_FILE" "$XCSH_CLIENT_CERT_FILE"
openssl crl -in "$XCSH_CLIENT_CRL_FILE" -noout -verify -CAfile "$XCSH_CLIENT_CA_FILE"'''
    variables = '''python3 - "$configuration/client.auto.tfvars.json" "$XCSH_CLIENT_CA_FILE" "$XCSH_CLIENT_CRL_FILE" "$XCSH_CLIENT_CRL_REVISION" <<'PY'
import json
import os
import sys
os.umask(0o077)
path, ca, crl, revision = sys.argv[1:]
with open(path, "x") as stream:
    json.dump({"client_mtls": {"trusted_ca_file": ca, "crl_revisions": {revision: crl}, "active_crl_revision": revision}}, stream, indent=2)
PY
terraform -chdir="$configuration" init -upgrade
terraform -chdir="$configuration" validate
terraform -chdir="$configuration" plan -out=client.plan
terraform -chdir="$configuration" show client.plan
shasum -a 256 "$configuration/client.plan"'''
    verify = """challenge=$(openssl rand -hex 16)
curl --silent --show-error --fail "https://$XCSH_DOMAINNAME/mtls/identity?challenge=$challenge"
openssl x509 -in "$XCSH_CLIENT_CERT_FILE" -noout -fingerprint -sha256
for method in POST PUT PATCH; do
  challenge=$(openssl rand -hex 16)
  curl --silent --show-error --fail --cert "$XCSH_CLIENT_CERT_FILE" --key "$XCSH_CLIENT_KEY_FILE" \\
    --request "$method" "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
  curl --silent --show-error --output /dev/null --write-out '%{http_code}\\n' \\
    --request "$method" "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
done
curl --silent --show-error --fail "http://$XCSH_DOMAINNAME/mtls/crl/$XCSH_CLIENT_CRL_REVISION.pem" --output "$XCSH_WORKDIR/downloaded-crl.pem"
cmp "$XCSH_CLIENT_CRL_FILE" "$XCSH_WORKDIR/downloaded-crl.pem"
openssl crl -in "$XCSH_WORKDIR/downloaded-crl.pem" -noout -verify -CAfile "$XCSH_CLIENT_CA_FILE"
openssl crl -in "$XCSH_WORKDIR/downloaded-crl.pem" -noout -issuer -lastupdate -nextupdate -text
terraform -chdir="$configuration" output -json client_mtls_inventory
terraform -chdir="$configuration" plan -detailed-exitcode"""
    forged = """for method in POST PUT PATCH; do
  for value in 'Hash=forged' 'Cert="%zz"' 'Hash=one;Hash=two'; do
    challenge=$(openssl rand -hex 16)
    curl --silent --show-error --output /dev/null --write-out '%{http_code}\\n' \\
      --request "$method" --header "X-Forwarded-Client-Cert: $value" \\
      "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
  done
  challenge=$(openssl rand -hex 16)
  curl --silent --show-error --output /dev/null --write-out '%{http_code}\\n' \\
    --request "$method" --header 'X-Forwarded-Client-Cert: Hash=one' \\
    --header 'X-Forwarded-Client-Cert: Hash=two' \\
    "https://$XCSH_DOMAINNAME/mtls/write?challenge=$challenge"
done"""
    hcl = "\n\n".join(
        path.read_text().rstrip() for path in sorted(directory.glob("*.tf"))
    )
    download = (
        """umask 077
configuration="$XCSH_WORKDIR/named-certificate"
mkdir -p "$configuration"
"""
        + "\n".join(
            f'curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/named-certificate/{path.name}" --output "$configuration/{path.name}"'
            for path in sorted(directory.glob("*.tf"))
        )
        + '''
curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/scripts/client_pki.py" --output "$XCSH_WORKDIR/client_pki.py"'''
    )
    text = (
        """---
title: Client mTLS
description: Optional frontend client certificates, forwarded identity and certificate-authorized synthetic writes.
sidebar:
  order: 4
---

## Prerequisites

Complete the [server certificate workflow](../) and [Wingman runtime](../../wingman/). Use the existing named-certificate owner state and Wingman pool. [Origin mTLS](../certificate-surfaces/origin-mtls/) authenticates the load balancer to an origin; client mTLS authenticates a caller to the frontend. Keep their material distinct.

The retained Regional Edge endpoint uses optional client authentication with `no_crl`. Live XC validation rejects CRLs on Regional Edges. Edge CRL revocation is excluded from this workflow. Signed CRLs remain public downloadable lifecycle material; downloading one does not revoke a client at the edge.

Use Python 3 and OpenSSL 3 on Ubuntu or macOS. Store the synthetic CA database, CA key, client keys and plans in an owner-only directory outside Git. Only public CA certificates and signed PEM CRLs enter Terraform state. Select client file paths produced below; never reuse server, origin or Wingman key inputs.

## Configuration

Client mTLS is disabled when `client_mtls = null`. The complete HCL retains the named server certificate and existing routes. The public JSON describes the added resources and TLS extension; encoded-material placeholders are illustrative.

[Download public JSON](../../../assets/configurations/client-mtls.json).

"""
        + fence("json", json_text)
        + "\n"
        + fence("hcl", hcl)
        + "\n"
        + fence("bash", download)
        + """
The retained owner already has its Wingman contract and Default pool module dependencies. For an isolated deployment, download the same dependencies listed in the server workflow before initializing.

## Configure

Initialize a new private synthetic CA directory once, then issue a client certificate with `clientAuth`. Set Client CA file to `ca.pem`, Client certificate/key files to `clients/<client>/certificate.pem` and `key.pem`, and Client CRL file to `crls/<revision>.pem` under that directory.

"""
        + fence("bash", commands)
        + "\n"
        + fence("bash", variables)
        + """
Deploy the qualified Wingman image first. Publish the exact public CRL route and verify its bytes and signature, then enable optional client trust and the ordered Service Policy with `no_crl`. No XC CRL object is created. Review and hash fresh saved plans and reject unrelated changes or retained-resource replacement. Finish with a full zero-change plan.

The policy denies POST, PUT and PATCH on exact `/mtls/write` when XFCC is absent, then allows other traffic. Qualification must prove the edge sanitizes client-supplied XFCC before policy evaluation. The origin parser alone cannot establish edge trust. A header bypass fails acceptance and requires rollback.

## Verify

Use a new cURL process and unique challenge for every probe. Keep server verification enabled. Match the response challenge and `forwarded_client_certificate_sha256` to the client leaf fingerprint; `origin_server_certificate_sha256` identifies the Wingman server certificate separately. Synthetic acknowledgments store and echo no submitted data.

"""
        + fence("bash", verify)
        + "\n"
        + fence("bash", forged)
        + """
Expect public identity HTTP 200 with an empty client fingerprint, trusted writes HTTP 200, and certificate-free or forged-header writes HTTP 403. Require duplicate and malformed header denial, including a copied complete valid XFCC value presented without a client certificate. Presented untrusted and expired certificates must fail TLS before the handler returns a challenge. With `no_crl`, a locally revoked certificate remains accepted by the edge until it expires or its issuing CA loses trust. Prove and record that behavior explicitly; do not claim edge revocation.

Recheck `/get`, `/wingman/get`, all HTTP redirects outside the exact CRL paths, server fingerprints, retained resource IDs and Default pool responses. Repeat Wingman injection, READY, authorized unseal, denial, identity chain, TLS, restart, cleanup and credential revocation after publishing its changed image. Record client acceptance separately from the historical certificate matrix.

## Maintain

Renew by issuing another client under the same CA with a new issuance name. It has a new serial and fingerprint; both old and renewed certificates remain valid until explicit revocation.

"""
        + fence(
            "bash",
            '''python3 "$XCSH_WORKDIR/client_pki.py" issue "$XCSH_CLIENT_CA_DIR" --client "$XCSH_CLIENT_NAME-renewed"
python3 "$XCSH_WORKDIR/client_pki.py" revoke "$XCSH_CLIENT_CA_DIR" --client "$XCSH_CLIENT_NAME"
python3 "$XCSH_WORKDIR/client_pki.py" crl "$XCSH_CLIENT_CA_DIR" --revision "$XCSH_CLIENT_CRL_REVISION-next"''',
        )
        + """
Add the newly signed CRL to `crl_revisions` and publish and verify its exact HTTP path through a fresh reviewed plan. The CRL documents local revocation only. With fresh connections, verify the old and renewed clients still work at the edge while their CA remains trusted. Renewal and local revocation do not invalidate an individual client at this Regional Edge listener.

For CA rotation, initialize a separate private CA database and client. Concatenate the two public CA certificates into the trusted bundle. You may publish both issuers' signed PEM CRLs as a public bundle; verify each signature and validity window independently. The edge does not consume this CRL bundle. Preserve `xcsh_trusted_ca_list.client[0]` identity while adding new trust. Prove both clients work during overlap, then remove old CA trust through a reviewed update and prove old clients fail while new clients work. Retain prior public revisions until the transition is verified.

## Remove

Set `client_mtls = null` through a fresh reviewed plan. Remove the client policy, trust and public CRL routes while preserving the server certificate, load balancers, Wingman and Default pool additions. Verify public reads and redirects, unchanged server fingerprints and zero-change refresh. Exercise full destroy separately on an isolated deployment of this same configuration; never destroy the retained owner to test removal.
"""
    )
    page = ROOT / "docs/en/terraform/client-mtls/index.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if (
            not fenced
            and len(line) > PROSE_WRAP_THRESHOLD
            and not line.startswith(("<", "```"))
        ):
            lines.extend(
                textwrap.wrap(
                    line, width=120, break_long_words=False, break_on_hyphens=False
                )
            )
        else:
            lines.append(line)
    page.write_text("\n".join(lines) + "\n")
    imports = ROOT / "docs/_imports"
    lines = imports.read_text().splitlines()
    for path in [*sorted(directory.glob("*.tf")), ROOT / "scripts/client_pki.py"]:
        relative = path.relative_to(ROOT).as_posix()
        line = f"{relative} -> {relative}"
        if line not in lines:
            lines.append(line)
    imports.write_text("\n".join(lines) + "\n")
