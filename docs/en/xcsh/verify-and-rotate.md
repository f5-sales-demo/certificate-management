---
title: Verify and rotate
description: Verify readiness and strict TLS, then rotate with an existing renewed pair.
sidebar:
  label: Verify and rotate
  order: 3
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Verify the certificate served by your HTTPS load balancer, then replace it using an existing renewed certificate and key. Complete [creation](../create-certificates/) and keep its saved manifests, paired public documents, and `make-certificate.py`. Supply `chain2.pem`, `server2-key.pem`, and both trust files from the [overview](../#before-you-begin). Allow five minutes per propagation check.

## Check resource readiness

Read the named resource privately:

```bash
xcsh get http_loadbalancer "$XCSH_LB_NAME" -n "$XCSH_NAMESPACE" -o json   > readiness.json 2> readiness.err
jq -e '.success and .results[0].resource.spec.state == "VIRTUAL_HOST_READY" and
  .results[0].resource.spec.cert_state == "CertificateValid"' readiness.json > /dev/null
```

Wait for `VIRTUAL_HOST_READY` and `CertificateValid`, then check DNS. Have your DNS owner verify the hostname at the zone's authoritative nameservers as well as your client's resolver. A ready API resource alone does not prove the served certificate.

## Verify strict TLS

Create this script in your private directory. It waits up to five minutes, resolves the client hostname, validates explicit trust and hostname/SNI, compares the leaf SHA-256 fingerprint, and checks HTTP 200 from `/get`. If your application has another approved success path, change `/get` and its expected status accordingly.

```bash
cat > verify-https.py <<'PY'
import hashlib
import json
import os
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path

leaf, trust_file, report_name = sys.argv[1:]
expected = hashlib.sha256(subprocess.check_output(
    ['openssl', 'x509', '-in', leaf, '-outform', 'DER'])).hexdigest()
trust = ssl.create_default_context(cafile=trust_file)
domain = os.environ['XCSH_DOMAINNAME']
deadline = time.monotonic() + 300
while time.monotonic() < deadline:
    with open('lb-readback.json', 'wb') as out, open('lb-readback.err', 'wb') as err:
        read = subprocess.run([
            'xcsh', 'get', 'http_loadbalancer', os.environ['XCSH_LB_NAME'],
            '-n', os.environ['XCSH_NAMESPACE'], '-o', 'json',
        ], stdout=out, stderr=err, timeout=40, check=False)
    if read.returncode:
        raise SystemExit('Named load balancer read failed; inspect private report')
    spec = json.loads(Path('lb-readback.json').read_text())['results'][0]['resource']['spec']
    if (spec.get('state') != 'VIRTUAL_HOST_READY'
            or spec.get('cert_state') != 'CertificateValid'):
        time.sleep(3)
        continue
    try:
        addresses = sorted({x[4][0] for x in socket.getaddrinfo(
            domain, 443, type=socket.SOCK_STREAM)})
    except socket.gaierror:
        time.sleep(3)
        continue
    for address in addresses:
        vip = address
        if not vip:
            continue
        try:
            with socket.create_connection((vip, 443), timeout=5) as raw:
                with trust.wrap_socket(raw, server_hostname=domain) as tls:
                    actual = hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest()
            if actual != expected:
                continue
            with open('https.err', 'wb') as err:
                response = subprocess.run([
                    'curl', '--silent', '--show-error', '--fail', '--noproxy', '*',
                    '--connect-timeout', '5', '--max-time', '10', '--cacert', trust_file,
                    '--resolve', domain + ':443:' + ('[' + vip + ']' if ':' in vip else vip), 'https://' + domain + '/get',
                    '--output', 'https-body.txt', '--write-out', '%{http_code}',
                ], stdout=subprocess.PIPE, stderr=err, check=False)
            if response.returncode or response.stdout != b'200':
                continue
            summary = {
                'ready': True, 'certificate_valid': True, 'ca_trust': True,
                'sni': True, 'fingerprint_match': True, 'https': 200,
                'fingerprint': actual, 'client_dns': True,
            }
            Path(report_name).write_text(json.dumps(summary, indent=2) + '\n')
            print(json.dumps({k: v for k, v in summary.items() if k != 'fingerprint'}))
            raise SystemExit(0)
        except (OSError, ssl.SSLError):
            continue
    time.sleep(3)
raise SystemExit('HTTPS did not converge within five minutes; inspect private reports')
PY
python3 verify-https.py chain1.pem trust1.pem tls1-summary.json
```

Expected summary: every check is `true`, with `"https": 200`. For self-signed inputs, `trust1.pem` is the public certificate itself. For issued certificates, use your approved trust anchors. Keep system trust unchanged; do not disable certificate verification. This check requires an unexpired certificate and a DNS SAN matching `XCSH_DOMAINNAME`.

## Rotate with renewed inputs

Inspect the existing owned certificate, confirm the renewed chain/key match, and validate them with native preparation using new artifact paths. Retain the working certificate and trust anchor until the replacement serves successfully.

```bash
xcsh blindfold certificate --context-name certificate-admin   --cert chain2.pem --key server2-key.pem --name "$XCSH_CERT_NAME"   -n "$XCSH_NAMESPACE" --output-file native-renewed-certificate.json   > renewed-prepared.json 2> renewed-prepared.err
```

To follow the saved-manifest path, encrypt the existing replacement key, use the same serializer and ownership labels, and apply its new chain and location:

```bash
xcsh blindfold encrypt --input server2-key.pem \
  --public-key tenant-public-key.json --policy-document policy.json \
  --encoding location --output-file key2.location \
  > encrypt2-report.json 2> encrypt2.err
python3 make-certificate.py chain2.pem key2.location certificate2.json
xcsh validate -f certificate2.json -n "$XCSH_NAMESPACE" -o json \
  > certificate2-validation.json 2> certificate2-validation.err
xcsh apply -f certificate2.json -n "$XCSH_NAMESPACE" --dry-run client -o json \
  > certificate2-preview.json 2> certificate2-preview.err
xcsh apply -f certificate2.json -n "$XCSH_NAMESPACE" -o json \
  > certificate2-apply.json 2> certificate2-apply.err
jq -e '.success and .results[0].status == "updated"' \
  certificate2-apply.json > /dev/null
```

The load balancer keeps the same certificate reference. F5 rejects an algorithm change while a certificate is referenced; rotate RSA to RSA or elliptic curve (EC) to EC. To change algorithms, create a separate certificate, change the reference, and verify before removing the old resource.

```bash
python3 verify-https.py chain2.pem trust2.pem tls2-summary.json
jq -e -s '.[0].fingerprint != .[1].fingerprint and
  .[0].https == 200 and .[1].https == 200' \
  tls1-summary.json tls2-summary.json > /dev/null
printf '%s\n' 'Rotation verified: fingerprint changed; HTTPS 200'
```

Expected result: the served fingerprint changes and HTTPS returns 200 after rotation. This does not measure uninterrupted service during propagation. Retain the final saved manifest and private key for continued administration; identical reapply of that manifest should remain `unchanged`.

### Combined replacement

As an alternative to applying the rotation manifest, `blindfold replace` validates, encrypts, replaces once, and reads back the existing named certificate:

```bash
xcsh blindfold replace --context-name certificate-admin   --cert chain2.pem --key server2-key.pem --name "$XCSH_CERT_NAME"   -n "$XCSH_NAMESPACE" --json --result-file combined-replaced.json   > combined-replaced.out 2> combined-replaced.err
```

Replacement requires an existing name and preserves writable metadata and certificate options from F5's replace form. Verify TLS separately after either replacement path.

## Retire owned resources optionally

Retirement is an administrative choice; the permanent showcase remains deployed. Before deletion, verify recorded ownership and that no other resource references the certificate. Delete your load balancer first, then its certificate. Preserve shared origin pools, DNS zones, unrelated records, and shared certificates.

```bash
xcsh delete http_loadbalancer "$XCSH_LB_NAME" -n "$XCSH_NAMESPACE" -o json \
  > lb-delete.json 2> lb-delete.err
xcsh delete certificate "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" -o json \
  > certificate-delete.json 2> certificate-delete.err
```

Verify the exact names are absent; only a named `not_found` confirms absence:

```bash
python3 - <<'PY'
import json
import os
import subprocess
import time
from pathlib import Path

for kind, name in [('http_loadbalancer', os.environ['XCSH_LB_NAME']),
                   ('certificate', os.environ['XCSH_CERT_NAME'])]:
    deadline = time.monotonic() + 120
    while True:
        with open(kind + '-absence.json', 'wb') as out, open(kind + '-absence.err', 'wb') as err:
            result = subprocess.run([
                'xcsh', 'get', kind, name, '-n', os.environ['XCSH_NAMESPACE'], '-o', 'json',
            ], stdout=out, stderr=err, timeout=40, check=False)
        report = json.loads(Path(kind + '-absence.json').read_text())
        error = report['results'][0].get('error', {})
        if result.returncode and error.get('kind') == 'not_found':
            break
        if error or time.monotonic() >= deadline:
            raise SystemExit('Named absence not verified; inspect private report')
        time.sleep(3)
print('Cleanup verified: both named resources absent')
PY
```

Keep private ownership records until absence is verified, then follow your retention policy for local artifacts. An authentication or network error is not cleanup evidence. See [Troubleshooting](../troubleshooting/) for failures.
