---
title: Certificate surfaces
description: Evidence and prerequisites for all 25 certificate nodes across 14 provider resource types.
sidebar:
  order: 3
---

The native provider exposes **25 certificate nodes across 14 resource types**. Schema and serialization coverage applies to all nodes. Live
configuration lifecycle means create, encrypted full API readback, repeat plans, metadata/material updates, and cleanup passed for the recorded
artifact. Actual Transport Layer Security (TLS) serving requires independent trust, hostname, fingerprint, and traffic checks. These gates are
separate.

## Qualification matrix

The [machine matrix](../../../assets/terraform-certificate-matrix.json) separates dated historical lifecycle evidence from the [current qualification](../../../assets/current-artifacts.json). Historical receipts remain unchanged. Current schema validation proves configuration compatibility; encrypted API readback and served TLS require separate live evidence.

| Certificate node | Schema validation | Live lifecycle | Served TLS | Example and prerequisite or restriction |
| --- | --- | --- | --- | --- |
| `xcsh_advertise_policy.tls_parameters.common_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/advertise-tls) Concrete consumer/advertisement required for serving. |
| `xcsh_bigip_http_proxy.proxy_config.https.tls_parameters.tls_certificates` | Passed | Unqualified | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/bigip-server-tls) Sales Demo API returns HTTP 501 Not Implemented |
| `xcsh_cdn_loadbalancer.https.tls_cert_options.tls_inline_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/cdn-server-tls) Concrete consumer/advertisement required for serving. |
| `xcsh_cdn_loadbalancer.origin_pool.use_tls.use_mtls.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/cdn-origin-mtls) Existing origin with client authentication and trusted server chain. |
| `xcsh_certificate` | Passed | Passed | Passed | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/named-certificate) Existing namespace and tenant-managed hostname. |
| `xcsh_cluster.tls_parameters.common_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/cluster-tls) Concrete consumer/advertisement required for serving. |
| `xcsh_http_loadbalancer.default_pool.use_tls.use_mtls.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/http-origin-mtls) Existing origin with client authentication and trusted server chain. |
| `xcsh_http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Passed | Passed | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/inline-server-tls) Existing namespace and tenant-managed hostname. |
| `xcsh_network_connector.enable_forward_proxy.tls_intercept.custom_certificate` | Passed | Unqualified | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/connector-intercept) API accepts system object but drops interception TLS configuration |
| `xcsh_nfv_service.https_management.advertise_on_sli_vip.tls_certificates` | Passed | Unqualified | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/nfv-advertise_on_sli_vip) Isolated NFV service and managed cloud appliance prerequisites unavailable |
| `xcsh_nfv_service.https_management.advertise_on_slo_internet_vip.tls_certificates` | Passed | Unqualified | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/nfv-advertise_on_slo_internet_vip) Isolated NFV service and managed cloud appliance prerequisites unavailable |
| `xcsh_nfv_service.https_management.advertise_on_slo_sli.tls_certificates` | Passed | Unqualified | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/nfv-advertise_on_slo_sli) Isolated NFV service and managed cloud appliance prerequisites unavailable |
| `xcsh_nfv_service.https_management.advertise_on_slo_vip.tls_certificates` | Passed | Unqualified | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/nfv-advertise_on_slo_vip) Isolated NFV service and managed cloud appliance prerequisites unavailable |
| `xcsh_origin_pool.use_tls.use_mtls.tls_certificates` | Passed | Passed | Passed | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/origin-mtls) Existing origin with client authentication and trusted server chain. |
| `xcsh_proxy.dynamic_proxy.https_proxy.tls_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/proxy-tls) Concrete consumer/advertisement required for serving. |
| `xcsh_proxy.tls_intercept.custom_certificate` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/proxy-intercept) Forward proxy route and client CA trust. |
| `xcsh_secret_management_access.access_info.tls_config.common_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/secret-access-tls) Concrete consumer/advertisement required for serving. |
| `xcsh_tcp_loadbalancer.tls_tcp.tls_parameters.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/tcp-tls) Concrete consumer/advertisement required for serving. |
| `xcsh_virtual_host.tls_parameters.common_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/virtual-host-tls) Concrete consumer/advertisement required for serving. |
| `xcsh_workload.service.advertise_options.advertise_custom.ports.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/workload-service-custom) Existing CE virtual site and workload capacity. |
| `xcsh_workload.service.advertise_options.advertise_on_public.multi_ports.ports.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/workload-service-public-multi) Existing CE virtual site and workload capacity. |
| `xcsh_workload.service.advertise_options.advertise_on_public.port.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Passed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/workload-service-public-single) Existing CE virtual site and workload capacity. |
| `xcsh_workload.stateful_service.advertise_options.advertise_custom.ports.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Failed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/workload-stateful_service-custom) Current API returns HTTP 500; the HTTP-only control also fails |
| `xcsh_workload.stateful_service.advertise_options.advertise_on_public.multi_ports.ports.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Failed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/workload-stateful_service-public-multi) Current API returns HTTP 500; the HTTP-only control also fails |
| `xcsh_workload.stateful_service.advertise_options.advertise_on_public.port.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Failed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/workload-stateful_service-public-single) Current API returns HTTP 500; the HTTP-only control also fails |

## Choose an example

Each directory is independent: copy its `.tf` files into a separate private working directory, supply the variables declared by that example, run `terraform init -upgrade` with the current published provider, and review a saved plan. Do not combine configurations in one state or reuse an existing owned name. The namespace is a data source in every example.

[Named certificate](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/named-certificate) is the principal runnable
deployment with built-in JSON and an HTTP DNS companion. [Inline server
TLS](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/inline-server-tls) accepts stable-ID lists; it advertises HTTPS but
does not manage DNS. Supply an existing hostname route for serving.

Origin mutual TLS (mTLS) examples require a reachable server that requests client authentication, a client certificate with `clientAuth` usage, and
the origin’s public trust CA. They verify the origin using `origin_ca_file`; they do not disable server verification. The shared showcase server
certificate has only `serverAuth`, so it is not the mTLS client input. CDN examples also require an origin even when only server TLS is under test.

Cluster, advertise-policy, proxy, secret-access, TCP, and virtual-host examples prepare encrypted configuration without automatically creating a
concrete traffic consumer. Service-workload examples require an existing customer-edge (CE) virtual site with workload capacity and an available
container image. A configuration lifecycle pass with an empty qualification selector does not establish running workload traffic.

## Map prerequisite values

The form uses `<XCSH_NAMESPACE>`, `<XCSH_LB_NAME>`, and `<XCSH_DOMAINNAME>` for deployment settings. The named-certificate configuration uses the same `var.name` for its certificate and HTTPS load balancer; `<XCSH_CERT_NAME>` belongs to the separately owned xcsh certificate. `<XCSH_DNS_ZONE>` identifies your prerequisite zone; the named example manages a hostname association and has no zone variable.

Export the existing native variables for the configuration you choose. Each configuration ignores variables it does not declare. Create a separate directory and state for each configuration; never copy several configurations into one directory.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_NAMESPACE XCSH_LB_NAME XCSH_DOMAINNAME XCSH_CERT_FILE XCSH_KEY_FILE XCSH_ORIGIN_HOSTNAME XCSH_ORIGIN_CA_FILE XCSH_VIRTUAL_SITE_NAME XCSH_VIRTUAL_SITE_NAMESPACE XCSH_CONTAINER_IMAGE">

```bash
export TF_VAR_namespace="$XCSH_NAMESPACE"
export TF_VAR_name="$XCSH_LB_NAME"
export TF_VAR_domain="$XCSH_DOMAINNAME"
export TF_VAR_certificate_file="$XCSH_CERT_FILE"
export TF_VAR_private_key_file="$XCSH_KEY_FILE"
export TF_VAR_origin_hostname="$XCSH_ORIGIN_HOSTNAME"
export TF_VAR_origin_ca_file="$XCSH_ORIGIN_CA_FILE"
export TF_VAR_virtual_site_name="$XCSH_VIRTUAL_SITE_NAME"
export TF_VAR_virtual_site_namespace="$XCSH_VIRTUAL_SITE_NAMESPACE"
export TF_VAR_image="$XCSH_CONTAINER_IMAGE"
```

</div>

For the standalone origin-pool configuration, map the origin-pool name to its existing `name` variable:

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_ORIGIN_POOL_NAME">

```bash
export TF_VAR_name="$XCSH_ORIGIN_POOL_NAME"
```

</div>

For `inline-server-tls`, construct the list using JSON encoding rather than shell interpolation into JSON. IDs stay attached to their logical certificate; native provider resource labels remain fixed.

<div data-xcsh-context="shell" data-xcsh-fields="XCSH_CERT_ID XCSH_CERT_FILE XCSH_KEY_FILE">

```bash
TF_VAR_certificates="$(python3 -c 'import json,os; print(json.dumps([{"id":os.environ["XCSH_CERT_ID"],"certificate_file":os.environ["XCSH_CERT_FILE"],"private_key_file":os.environ["XCSH_KEY_FILE"]}]))')"
export TF_VAR_certificates
```

</div>

## Restricted reference fragments

Files under [`terraform/reference`](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference) end in `.tf.example`. They illustrate schema paths and are excluded from normal `terraform apply` discovery. Review them against the installed schema; do not deploy them into the retained shared namespace.

- BIG-IP HTTP proxy returned HTTP **501 Not Implemented** in the demo tenant.
- Stateful workloads’ public single-port, public multi-port, and custom advertisement paths were **rejected by the API**.
- Network function virtualization (NFV) certificates need a separately managed appliance and isolated site. All four nodes remain unqualified live.
- Network connectors require the **`system` namespace**. Current certificate-specific readback shows that the API accepts the object but drops interception TLS settings, so the encrypted lifecycle remains unqualified even there.

These limitations and unqualified served paths remain explicit even when schema validation passes. Provider [#2539](https://github.com/f5-sales-demo/terraform-provider-xcsh/issues/2539) scheduled acceptance failures are outside this documentation’s claims.

## Current qualification

The current artifact receipt links two-platform schema validation and all 16 supported encrypted lifecycles.
Named and inline HTTPS and named-origin mutual TLS have separate served traffic receipts. Generic HTTP
acceptance does not qualify a certificate path. The API drops the tested connector certificate settings.
Stateful advertisement attempts return HTTP 500, including a control without TLS; these remain failed tests.
BIG-IP proxy reads return HTTP 501. NFV paths remain reference fragments because no isolated managed-appliance
and site inputs were supplied in the authorized target namespace. These nine restrictions remain explicit in
the current matrix.
