resource "xcsh_cdn_loadbalancer" "example" {
  name                             = var.name
  namespace                        = data.xcsh_namespace.existing.name
  description                      = var.description
  labels                           = { certificate-example = "terraform" }
  domains                          = [var.domain]
  no_service_policies              = {}
  disable_waf                      = {}
  disable_api_definition           = {}
  disable_api_discovery            = {}
  disable_rate_limit               = {}
  disable_ip_reputation            = {}
  disable_malicious_user_detection = {}
  disable_client_side_defense      = {}
  disable_threat_mesh              = {}
  no_challenge                     = {}
  system_default_timeouts          = {}
  user_id_client_ip                = {}
  default_sensitive_data_policy    = {}
  l7_ddos_action_default           = {}
  origin_pool {
    origin_request_timeout = "60s"
    origin_servers {
      port = 443
      public_name {
        dns_name = var.origin_hostname
      }
    }
    no_tls = {}
  }
  https {
    tls_cert_options {
      tls_inline_params {
        no_mtls = {}
        tls_config {
          default_security = {}
        }
        tls_certificates {
          blindfold = { id = "server", certificate_file = var.certificate_file, private_key_file = var.private_key_file }
        }
      }
    }
  }
}
