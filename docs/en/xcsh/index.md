---
title: xcsh
description: xcsh certificate workflow overview and ordered tasks.
sidebar:
  label: xcsh
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
---

Use the latest [xcsh](https://f5-sales-demo.github.io/xcsh/) with an [authenticated environment](https://f5-sales-demo.github.io/xcsh/en/f5-distributed-cloud/contexts-namespaces/), existing certificate/key inputs, and your namespace in `XCSH_NAMESPACE`. Keep keys, encrypted artifacts, and resource reports in a private directory outside Git.

For native Terraform preparation without the xcsh CLI, see the [Terraform walkthrough](../terraform/). Both retained endpoints serve the same public trust certificate; each tool owns separate resources.

## Prerequisites at a glance

An authenticated xcsh context, an existing namespace, a matching certificate/key pair, and private owner storage.

## Workflow

1. [Prerequisites](./prerequisites/)
2. [Configuration](./configuration/)
3. [Configure](./configure/)
4. [Verify](./verify/)
5. [Maintain](./maintain/)
6. [Remove](./remove/)
