---
title: Certificate Management
sidebar:
  order: 1
---

Prepare and encrypt certificate keys for F5 Distributed Cloud with independently owned resources.

Use Customize examples to select your tenant, application, certificate paths, and prerequisites. Noncredential edits follow matching fields across these workflows and other F5 guides, including CSD. Each field is independent; hostnames and paths are never inferred. Unknown paths and site identities remain visible placeholders until you supply them.

Credentials stay in this tab's session. Leave them empty to use shell environment values or private prompts. Reset shared values restores noncredential defaults; Clear credentials removes tokens and passphrases. Enter only paths for private files. Published HCL, scripts, public certificates, and historical evidence remain canonical downloads.

- [Terraform](./terraform/) deploys a certificate and HTTPS endpoint using native provider Blindfold preparation, without installing xcsh.
- [Wingman](./wingman/) shows how an application authorizes and unseals its TLS key through the injected sidecar, with a live HTTPS example.
- [xcsh](./xcsh/) prepares certificate manifests and reconciles certificate resources through the CLI.

The retained Terraform and xcsh endpoints use the same [public load-balancer certificate](../assets/certificate-management.pem). Wingman serves behind the Terraform endpoint with a separate [application certificate chain](../assets/wingman-certificate.pem). Private keys, rollback material, credentials, and Terraform state remain in private owner storage.
