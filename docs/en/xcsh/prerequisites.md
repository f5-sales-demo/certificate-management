---
title: xcsh — Prerequisites
description: Prerequisites for the xcsh certificate workflow.
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

Use Customize examples to select `<XCSH_WORKDIR>`, certificate paths, namespace, and an exclusively owned certificate name. Paths are literal absolute paths outside Git; the form accepts paths, never key or bundle contents. Authenticate xcsh through its existing context before these commands; the form does not switch that context. Keep this working directory separate from Terraform state.
