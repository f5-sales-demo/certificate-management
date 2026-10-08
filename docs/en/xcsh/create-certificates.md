---
title: Create certificates
description: Prepare a certificate manifest and reference it from an HTTPS load balancer.
sidebar:
  label: Create certificates
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Create a certificate from existing inputs and reference an existing origin pool. Complete the [overview setup](../#before-you-begin) first. Use `chain1.pem` and its matching `server1-key.pem`; the manual path also needs `key1.location` from [encryption](../encrypt-private-keys/). Allow about ten minutes plus propagation.

Inspect the exact certificate and load balancer names before applying. Create missing resources you own; if an existing name belongs to another operator or project, select another name. Schema validation and dry run do not establish ownership.

## Prepare a validated certificate

Native preparation verifies the key matches the leaf, checks chain order, issuer signatures and validity dates, and encrypts the normalized key without deploying:

```bash
xcsh blindfold certificate --context-name certificate-admin \
  --cert chain1.pem --key server1-key.pem --name "$XCSH_CERT_NAME" \
  -n "$XCSH_NAMESPACE" --output-file native-certificate.json \
  --result-file native-prepared.json > native-report.json 2> native.err
```

It retrieves public material online with the default `shared/ves-io-allow-volterra` policy. Use [input workflows](../input-workflows/) for protected PEM or PKCS#12. To use this prepared artifact with the commands below, substitute `native-certificate.json` for `certificate1.json` throughout; reuse that same saved file on reapply.

## Construct structured JSON

For an already encrypted location, create this serializer and run it with the public chain. This alternative checks encoding, not the cryptographic relationship between the original key and chain; perform native validation of the source pair first.

```bash
cat > make-certificate.py <<'PY'
import base64
import json
import os
import sys
from pathlib import Path

chain_file, location_file, destination = sys.argv[1:]
XCSH_NAMESPACE = os.environ['XCSH_NAMESPACE']
location = Path(location_file).read_text().strip()
prefix = 'string:///'
if not location.startswith(prefix):
    raise SystemExit('Expected a Blindfold location')
base64.b64decode(location[len(prefix):], validate=True)
manifest = {
    'kind': 'certificate',
    'metadata': {
        'name': os.environ['XCSH_CERT_NAME'],
        'namespace': XCSH_NAMESPACE,
        'labels': {'certificate-administration': 'example-tls'},
    },
    'spec': {
        'certificate_url': prefix + base64.b64encode(
            Path(chain_file).read_bytes()).decode('ascii'),
        'private_key': {'blindfold_secret_info': {'location': location}},
    },
}
with Path(destination).open('x') as output:
    json.dump(manifest, output, indent=2)
    output.write('\n')
PY
python3 make-certificate.py chain1.pem key1.location certificate1.json
```

| Field | Purpose |
| --- | --- |
| `kind` | Selects the xcsh `certificate` resource kind. |
| `metadata.name`, `metadata.namespace` | Identify your owned resource. |
| `metadata.labels` | Record project ownership; use your team's label value consistently. |
| `spec.certificate_url` | `string:///` plus base64 of the public leaf-first PEM chain. Base64 is encoding. |
| `spec.private_key.blindfold_secret_info.location` | The retained encrypted location, unchanged. |

## Validate, apply, and reapply

Validate syntax and schema, inspect a client dry run, then apply your saved manifest. Capture all resource reports privately:

```bash
jq -e . certificate1.json > /dev/null
xcsh validate -f certificate1.json -n "$XCSH_NAMESPACE" -o json \
  > certificate1-validation.json 2> certificate1-validation.err
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" --dry-run client -o json \
  > certificate1-preview.json 2> certificate1-preview.err
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" -o json \
  > certificate1-apply.json 2> certificate1-apply.err
jq -e '.success and (.results[0].status == "created" or .results[0].status == "updated" or .results[0].status == "unchanged")' \
  certificate1-apply.json > /dev/null
jq '{success, statuses: [.results[].status]}' certificate1-apply.json
```

For a missing owned name, the sanitized status is `created`; reconciling owned configuration is `updated`, and an identical existing manifest is `unchanged`. Inspect the full private preview before any update. Client dry run reads the target and calculates changes without a tenant write. Neither JSON parsing nor generic schema validation checks that an encrypted key matches a certificate.

Apply the identical saved manifest again:

```bash
xcsh apply -f certificate1.json -n "$XCSH_NAMESPACE" -o json \
  > certificate1-reapply.json 2> certificate1-reapply.err
jq -e '.success and .results[0].status == "unchanged"' \
  certificate1-reapply.json > /dev/null
jq '{success, statuses: [.results[].status]}' certificate1-reapply.json
```

Expected status: `unchanged`. New encryption changes ciphertext; reuse the file rather than preparing it again.

### Combined creation

When you do not need a saved manifest, `blindfold create` validates, encrypts, creates once, and reads back the named certificate. Use it instead of generic creation for an absent owned name:

```bash
xcsh blindfold create --context-name certificate-admin   --cert chain1.pem --key server1-key.pem --name "$XCSH_CERT_NAME"   -n "$XCSH_NAMESPACE" --dry-run client --json   --result-file combined-preview.json > combined-preview.out 2> combined-preview.err
xcsh blindfold create --context-name certificate-admin   --cert chain1.pem --key server1-key.pem --name "$XCSH_CERT_NAME"   -n "$XCSH_NAMESPACE" --json --result-file combined-created.json   > combined-created.out 2> combined-created.err
```

Creation fails if the name exists. The public report's `accepted` status confirms matching named readback; it does not prove HTTPS readiness. See [uncertain outcomes](../troubleshooting/#reconcile-uncertain-outcomes) before retrying.

## Reference an existing origin pool

Your origin pool must already be reachable and configured for the intended origin. For an HTTPS origin, verify upstream trust and matching Server Name Indication (SNI) there. Set `XCSH_UPSTREAM_HOST` to the origin's expected Host header. Keep the approved origin pool configuration under its existing owner's control.

This minimal HTTPS load balancer references your certificate and existing pool. It enables no application security controls; apply your organization's security configuration before using it beyond an authorized administration example. The owned hostname needs a DNS record, either managed by the load balancer in an existing F5 DNS zone or provisioned by your DNS owner. Preserve unrelated records.

```bash
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
xcsh apply -f load-balancer.json -n "$XCSH_NAMESPACE" -o json \
  > lb-apply.json 2> lb-apply.err
jq -e '.success and (.results[0].status == "created" or .results[0].status == "updated" or .results[0].status == "unchanged")' lb-apply.json > /dev/null
```

Continue to [Verify and rotate](../verify-and-rotate/). API acceptance does not establish that clients receive the expected certificate.
