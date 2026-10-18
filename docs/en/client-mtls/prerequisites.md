---
title: Client mTLS — Prerequisites
description: Prerequisites for the Client mTLS certificate workflow.
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

Complete the [server certificate workflow](../../terraform/) and [Wingman runtime](../../wingman/). Use the existing
named-certificate owner state and Wingman pool. [Origin mTLS](../../terraform/certificate-surfaces/origin-mtls/)
authenticates the load balancer to an origin; client mTLS authenticates a caller to the frontend. Keep their material
distinct.

The retained Regional Edge endpoint uses optional client authentication with `no_crl`. Live XC validation rejects CRLs
on Regional Edges. Edge CRL revocation is excluded from this workflow. Signed CRLs remain public downloadable lifecycle
material; downloading one does not revoke a client at the edge.

Use Python 3 and OpenSSL 3 on Ubuntu or macOS. Store the synthetic CA database, CA key, client keys and plans in an
owner-only directory outside Git. Only public CA certificates and signed PEM CRLs enter Terraform state. Select client
file paths produced below; never reuse server, origin or Wingman key inputs.
