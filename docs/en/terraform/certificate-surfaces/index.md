---
title: Certificate types
sidebar:
  label: Choose configuration
  order: 3
---

Choose a configuration based on the TLS endpoint and resource owner. Every supported example includes complete HCL, resulting public JSON, commands, and expected results. Use the [named certificate workflow](../) for the primary HTTPS deployment.

## Supported configurations

- [Advertise TLS](./advertise-tls/)
- [CDN origin mTLS](./cdn-origin-mtls/)
- [CDN server TLS](./cdn-server-tls/)
- [Cluster TLS](./cluster-tls/)
- [Default pool mTLS](./http-origin-mtls/)
- [Inline server TLS](./inline-server-tls/)
- [Origin mTLS](./origin-mtls/)
- [TLS interception](./proxy-intercept/)
- [Proxy TLS](./proxy-tls/)
- [Secret access TLS](./secret-access-tls/)
- [TCP TLS](./tcp-tls/)
- [Virtual host TLS](./virtual-host-tls/)
- [Custom workload TLS](./workload-service-custom/)
- [Multiport workload TLS](./workload-service-public-multi/)
- [Workload TLS](./workload-service-public-single/)

## Qualification limits

The provider has 25 certificate nodes across 14 resource types. Sixteen support encrypted configuration lifecycles in the documented environment. Configuration readback, stable plans, and cleanup are separate from served TLS. Use [dated qualification records](../../../assets/certificate-administration-qualification.json) for observed status; verify your own deployment with the installed artifacts.

| Certificate node | Schema validation | Live lifecycle | Served TLS | Example and prerequisite or restriction |
| --- | --- | --- | --- | --- |
| `xcsh_advertise_policy.tls_parameters.common_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](./advertise-tls/) Concrete consumer/advertisement required for serving. |
| `xcsh_bigip_http_proxy.proxy_config.https.tls_parameters.tls_certificates` | Passed | Unqualified | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/bigip-server-tls) Tenant API returns HTTP 501 Not Implemented |
| `xcsh_cdn_loadbalancer.https.tls_cert_options.tls_inline_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](./cdn-server-tls/) Concrete consumer/advertisement required for serving. |
| `xcsh_cdn_loadbalancer.origin_pool.use_tls.use_mtls.tls_certificates` | Passed | Passed | Unqualified | [HCL](./cdn-origin-mtls/) Existing origin with client authentication and trusted server chain. |
| `xcsh_certificate` | Passed | Passed | Passed | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/named-certificate) Existing namespace and tenant-managed hostname. |
| `xcsh_cluster.tls_parameters.common_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](./cluster-tls/) Concrete consumer/advertisement required for serving. |
| `xcsh_http_loadbalancer.default_pool.use_tls.use_mtls.tls_certificates` | Passed | Passed | Unqualified | [HCL](./http-origin-mtls/) Existing origin with client authentication and trusted server chain. |
| `xcsh_http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Passed | Passed | [HCL](./inline-server-tls/) Existing namespace and tenant-managed hostname. |
| `xcsh_network_connector.enable_forward_proxy.tls_intercept.custom_certificate` | Passed | Failed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/connector-intercept) API accepts system object but drops interception TLS configuration |
| `xcsh_nfv_service.https_management.advertise_on_sli_vip.tls_certificates` | Passed | Unqualified | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/nfv-advertise_on_sli_vip) Isolated NFV service and managed cloud appliance prerequisites unavailable |
| `xcsh_nfv_service.https_management.advertise_on_slo_internet_vip.tls_certificates` | Passed | Unqualified | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/nfv-advertise_on_slo_internet_vip) Isolated NFV service and managed cloud appliance prerequisites unavailable |
| `xcsh_nfv_service.https_management.advertise_on_slo_sli.tls_certificates` | Passed | Unqualified | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/nfv-advertise_on_slo_sli) Isolated NFV service and managed cloud appliance prerequisites unavailable |
| `xcsh_nfv_service.https_management.advertise_on_slo_vip.tls_certificates` | Passed | Unqualified | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/nfv-advertise_on_slo_vip) Isolated NFV service and managed cloud appliance prerequisites unavailable |
| `xcsh_origin_pool.use_tls.use_mtls.tls_certificates` | Passed | Passed | Passed | [HCL](./origin-mtls/) Existing origin with client authentication and trusted server chain. |
| `xcsh_proxy.dynamic_proxy.https_proxy.tls_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](./proxy-tls/) Concrete consumer/advertisement required for serving. |
| `xcsh_proxy.tls_intercept.custom_certificate` | Passed | Passed | Unqualified | [HCL](./proxy-intercept/) Forward proxy route and client CA trust. |
| `xcsh_secret_management_access.access_info.tls_config.common_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](./secret-access-tls/) Concrete consumer/advertisement required for serving. |
| `xcsh_tcp_loadbalancer.tls_tcp.tls_parameters.tls_certificates` | Passed | Passed | Unqualified | [HCL](./tcp-tls/) Concrete consumer/advertisement required for serving. |
| `xcsh_virtual_host.tls_parameters.common_params.tls_certificates` | Passed | Passed | Unqualified | [HCL](./virtual-host-tls/) Concrete consumer/advertisement required for serving. |
| `xcsh_workload.service.advertise_options.advertise_custom.ports.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Passed | Unqualified | [HCL](./workload-service-custom/) Existing CE virtual site and workload capacity. |
| `xcsh_workload.service.advertise_options.advertise_on_public.multi_ports.ports.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Passed | Unqualified | [HCL](./workload-service-public-multi/) Existing CE virtual site and workload capacity. |
| `xcsh_workload.service.advertise_options.advertise_on_public.port.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Passed | Unqualified | [HCL](./workload-service-public-single/) Existing CE virtual site and workload capacity. |
| `xcsh_workload.stateful_service.advertise_options.advertise_custom.ports.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Failed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/workload-stateful_service-custom) Current API returns HTTP 500; the HTTP-only control also fails |
| `xcsh_workload.stateful_service.advertise_options.advertise_on_public.multi_ports.ports.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Failed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/workload-stateful_service-public-multi) Current API returns HTTP 500; the HTTP-only control also fails |
| `xcsh_workload.stateful_service.advertise_options.advertise_on_public.port.http_loadbalancer.https.tls_parameters.tls_certificates` | Passed | Failed | Unqualified | [HCL](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference/workload-stateful_service-public-single) Current API returns HTTP 500; the HTTP-only control also fails |

## Restricted reference fragments

Files under [`terraform/reference`](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/reference) end in `.tf.example`. They illustrate schema paths and are excluded from normal `terraform apply` discovery. Review them against the installed schema; do not deploy them into the retained shared namespace.

- BIG-IP HTTP proxy returned HTTP **501 Not Implemented** in the tenant.
- Stateful workloads’ public single-port, public multi-port, and custom advertisement paths were **rejected by the API**.
- Network function virtualization (NFV) certificates need a separately managed appliance and isolated site. All four nodes remain unqualified live.
- Network connectors require the **`system` namespace**. Current certificate-specific readback shows that the API accepts the object but drops interception TLS settings, so the current provider fails the write when encrypted readback is missing. The path remains restricted even there.

These limitations and unqualified served paths remain explicit even when schema validation passes. Review provider [#2539](https://github.com/f5-sales-demo/terraform-provider-xcsh/issues/2539) for tracked acceptance restrictions before selecting these configurations.
