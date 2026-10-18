---
title: Terraform — Prerequisites
description: Prerequisites for the Terraform certificate workflow.
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

Install the current published Terraform and
**`f5-sales-demo/xcsh` provider** artifacts. The provider supports Terraform 1.11 or later for write-only inputs.
See the [current qualification receipt](../../../assets/current-artifacts.json) for resolved versions, digests, source commits, and the status of live gates. Provide an existing namespace, certificate permissions, load-balancer capacity, and a hostname in a tenant-managed
DNS zone. Terraform reads the namespace as a data source and never owns it.

Set `<XCSH_API_URL>` to your tenant console URL and supply a session credential. These are **provider environment settings**, independent of the xcsh command-line interface (CLI).

Keep credentials out of HashiCorp Configuration Language (HCL), variable files, and plans. Leave credentials blank in Customize examples to use shell environment values or a private prompt. Entered credentials appear in displayed/copied shell commands; avoid recording them in shell history:

[HCL source](https://github.com/f5-sales-demo/certificate-management/tree/main/terraform/named-certificate) is authoritative. Use a dedicated private working directory and state for each example. Review the [certificate surfaces](.././certificate-surfaces/) before selecting a prerequisite-bound configuration.
