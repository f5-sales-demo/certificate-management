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

First set `client_mtls.enabled = false` while retaining its trust and CRL inputs. Review and apply the listener update,
then verify policy and trust references are absent. Set `client_mtls = null` through a second reviewed plan to delete
the detached objects. XC rejects policy deletion while a listener still references it. Remove the client policy, trust
and public CRL routes while preserving the server certificate, load balancers, Wingman and Default pool additions.
Verify public reads and redirects, unchanged server fingerprints and zero-change refresh. Exercise full destroy
separately on an isolated deployment of this same configuration; never destroy the retained owner to test removal.
