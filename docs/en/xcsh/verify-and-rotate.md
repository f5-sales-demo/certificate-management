---
title: Verify and rotate
description: Check resource readiness and strict TLS, then apply a validated replacement.
sidebar:
  label: Verify and rotate
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 2
---

Use the [overview setup](../#before-you-begin) and an existing HTTPS load balancer that references your certificate, such as the one in
[Create certificates](../create-certificates/). Set `XCSH_DOMAINNAME` to its owned hostname. Supply `chain1.pem` and approved `trust1.pem`
anchors; for a self-signed certificate, use that public certificate itself. Allow five minutes for propagation before repeating a failed
readiness or fingerprint check.

## Check resource readiness and DNS

Read the named load balancer and check both states:

```bash
xcsh get http_loadbalancer "$XCSH_LB_NAME" -n "$XCSH_NAMESPACE" -o json \
  > readiness.json 2> readiness.err
jq -e '.success and .results[0].resource.spec.state == "VIRTUAL_HOST_READY" and
  .results[0].resource.spec.cert_state == "CertificateValid"' readiness.json > /dev/null
```

Wait for `VIRTUAL_HOST_READY` and `CertificateValid`. Check resolution from your client:

```bash
python3 -c 'import os,socket; print(*sorted({a[4][0] for a in socket.getaddrinfo(os.environ["XCSH_DOMAINNAME"],443,type=socket.SOCK_STREAM)}),sep="\n")'
```

Have your DNS owner check the hostname at the zone's authoritative nameservers if resolution fails. Resource readiness alone does not prove which certificate clients receive.

## Verify strict TLS and the application

Select the expected chain, approved trust anchors, application path, and expected HTTP status. Keep the path beginning with `/`; use the application's documented success status.

```bash
export XCSH_EXPECTED_CHAIN=chain1.pem
export XCSH_TRUST_FILE=trust1.pem
export XCSH_HTTPS_PATH='/'
export XCSH_EXPECTED_HTTP_STATUS=200
export XCSH_TLS_PREFIX=tls1
```

Validate trust and the hostname, send Server Name Indication (SNI), and retain the served certificate:

```bash
openssl s_client -connect "$XCSH_DOMAINNAME:443" -servername "$XCSH_DOMAINNAME" \
  -verify_hostname "$XCSH_DOMAINNAME" -verify_return_error \
  -CAfile "$XCSH_TRUST_FILE" -showcerts < /dev/null \
  > "$XCSH_TLS_PREFIX-handshake.txt" 2> "$XCSH_TLS_PREFIX-handshake.err"
openssl x509 -in "$XCSH_TLS_PREFIX-handshake.txt" \
  -out "$XCSH_TLS_PREFIX-served.pem"
openssl x509 -in "$XCSH_EXPECTED_CHAIN" -noout -sha256 -fingerprint \
  > "$XCSH_TLS_PREFIX-expected.sha256"
openssl x509 -in "$XCSH_TLS_PREFIX-served.pem" -noout -sha256 -fingerprint \
  > "$XCSH_TLS_PREFIX-served.sha256"
cmp "$XCSH_TLS_PREFIX-expected.sha256" "$XCSH_TLS_PREFIX-served.sha256"
```

Expect successful trust and hostname validation and identical SHA-256 leaf fingerprints. A mismatch can indicate propagation or the wrong certificate reference; investigate before continuing. The certificate must be current and have a DNS Subject Alternative Name (SAN) matching the hostname.

Check the configured application path with the same trust and hostname:

```bash
curl --silent --show-error --fail --noproxy '*' \
  --connect-timeout 5 --max-time 15 --cacert "$XCSH_TRUST_FILE" \
  "https://$XCSH_DOMAINNAME$XCSH_HTTPS_PATH" \
  --output "$XCSH_TLS_PREFIX-body.txt" --write-out '%{http_code}\n' \
  > "$XCSH_TLS_PREFIX-http-status.txt" 2> "$XCSH_TLS_PREFIX-https.err"
test "$(cat "$XCSH_TLS_PREFIX-http-status.txt")" = "$XCSH_EXPECTED_HTTP_STATUS"
```

Expect the configured HTTP status. Keep system trust unchanged and do not disable certificate verification. An application failure after successful TLS checks requires [origin troubleshooting](../troubleshooting/#diagnose-deployment-and-tls-failures).

## Rotate with renewed inputs

Supply existing renewed `chain2.pem`, matching `server2-key.pem`, and approved `trust2.pem`. Inspect the owned certificate before changing it. Retain the working certificate and trust anchor until the replacement serves successfully.

Keep the same key algorithm while the certificate is referenced: RSA to RSA or elliptic curve (EC) to EC. To change algorithms, create a separate certificate, change the load balancer reference, and verify before removing the old resource.

Prepare the replacement once:

```bash
xcsh blindfold certificate --context-name certificate-admin \
  --cert chain2.pem --key server2-key.pem --name "$XCSH_CERT_NAME" \
  -n "$XCSH_NAMESPACE" --output-file certificate2.json \
  > certificate2-prepared.json 2> certificate2-prepared.err
jq -e '.status == "prepared"' certificate2-prepared.json > /dev/null
export XCSH_CERT_MANIFEST=certificate2.json
```

Follow [Preview and apply](../create-certificates/#preview-and-apply) with this saved manifest, including unchanged reapply. A changed replacement returns `updated`; the load balancer keeps the same certificate reference.

Select the replacement inputs, then repeat the resource, DNS, handshake, fingerprint, and application commands above:

```bash
export XCSH_EXPECTED_CHAIN=chain2.pem
export XCSH_TRUST_FILE=trust2.pem
export XCSH_TLS_PREFIX=tls2
```

Confirm the new served fingerprint matches `chain2.pem` and differs from the previous one:

```bash
if cmp -s tls1-served.sha256 tls2-served.sha256; then
  printf '%s\n' 'Replacement fingerprint did not change' >&2
  exit 1
fi
```

Retain `certificate2.json` and its private inputs for continued administration. These checks verify the replacement after propagation; they do not measure uninterrupted service during propagation.

## Retire owned resources optionally

Before deletion, verify ownership and that no other resource references the certificate. Delete your load balancer first, then its certificate. Preserve shared origin pools, DNS zones, and unrelated records.

```bash
xcsh delete http_loadbalancer "$XCSH_LB_NAME" -n "$XCSH_NAMESPACE" -o json \
  > lb-delete.json 2> lb-delete.err
xcsh delete certificate "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" -o json \
  > certificate-delete.json 2> certificate-delete.err
```

Read both exact names. These reads should exit nonzero, so capture the reports before interpreting the errors:

```bash
xcsh get http_loadbalancer "$XCSH_LB_NAME" -n "$XCSH_NAMESPACE" -o json \
  > lb-absence.json 2> lb-absence.err || true
xcsh get certificate "$XCSH_CERT_NAME" -n "$XCSH_NAMESPACE" -o json \
  > certificate-absence.json 2> certificate-absence.err || true
jq -e '.results[0].error.kind == "not_found"' lb-absence.json > /dev/null
jq -e '.results[0].error.kind == "not_found"' certificate-absence.json > /dev/null
```

Only named `not_found` confirms absence. If a resource still exists, allow deletion to propagate and repeat its read. Authentication and network failures do not prove deletion. Keep private ownership records until absence is verified, then follow your retention policy.
