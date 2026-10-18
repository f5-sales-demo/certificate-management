---
title: Wingman — Configuration
description: Configuration for the Wingman certificate workflow.
sidebar:
  label: Configuration
  order: 2
tableOfContents:
  minHeadingLevel: 2
  maxHeadingLevel: 3
prev:
  link: ../prerequisites/
  label: Prerequisites
next:
  link: ../configure/
  label: Configure
---

Set `XCSH_APPLICATION_CERT_FILE` to the application leaf-first chain, `XCSH_CERT_FILE` to public endpoint trust, and `XCSH_ORIGIN_CA_FILE` to origin root trust. Use the governed latest image or an immutable digest.
Terraform resolves the selection to a verified immutable image during planning; inspect that digest before applying the saved plan. The runtime ConfigMap contains only the public chain and encrypted locations.
Terraform creates it before this Deployment; do not apply this JSON separately to a Terraform-owned resource.

## Public Deployment JSON

<div data-xcsh-context="json" data-xcsh-fields="XCSH_DOMAINNAME XCSH_NAMESPACE XCSH_WINGMAN_NAME">

```json
{
  "apiVersion": "apps/v1",
  "kind": "Deployment",
  "metadata": {
    "name": "<XCSH_WINGMAN_NAME>-wingman",
    "namespace": "<XCSH_NAMESPACE>",
    "labels": {
      "app": "<XCSH_WINGMAN_NAME>-wingman"
    }
  },
  "spec": {
    "replicas": 1,
    "selector": {
      "matchLabels": {
        "app": "<XCSH_WINGMAN_NAME>-wingman"
      }
    },
    "template": {
      "metadata": {
        "labels": {
          "app": "<XCSH_WINGMAN_NAME>-wingman"
        },
        "annotations": {
          "ves.io/wingman-injection-mode": "enable",
          "certificate-management/material-sha256": "<MATERIAL_SHA256>"
        }
      },
      "spec": {
        "containers": [
          {
            "name": "application",
            "image": "ghcr.io/f5-sales-demo/certificate-management-wingman@sha256:<RESOLVED_IMAGE_DIGEST>",
            "imagePullPolicy": "Always",
            "ports": [
              {
                "name": "https",
                "containerPort": 8443
              }
            ],
            "env": [
              {
                "name": "TLS_HOSTNAME",
                "value": "<XCSH_DOMAINNAME>"
              }
            ],
            "resources": {
              "requests": {
                "cpu": "50m",
                "memory": "32Mi"
              },
              "limits": {
                "cpu": "250m",
                "memory": "128Mi"
              }
            },
            "securityContext": {
              "runAsNonRoot": true,
              "allowPrivilegeEscalation": false,
              "readOnlyRootFilesystem": true,
              "capabilities": {
                "drop": ["ALL"]
              }
            },
            "volumeMounts": [
              {
                "name": "material",
                "mountPath": "/material",
                "readOnly": true
              }
            ],
            "startupProbe": {
              "httpGet": {
                "path": "/readyz",
                "port": "https",
                "scheme": "HTTPS"
              },
              "periodSeconds": 5,
              "timeoutSeconds": 6,
              "failureThreshold": 30
            },
            "livenessProbe": {
              "tcpSocket": {
                "port": "https"
              },
              "periodSeconds": 10,
              "failureThreshold": 3
            },
            "readinessProbe": {
              "httpGet": {
                "path": "/readyz",
                "port": "https",
                "scheme": "HTTPS"
              },
              "periodSeconds": 5,
              "timeoutSeconds": 6
            }
          }
        ],
        "volumes": [
          {
            "name": "material",
            "configMap": {
              "name": "<XCSH_WINGMAN_NAME>-wingman-material"
            }
          }
        ]
      }
    }
  }
}
```

</div>

[Download public Deployment JSON](../../../assets/configurations/wingman-deployment.json).

## Blindfold request

<div data-xcsh-context="json" data-xcsh-fields="">

```json
{"type":"blindfold","location":"<ENCRYPTED_LOCATION>"}
```

</div>

<!-- generated-wingman-hcl -->

## Bootstrap HCL

Download unchanged files: [main.tf](../../../_data/wingman/bootstrap/main.tf) · [versions.tf](../../../_data/wingman/bootstrap/versions.tf).

<div data-xcsh-context="hcl" data-xcsh-fields="">

```hcl
locals {
  contract  = jsondecode(file("${path.module}/../contract.json"))
  namespace = var.namespace == null ? local.contract.namespace : var.namespace
  base_name = var.name == null ? local.contract.base_name : var.name
  names     = { for key, suffix in local.contract.suffixes : key => "${local.base_name}${suffix}" }
}
variable "namespace" {
  type        = string
  default     = null
  description = "Existing namespace; this state never owns it."
}
variable "name" {
  type        = string
  default     = null
  description = "Naming base shared with runtime and the existing Terraform owner."
}
variable "site_selector" {
  type        = string
  default     = null
  description = "Existing Toronto RE label. Verify exactly one selected site and effective quota before applying."
}
data "xcsh_namespace" "existing" {
  name = local.namespace
}
resource "xcsh_secret_policy" "application" {
  name                  = local.names.policy
  namespace             = data.xcsh_namespace.existing.name
  description           = "Wingman application TLS authorization"
  allow_f5xc            = true
  decrypt_cache_timeout = "30s"
  rules = [
    {
      name            = "allow-application"
      action          = "ALLOW"
      client_selector = ["${local.contract.app_label}=${local.names.application}"]
    },
    { name = "deny-all", action = "DENY" }
  ]
}
resource "xcsh_virtual_site" "toronto" {
  name      = local.names.virtual_site
  namespace = data.xcsh_namespace.existing.name
  site_type = "REGIONAL_EDGE"
  site_selector {
    expressions = [var.site_selector == null ? local.contract.site_selector : var.site_selector]
  }
}
resource "xcsh_virtual_k8s" "application" {
  name      = local.names.virtual_k8s
  namespace = data.xcsh_namespace.existing.name
  vsite_refs {
    name      = xcsh_virtual_site.toronto.name
    namespace = data.xcsh_namespace.existing.name
  }
}
output "runtime_contract" {
  value = {
    namespace = local.namespace
    name      = local.base_name
    policy    = "${local.namespace}/${xcsh_secret_policy.application.name}"
    vk8s      = xcsh_virtual_k8s.application.name
  }
}

output "vk8s_name" {
  value = xcsh_virtual_k8s.application.name
}
output "policy" {
  value = "${local.namespace}/${xcsh_secret_policy.application.name}"
}
terraform {
  required_version = null
  required_providers {
    xcsh = {
      source  = "f5-sales-demo/xcsh"
      version = ">= 0"
    }
  }
}
provider "xcsh" {}
```

</div>

## Runtime HCL

Download unchanged files: [main.tf](../../../_data/wingman/runtime/main.tf) · [variables.tf](../../../_data/wingman/runtime/variables.tf) · [versions.tf](../../../_data/wingman/runtime/versions.tf).

<div data-xcsh-context="hcl" data-xcsh-fields="">

```hcl
data "external" "application_image" {
  program = ["python3", "${path.module}/../resolve_image.py"]
  query   = { image = var.application_image }
}

locals {
  contract  = jsondecode(file("${path.module}/../contract.json"))
  namespace = var.namespace == null ? local.contract.namespace : var.namespace
  base_name = var.name == null ? local.contract.base_name : var.name
  names     = { for key, suffix in local.contract.suffixes : key => "${local.base_name}${suffix}" }
  selector  = { (local.contract.app_label) = local.names.application }
}
data "xcsh_namespace" "existing" {
  name = local.namespace
}
data "xcsh_virtual_k8s" "bootstrapped" {
  name      = local.names.virtual_k8s
  namespace = data.xcsh_namespace.existing.name
}
resource "xcsh_certificate" "wingman" {
  name      = local.names.certificate
  namespace = data.xcsh_namespace.existing.name
  blindfold = {
    certificate_file = var.certificate_file
    private_key_file = var.private_key_file
    policy           = "${local.namespace}/${local.names.policy}"
  }
  depends_on = [data.xcsh_virtual_k8s.bootstrapped]
}
resource "kubernetes_config_map_v1" "material" {
  metadata {
    name      = local.names.material
    namespace = local.namespace
  }
  data = merge({
    "certificate.pem"    = file(var.certificate_file)
    "encrypted-location" = xcsh_certificate.wingman.blindfold.encrypted_location
    }, var.xcsh_encrypted_location_file == "" ? {} : {
    "encrypted-location-xcsh" = trimspace(file(var.xcsh_encrypted_location_file))
  })
}
resource "kubernetes_deployment_v1" "application" {
  metadata {
    name      = local.names.application
    namespace = local.namespace
    labels    = local.selector
  }
  spec {
    replicas = 1
    selector {
      match_labels = local.selector
    }
    template {
      metadata {
        labels = local.selector
        annotations = {
          "ves.io/wingman-injection-mode"          = "enable"
          "certificate-management/material-sha256" = sha256(jsonencode(kubernetes_config_map_v1.material.data))
        }
      }
      spec {
        container {
          name              = "application"
          image             = "ghcr.io/f5-sales-demo/certificate-management-wingman@sha256:${split(":", data.external.application_image.result.digest)[1]}"
          image_pull_policy = "Always"
          port {
            name           = "https"
            container_port = local.contract.backend_port
          }
          env {
            name  = "TLS_HOSTNAME"
            value = var.domain
          }
          resources {
            requests = { cpu = "50m", memory = "32Mi" }
            limits   = { cpu = "250m", memory = "128Mi" }
          }
          # vK8s forbids RunAsUser; the immutable image declares USER 65532:65532.
          security_context {
            run_as_non_root            = true
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }
          volume_mount {
            name       = "material"
            mount_path = "/material"
            read_only  = true
          }
          startup_probe {
            http_get {
              path   = "/readyz"
              port   = "https"
              scheme = "HTTPS"
            }
            period_seconds    = 5
            timeout_seconds   = 6
            failure_threshold = 30
          }
          liveness_probe {
            tcp_socket {
              port = "https"
            }
            period_seconds    = 10
            failure_threshold = 3
          }
          readiness_probe {
            http_get {
              path   = "/readyz"
              port   = "https"
              scheme = "HTTPS"
            }
            period_seconds  = 5
            timeout_seconds = 6
          }
        }
        volume {
          name = "material"
          config_map {
            name = kubernetes_config_map_v1.material.metadata[0].name
          }
        }
      }
    }
  }
}
resource "kubernetes_service_v1" "application" {
  metadata {
    name      = local.names.service
    namespace = local.namespace
  }
  spec {
    type     = "ClusterIP"
    selector = local.selector
    port {
      name        = "https"
      port        = local.contract.backend_port
      target_port = "https"
    }
  }
}
output "certificate_fingerprint" {
  value = xcsh_certificate.wingman.blindfold.fingerprint
}
output "owner_integration" {
  value = { name = local.base_name, virtual_site_name = local.names.virtual_site }
}
variable "namespace" {
  type        = string
  default     = null
  description = "Existing namespace; bootstrap and runtime must agree."
}
variable "name" {
  type        = string
  default     = null
  description = "Naming base shared with bootstrap and the existing Terraform owner."
}
variable "kubeconfig_file" {
  type        = string
  description = "Absolute path to a one-day scoped kubeconfig in private session storage."
  validation {
    condition     = startswith(var.kubeconfig_file, "/")
    error_message = "An explicit absolute kubeconfig path is required."
  }
}
variable "kubeconfig_context" {
  type        = string
  description = "Explicit context from the scoped kubeconfig; never use the ambient context."
}
variable "application_image" {
  type        = string
  description = "Published governed Wingman application image."
  validation {
    condition     = can(regex("^ghcr.io/f5-sales-demo/certificate-management-wingman(:latest|@sha256:[a-f0-9]{64})$", var.application_image))
    error_message = "Supply the governed latest application image or an immutable SHA-256 reference."
  }
}
variable "certificate_file" {
  type        = string
  description = "Absolute private path to the Wingman public PEM chain; retained certificate files remain separate."
}
variable "private_key_file" {
  type        = string
  description = "Absolute private path to the existing matching PEM key. Never mount the plaintext key."
}
variable "domain" {
  type        = string
  default     = "certificate-management-terraform.f5-sales-demo.com"
  description = "Existing application hostname covered by the Wingman certificate."
}

variable "xcsh_encrypted_location_file" {
  type        = string
  default     = ""
  description = "Private path to a separate xcsh-prepared Wingman-policy encrypted location for cross-tool qualification. Never supply retained certificate ciphertext from another policy."
}
terraform {
  required_version = null
  required_providers {
    external = {
      source  = "hashicorp/external"
      version = ">= 0"
    }
    xcsh = {
      source  = "f5-sales-demo/xcsh"
      version = ">= 0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 0"
    }
  }
}
provider "xcsh" {}
provider "kubernetes" {
  config_path    = var.kubeconfig_file
  config_context = var.kubeconfig_context
}
```

</div>

## Qualification HCL

Download unchanged files: [main.tf](../../../_data/wingman/qualification/main.tf) · [variables.tf](../../../_data/wingman/qualification/variables.tf) · [versions.tf](../../../_data/wingman/qualification/versions.tf).

<div data-xcsh-context="hcl" data-xcsh-fields="">

```hcl
data "external" "application_image" {
  program = ["python3", "${path.module}/../resolve_image.py"]
  query   = { image = var.application_image }
}

locals {
  contract = jsondecode(file("${path.module}/../contract.json"))
  cases = [
    { mode = "probe-authorized", source = "encrypted-location" },
    { mode = "probe-authorized", source = "encrypted-location-xcsh" },
    { mode = "probe-denied", source = "encrypted-location" }
  ]
  probes = { for index, item in local.cases : tostring(index) => merge(item, {
    name = "${var.run_id}-${index}"
    labels = {
      (local.contract.app_label) = item.mode == "probe-authorized" ? "${var.name}${local.contract.suffixes.application}" : "${var.run_id}-${index}"
      qualification-run          = var.run_id
      qualification-probe        = "${var.run_id}-${index}"
    }
  }) }
}
# Deployments inject Wingman on the observed RE; Job-generated pods do not.
resource "kubernetes_deployment_v1" "probe" {
  for_each         = local.probes
  wait_for_rollout = false
  metadata {
    name      = each.value.name
    namespace = var.namespace
    labels    = each.value.labels
  }
  spec {
    replicas = 1
    selector {
      match_labels = each.value.labels
    }
    template {
      metadata {
        labels      = each.value.labels
        annotations = { "ves.io/wingman-injection-mode" = "enable" }
      }
      spec {
        automount_service_account_token = false
        container {
          name              = "application"
          image             = "ghcr.io/f5-sales-demo/certificate-management-wingman@sha256:${split(":", data.external.application_image.result.digest)[1]}"
          image_pull_policy = "Always"
          command           = ["/wingman-app", each.value.mode]
          env {
            name  = "TLS_HOSTNAME"
            value = var.domain
          }
          env {
            name  = "PROBE_LOCATION_FILE"
            value = "/material/${each.value.source}"
          }
          resources {
            requests = { cpu = "50m", memory = "32Mi" }
            limits   = { cpu = "250m", memory = "128Mi" }
          }
          security_context {
            run_as_non_root            = true
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }
          # Transport reachability only; the application probe requires the READY body.
          readiness_probe {
            tcp_socket {
              port = 8070
            }
            period_seconds = 5
          }
          liveness_probe {
            tcp_socket {
              port = 8070
            }
            initial_delay_seconds = 180
            period_seconds        = 10
          }
          volume_mount {
            name       = "material"
            mount_path = "/material"
            read_only  = true
          }
        }
        volume {
          name = "material"
          config_map {
            name = "${var.name}${local.contract.suffixes.material}"
          }
        }
      }
    }
  }
}
output "probe_inventory" {
  description = "Exact owned UIDs for read-only observation and pre-destroy checks. Keep private."
  value = {
    run              = var.run_id
    requested_image  = var.application_image
    resolved_image   = data.external.application_image.result.image
    platform_digests = split(",", data.external.application_image.result.platform_digests)
    entries = [for index, item in local.cases : {
      name      = kubernetes_deployment_v1.probe[tostring(index)].metadata[0].name
      namespace = var.namespace
      uid       = kubernetes_deployment_v1.probe[tostring(index)].metadata[0].uid
      kind      = "deployment"
      mode      = item.mode
      source    = item.source
    }]
  }
}
variable "namespace" {
  type        = string
  description = "Existing namespace; qualification never owns it."
}
variable "name" {
  type        = string
  description = "Existing runtime naming base; qualification never owns retained resources."
}
variable "kubeconfig_file" {
  type        = string
  description = "Absolute path to a one-day scoped kubeconfig in private session storage."
  validation {
    condition     = startswith(var.kubeconfig_file, "/")
    error_message = "An explicit absolute kubeconfig path is required."
  }
}
variable "kubeconfig_context" {
  type        = string
  description = "Explicit context from the scoped kubeconfig; never use the ambient context."
}
variable "application_image" {
  type        = string
  description = "Published governed Wingman application image."
  validation {
    condition     = can(regex("^ghcr.io/f5-sales-demo/certificate-management-wingman(:latest|@sha256:[a-f0-9]{64})$", var.application_image))
    error_message = "Supply the governed latest application image or an immutable SHA-256 reference."
  }
}
variable "domain" {
  type        = string
  description = "Hostname covered by the existing application certificate."
}
variable "run_id" {
  type        = string
  description = "Unique private run identity; use a new state directory for each run."
  validation {
    condition     = can(regex("^wingman-q-[a-f0-9]{12}$", var.run_id))
    error_message = "Use wingman-q- followed by twelve random lowercase hexadecimal characters."
  }
}
terraform {
  required_version = null
  required_providers {
    external = {
      source  = "hashicorp/external"
      version = ">= 0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 0"
    }
  }
}
provider "kubernetes" {
  config_path    = var.kubeconfig_file
  config_context = var.kubeconfig_context
}
```

</div>

