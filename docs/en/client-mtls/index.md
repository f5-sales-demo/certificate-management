---
title: Client mTLS
description: Client mTLS certificate workflow overview and ordered tasks.
sidebar:
  label: Client mTLS
  order: 4
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
---

Authenticate callers with optional frontend client certificates and authorize synthetic writes using verified forwarded identity. Keep client CA and key material separate from the server, origin, and Wingman inputs.

## Prerequisites at a glance

An existing server certificate and Wingman deployment, Python 3, OpenSSL 3, and a separate private synthetic client CA.

## Workflow

1. [Prerequisites](./prerequisites/)
2. [Configuration](./configuration/)
3. [Configure](./configure/)
4. [Verify](./verify/)
5. [Maintain](./maintain/)
6. [Remove](./remove/)
