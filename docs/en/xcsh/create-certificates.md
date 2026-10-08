---
title: Create certificates
description: Prepare one validated manifest, preview and apply it, then configure HTTPS.
sidebar:
  label: Create certificates
  order: 1
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Complete the [overview setup](../#before-you-begin). Supply `chain1.pem`, a current PEM certificate chain with the leaf first, and its matching unprotected `server1-key.pem`. Allow about ten minutes plus propagation. For protected PEM, PKCS#12, or stdin, choose an [input workflow](../input-workflows/) instead of the preparation command below.

Inspect the exact certificate and load balancer names before applying. Create missing resources you own; if an existing name belongs to another operator or project, select another name. Schema validation and dry run do not establish ownership.

## Prepare a validated manifest

Prepare `certificate1.json` directly. Native preparation checks the key matches the leaf, chain order, issuer signatures, and validity dates, then encrypts the normalized key. It retrieves public material using the default `shared/ves-io-allow-volterra` policy and creates no tenant resource.

```bash
xcsh blindfold certificate --context-name certificate-admin \
  --cert chain1.pem --key server1-key.pem --name "$XCSH_CERT_NAME" \
  -n "$XCSH_NAMESPACE" --output-file certificate1.json \
  > certificate1-prepared.json 2> certificate1-prepared.err
jq -e '.status == "prepared"' certificate1-prepared.json > /dev/null
export XCSH_CERT_MANIFEST=certificate1.json
```

## Preview and apply

Use this procedure for any saved native manifest. `XCSH_CERT_MANIFEST` names the file you prepared; report filenames derive from it. Validate and preview the file:

```bash
XCSH_APPLY_PREFIX="${XCSH_CERT_MANIFEST%.json}"
jq -e . "$XCSH_CERT_MANIFEST" > /dev/null
xcsh validate -f "$XCSH_CERT_MANIFEST" -n "$XCSH_NAMESPACE" -o json \
  > "$XCSH_APPLY_PREFIX-validation.json" 2> "$XCSH_APPLY_PREFIX-validation.err"
xcsh apply -f "$XCSH_CERT_MANIFEST" -n "$XCSH_NAMESPACE" --dry-run client -o json \
  > "$XCSH_APPLY_PREFIX-preview.json" 2> "$XCSH_APPLY_PREFIX-preview.err"
```

Inspect the full private preview before continuing. Client dry run reads the target and calculates changes without a tenant write. Apply the same file:

```bash
xcsh apply -f "$XCSH_CERT_MANIFEST" -n "$XCSH_NAMESPACE" -o json \
  > "$XCSH_APPLY_PREFIX-apply.json" 2> "$XCSH_APPLY_PREFIX-apply.err"
jq -e '.success and (.results[0].status == "created" or
  .results[0].status == "updated" or .results[0].status == "unchanged")' \
  "$XCSH_APPLY_PREFIX-apply.json" > /dev/null
jq '{success, statuses: [.results[].status]}' "$XCSH_APPLY_PREFIX-apply.json"
```

Expect `created` for a missing owned name, `updated` for changed owned configuration, or `unchanged` for an identical manifest. Generic parsing and schema validation do not check whether an encrypted key matches the certificate; native preparation performs that check before encryption.

Reapply the identical saved file:

```bash
xcsh apply -f "$XCSH_CERT_MANIFEST" -n "$XCSH_NAMESPACE" -o json \
  > "$XCSH_APPLY_PREFIX-reapply.json" 2> "$XCSH_APPLY_PREFIX-reapply.err"
jq -e '.success and .results[0].status == "unchanged"' \
  "$XCSH_APPLY_PREFIX-reapply.json" > /dev/null
```

Expect `unchanged`. Encryption uses fresh randomness, so encrypting the same key again produces different ciphertext. Preserve the saved manifest and encrypted location for unchanged reapply.

## Reference an existing origin pool

Supply an existing reachable origin pool, an owned hostname with a DNS record, and outbound endpoint access on port 443. For an HTTPS origin, verify upstream trust and matching Server Name Indication (SNI) there. Set `XCSH_UPSTREAM_HOST` to the origin's expected Host header. Keep the approved origin pool configuration under its existing owner's control.

This minimal HTTPS load balancer references your certificate and existing pool. It enables no application security controls; apply your
organization's security configuration before using it beyond an authorized administration example. The owned hostname needs a DNS record,
either managed by the load balancer in an existing F5 DNS zone or provisioned by your DNS owner. Preserve unrelated records.

```bash
export XCSH_ORIGIN_POOL_NAME='<EXISTING_ORIGIN_POOL_NAME>'
export XCSH_ORIGIN_NAMESPACE="$XCSH_NAMESPACE"
export XCSH_DOMAINNAME='app.example.com'
export XCSH_UPSTREAM_HOST='origin.example.com'
python3 - <<'PY'
import json
import os
from pathlib import Path

XCSH_NAMESPACE = os.environ['XCSH_NAMESPACE']
ORIGIN_NAMESPACE = os.environ['XCSH_ORIGIN_NAMESPACE']
manifest = {
    'kind': 'http_loadbalancer',
    'metadata': {
        'name': os.environ['XCSH_LB_NAME'],
        'namespace': XCSH_NAMESPACE,
        'labels': {'certificate-administration': 'example-tls'},
    },
    'spec': {
        'domains': [os.environ['XCSH_DOMAINNAME']],
        'https': {
            'port': 443,
            'tls_cert_params': {
                'certificates': [{
                    'name': os.environ['XCSH_CERT_NAME'],
                    'namespace': XCSH_NAMESPACE,
                }],
                'no_mtls': {},
                'tls_config': {'default_security': {}},
            },
            'http_redirect': False,
            'enable_path_normalize': {},
        },
        'advertise_on_public_default_vip': {},
        'routes': [{'simple_route': {
            'http_method': 'ANY',
            'path': {'prefix': '/'},
            'origin_pools': [{
                'pool': {
                    'name': os.environ['XCSH_ORIGIN_POOL_NAME'],
                    'namespace': ORIGIN_NAMESPACE,
                },
                'weight': 1,
                'priority': 1,
                'endpoint_subsets': {},
            }],
            'host_rewrite': os.environ['XCSH_UPSTREAM_HOST'],
        }}],
        'default_route_pools': [{
            'pool': {
                'name': os.environ['XCSH_ORIGIN_POOL_NAME'],
                'namespace': ORIGIN_NAMESPACE,
            },
            'weight': 1,
            'priority': 1,
            'endpoint_subsets': {},
        }],
        'origin_pools': [],
        'disable_waf': {},
        'no_service_policies': {},
        'disable_api_definition': {},
        'disable_api_discovery': {},
        'disable_bot_defense': {},
        'disable_rate_limit': {},
        'disable_ip_reputation': {},
        'disable_malicious_user_detection': {},
    },
}
with Path('load-balancer.json').open('x') as output:
    json.dump(manifest, output, indent=2)
    output.write('\n')
PY
xcsh validate -f load-balancer.json -n "$XCSH_NAMESPACE" -o json \
  > lb-validation.json 2> lb-validation.err
xcsh apply -f load-balancer.json -n "$XCSH_NAMESPACE" --dry-run client -o json \
  > lb-preview.json 2> lb-preview.err
```

Inspect `lb-preview.json` privately before applying:

```bash
xcsh apply -f load-balancer.json -n "$XCSH_NAMESPACE" -o json \
  > lb-apply.json 2> lb-apply.err
jq -e '.success and (.results[0].status == "created" or .results[0].status == "updated" or .results[0].status == "unchanged")' lb-apply.json > /dev/null
```

Continue to [Verify and rotate](../verify-and-rotate/). API acceptance does not establish that clients receive the expected certificate.
