---
title: Client mTLS — Configuration
description: Configuration for the Client mTLS certificate workflow.
sidebar:
  label: Configuration
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../prerequisites/
  label: Prerequisites
next:
  link: ../configure/
  label: Configure
---

Client mTLS is disabled when `client_mtls = null`. The complete HCL retains the named server certificate and existing
routes. The public JSON describes the added resources and TLS extension; encoded-material placeholders are illustrative.

[Download public JSON](../../../assets/configurations/client-mtls.json).

## Public JSON

<div data-xcsh-context="json" data-xcsh-fields="XCSH_LB_NAME XCSH_NAMESPACE">

```json
{
  "trusted_ca_list": {
    "metadata": {
      "name": "<XCSH_LB_NAME>-client-ca",
      "namespace": "<XCSH_NAMESPACE>"
    },
    "spec": {
      "trusted_ca_url": "string:///<BASE64_CLIENT_CA_BUNDLE>"
    }
  },
  "service_policy": {
    "metadata": {
      "name": "<XCSH_LB_NAME>-client-write",
      "namespace": "<XCSH_NAMESPACE>"
    },
    "spec": {
      "any_server": {},
      "rule_list": {
        "rules": [
          {
            "metadata": {
              "name": "deny-write-without-client-identity"
            },
            "spec": {
              "action": "DENY",
              "any_client": {},
              "http_method": {
                "methods": ["POST", "PUT", "PATCH"]
              },
              "path": {
                "exact_values": ["/mtls/write"]
              },
              "headers": [
                {
                  "name": "X-Forwarded-Client-Cert",
                  "check_not_present": {},
                  "invert_matcher": false
                }
              ],
              "waf_action": {
                "none": {}
              }
            }
          },
          {
            "metadata": {
              "name": "allow-other-traffic"
            },
            "spec": {
              "action": "ALLOW",
              "any_client": {},
              "waf_action": {
                "none": {}
              }
            }
          }
        ]
      }
    }
  },
  "https_tls_cert_params_extension": {
    "use_mtls": {
      "trusted_ca": {
        "name": "<XCSH_LB_NAME>-client-ca",
        "namespace": "<XCSH_NAMESPACE>"
      },
      "client_certificate_optional": true,
      "no_crl": {},
      "xfcc_options": {
        "xfcc_header_elements": ["XFCC_CERT", "XFCC_CHAIN"]
      }
    }
  }
}
```

</div>

<div data-xcsh-context="hcl" data-xcsh-fields="XCSH_API_TOKEN XCSH_API_URL">

## Shared Terraform source

The complete shared HCL appears once in [Terraform Configuration](../../terraform/configuration/). Download that root unchanged; client mTLS is its optional frontend extension.

</div>

The retained owner already has its Wingman contract and Default pool module dependencies. For an isolated deployment,
download the same dependencies listed in [Terraform Configure](../../terraform/configure/) before initializing.
