---
title: Certificate Management
sidebar:
  order: 1
---

Prepare and encrypt certificate keys for F5 Distributed Cloud with independently owned resources.

- [Terraform](./terraform/) deploys a certificate and HTTPS endpoint using native provider Blindfold preparation, without installing xcsh.
- [xcsh](./xcsh/) prepares certificate manifests and reconciles certificate resources through the CLI.

Both retained demonstrations use the same [public certificate](../assets/certificate-management.pem). Private keys, rollback material, credentials, and Terraform state remain in private owner storage.
