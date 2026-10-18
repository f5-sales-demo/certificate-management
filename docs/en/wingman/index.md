---
title: Wingman
description: Wingman certificate workflow overview and ordered tasks.
sidebar:
  label: Overview
  order: 5
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
---

Your application can serve Hypertext Transfer Protocol Secure (HTTPS) without mounting a plaintext private key. Wingman authorizes the workload, unseals its encrypted key, and lets the application keep the decrypted material in memory. Try the [live example](https://certificate-management-terraform.f5-sales-demo.com/wingman/get), then follow the workflow in your own environment.

## Prerequisites at a glance

Tenant access, Terraform scaffolding, a Wingman-enabled vK8s workload, an application Secret Policy, and a scoped kubeconfig.

## Workflow

1. [Prerequisites](./prerequisites/)
2. [Configuration](./configuration/)
3. [Configure](./configure/)
4. [Verify](./verify/)
5. [Maintain](./maintain/)
6. [Remove](./remove/)
