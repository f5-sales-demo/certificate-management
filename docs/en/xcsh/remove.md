---
title: xcsh — Remove
description: Remove for the xcsh certificate workflow.
sidebar:
  label: Remove
  order: 6
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../maintain/
  label: Maintain
next:
  link: ../
  label: Overview
---

## Remove steps

Detach dependent consumers before removing your exclusively owned certificate through xcsh. Confirm the exact resource and namespace, check `xcsh delete --help` for the current resource deletion interface, and verify named API absence. Retain private manifests for recovery. Never remove Terraform-owned or retained demonstration resources.

For infrastructure retirement, follow [Terraform Remove](../../terraform/remove/) in its independently owned state. Removing a certificate manifest does not tear down its consumers.
