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
          image             = var.application_image
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
    run = var.run_id
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
