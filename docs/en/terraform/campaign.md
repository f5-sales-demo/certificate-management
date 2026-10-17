---
title: Traffic qualification
sidebar:
  order: 5
---

The [campaign](https://github.com/f5-sales-demo/certificate-management/issues/93) extends the existing named-certificate, Wingman bootstrap, and Wingman runtime deployments. GitHub Pages serves this documentation. Successful infrastructure stays deployed. Temporary probes and an isolated teardown deployment are removed through reviewed Terraform plans.

Default pool mTLS is first. Its [case issue](https://github.com/f5-sales-demo/certificate-management/issues/94) requires the origin to report the client certificate F5 presents, including after renewal. The optional deployment below provides the missing route and backend. Implementation and schema checks do not qualify live traffic.

| Order | Configuration | Current traffic status |
| --- | --- | --- |
| 1 | Default pool mTLS | Pending live deployment and qualification |
| 2 | TCP TLS | Pending the published first result |
| 3 | CDN server TLS | Pending |
| 4 | CDN origin mTLS | Pending |
| 5 | Advertise TLS | Pending |
| 6 | Virtual host TLS | Pending |
| 7 | Cluster TLS | Pending |
| 8 | Proxy TLS | Pending |
| 9 | TLS interception | Pending |
| 10 | Secret access TLS | Pending |
| 11 | Workload TLS | Pending |
| 12 | Multiport workload TLS | Pending |
| 13 | Custom workload TLS | Pending |

Named certificate, inline server TLS, and origin mTLS remain regression controls. Preserve historical receipts. Publish each dated result and finish its cleanup, merged CI, and published-reader checks before testing the next case.

## Default pool dependencies

Deploy the optional certificate capability from [origin-server](https://github.com/f5-sales-demo/origin-server/issues/766)
on a dedicated Azure origin with a separate private state. Use its exported Azure hostname and mTLS port.
The origin requires a server certificate for that hostname and a public CA trusting the F5 client's
`clientAuth` certificate. Its managed identity retrieves write-only Key Vault material; this serving path
requires no Customer Edge, RE vK8s, or additional application container.

The existing Wingman deployment remains a regression control. Its bootstrap and runtime states continue
owning their existing resources. They do not own this Azure origin.

The named-certificate owner imports the canonical [Default pool configuration](../certificate-surfaces/http-origin-mtls/)
through `module.certificate_use_cases`. Its HTTPS listener serves a distinct downstream certificate; a managed HTTP companion owns the new DNS
association in the tenant zone. The certificate under test authenticates the upstream TLS connection.

[Named-certificate commands](../) download the canonical module dependency. The optional map defaults to empty.
Prepare private client material before planning, then add this input to the existing owner root, replacing
the example paths and hostnames with verified deployment values:

```hcl
certificate_use_cases = {
  default-pool-mtls = {
    enabled = true
    name = "certificate-default-pool"
    hostname = "certificate-default-pool.example.com"
    certificate_file = "/private/certificate-campaign/client.pem"
    private_key_file = "/private/certificate-campaign/client.key"
    origin_hostname = "unique-certificate-origin.eastus2.cloudapp.azure.com"
    origin_ca_file = "/private/certificate-campaign/server-ca.pem"
    origin_port = 18443
    frontend_tls = {
      certificate_file = "/private/certificate-campaign/frontend.pem"
      private_key_file = "/private/certificate-campaign/frontend.key"
    }
  }
}
```

## Review and apply

Apply the origin-server plan, verify its origin prerequisites, then apply the named-certificate plan. Run these commands on Ubuntu in each owner directory with its private provider environment. Review the complete plan and reject unrelated changes, replacement of retained identities, or changes to existing endpoints. Keep plans and readbacks in private storage.

```bash
terraform init -upgrade
terraform validate
terraform plan -out=case.plan
terraform show case.plan
shasum -a 256 case.plan
terraform apply case.plan
terraform plan -out=followup.plan -detailed-exitcode
```

Require exit `0` for the refresh-enabled follow-up plan. Read `certificate_use_case_inventory` to identify the certificate role, logical ID, resource address, URL, and dependencies. Read back the complete API object privately and compare that exact certificate node, public chain, encrypted location, and stable identity.

## Traffic and renewal

Send a unique request to the public F5 listener without a client certificate on your laptop:

```bash
challenge="$(openssl rand -hex 16)"
curl --silent --show-error --fail \
  --cacert /private/certificate-campaign/frontend-ca.pem \
  "https://certificate-default-pool.example.com/get?challenge=$challenge"
openssl x509 -in /private/certificate-campaign/client.pem -noout -fingerprint -sha256
```

Require HTTP `200`, `example: certificate-origin`, the exact challenge, and `client_certificate_sha256` matching the configured client's SHA-256 fingerprint. The JSON fingerprint has lowercase hexadecimal without colons. The backend accepts only clients chaining to its configured public CA. A direct laptop handshake does not establish F5-originated mTLS.

Through separate saved plans, set `send_client_certificate = false` to test a missing client, supply untrusted client files, change the origin CA to test wrong trust, and set `origin_sni` to test a wrong TLS hostname.
Restore the healthy configuration through another reviewed plan. Renew only this case's client material while
preserving logical ID `server`, names, resource addresses, and the backend server material. Require the new
backend-observed client fingerprint and response, unchanged identities, and an empty follow-up plan. Run
reachable traffic checks on Ubuntu and macOS.

Create temporary probes through Terraform and remove them through reviewed plans. Confirm typed absence twice and revoke the scoped kubeconfig. Scan private state, every decoded saved-plan archive member, logs, and public evidence for plaintext keys and credentials. Run complete teardown against an isolated deployment of these same configurations; retain the documentation environment.

Missing configured capacity, runtime support, network access, or site references remain precise prerequisite-unavailable outcomes. A failed case restores the previous healthy configuration and removes only its unsuccessful additions. Shared changes require every affected regression control to pass.
