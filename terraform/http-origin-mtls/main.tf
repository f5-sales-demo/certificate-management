resource "xcsh_http_loadbalancer" "example" {
  name                            = var.name
  namespace                       = data.xcsh_namespace.existing.name
  description                     = var.description
  labels                          = { certificate-example = "terraform" }
  domains                         = [var.domain]
  do_not_advertise                = var.serve ? null : {}
  advertise_on_public_default_vip = var.serve ? {} : null
  dynamic "http" {
    for_each = var.frontend_tls == null ? [1] : []
    content {
      port                 = 80
      dns_volterra_managed = var.serve ? true : null
    }
  }
  dynamic "https" {
    for_each = var.frontend_tls == null ? [] : [var.frontend_tls]
    content {
      port = 443
      tls_parameters {
        no_mtls = {}
        tls_config { default_security = {} }
        tls_certificates {
          blindfold = { id = "downstream", certificate_file = https.value.certificate_file, private_key_file = https.value.private_key_file }
        }
      }
    }
  }
  disable_waf                      = {}
  no_service_policies              = {}
  disable_api_definition           = {}
  disable_api_discovery            = {}
  disable_bot_defense              = {}
  disable_rate_limit               = {}
  disable_ip_reputation            = {}
  disable_malicious_user_detection = {}
  dynamic "routes" {
    for_each = var.serve ? [1] : []
    content {
      simple_route {
        http_method          = "GET"
        disable_host_rewrite = {}
        path { prefix = "/get" }
      }
    }
  }
  default_pool {
    port = var.origin_port
    dynamic "origin_servers" {
      for_each = var.backend_service == null ? [var.origin_hostname] : []
      content {
        public_name { dns_name = origin_servers.value }
      }
    }
    dynamic "origin_servers" {
      for_each = var.backend_service == null ? [] : [var.backend_service]
      content {
        k8s_service {
          protocol      = "PROTOCOL_TCP"
          service_name  = origin_servers.value.service_name
          vk8s_networks = {}
          site_locator {
            virtual_site {
              name      = origin_servers.value.virtual_site_name
              namespace = origin_servers.value.virtual_site_namespace
            }
          }
        }
      }
    }
    use_tls {
      sni = var.origin_sni == null ? var.origin_hostname : var.origin_sni
      tls_config {
        default_security = {}
      }
      no_mtls = var.send_client_certificate ? null : {}
      dynamic "use_mtls" {
        for_each = var.send_client_certificate ? [1] : []
        content {
          tls_certificates {
            blindfold = { id = "server", certificate_file = var.certificate_file, private_key_file = var.private_key_file }
          }
        }
      }
      use_server_verification {
        trusted_ca_url = "string:///${filebase64(var.origin_ca_file)}"
      }
    }
  }
}
