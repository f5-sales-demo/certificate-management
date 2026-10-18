---
title: Wingman — Prerequisites
description: Prerequisites for the Wingman certificate workflow.
sidebar:
  label: Prerequisites
  order: 1
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../
  label: Overview
next:
  link: ../configuration/
  label: Configuration
---

## Prerequisites steps

You need F5 Distributed Cloud tenant
access, a namespace with a Wingman-enabled virtual Kubernetes (vK8s) workload, an
application-specific Secret Policy, xcsh, kubectl, jq, and matching Transport Layer Security (TLS)
certificate/key files in private storage. Supply an explicit scoped kubeconfig and context. Use
**Customize examples** to set your namespace, Wingman naming base, hostname, application
image, and file paths; matching fields carry across the other certificate guides.

The [infrastructure runbook](.././validation/) provisions this example's supporting policy, cluster, application, and disposable checks through Terraform plans. Complete it once if you need a working environment. Its ownership and teardown commands are operator support for this walkthrough. The steps below use that environment to demonstrate key preparation and application behavior.

Follow F5's [Wingman how-to](https://docs.cloud.f5.com/docs-v2/multi-cloud-network-connect/how-tos/secret-mgmt/pp-secrets-using-wingman) for the platform setup and its [API reference](https://docs.cloud.f5.com/docs-v2/platform/reference/wingman-api-reference) for protocol details.
