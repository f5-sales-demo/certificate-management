---
title: Client mTLS — Remove
description: Remove for the Client mTLS certificate workflow.
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

Set `client_mtls = null` through a fresh reviewed plan. Remove the client policy, trust and public CRL routes while
preserving the server certificate, load balancers, Wingman and Default pool additions. Verify public reads and
redirects, unchanged server fingerprints and zero-change refresh. Exercise full destroy separately on an isolated
deployment of this same configuration; never destroy the retained owner to test removal.
