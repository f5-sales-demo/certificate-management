---
title: Certificate Management
sidebar:
  order: 1
---

Manage certificates and encrypted private keys for F5 Distributed Cloud. Choose a workflow based on who owns the resource and where the key is used.

- [xcsh](./xcsh/) prepares and applies named certificate manifests through the CLI.
- [Terraform](./terraform/) owns a certificate and HTTPS service, with native key encryption.
- [Wingman](./wingman/) authorizes an application to unseal its TLS key in memory.
- [Certificate types](./terraform/certificate-surfaces/) covers inline TLS, origin authentication, interception, and workload configurations.

Use **Customize examples** to supply tenant settings and literal paths to local files. Matching fields carry across guides. Credentials remain in the tab session; leave them empty to use your shell environment or a private prompt. Reset restores noncredential defaults; Clear credentials removes tokens and passphrases.

Keep keys, state, plans, and rollback material in private owner storage. Each tool must own separate resource names. The public endpoint certificate, Wingman application chain, and origin trust CA are separate inputs. [Qualification records](../assets/current-artifacts.json) report observed artifacts and results; they do not replace verification of your deployment.
