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
