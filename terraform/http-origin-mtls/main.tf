resource "xcsh_http_loadbalancer" "example" {
  name             = var.name
  namespace        = data.xcsh_namespace.existing.name
  description      = var.description
  labels           = { certificate-example = "terraform" }
  domains          = [var.domain]
  do_not_advertise = {}
  http {
    port = 80
  }
  disable_waf                      = {}
  no_service_policies              = {}
  disable_api_definition           = {}
  disable_api_discovery            = {}
  disable_bot_defense              = {}
  disable_rate_limit               = {}
  disable_ip_reputation            = {}
  disable_malicious_user_detection = {}
  default_pool {
    port = 443
    origin_servers {
      public_name {
        dns_name = var.origin_hostname
      }
    }
    use_tls {
      sni = var.origin_hostname
      tls_config {
        default_security = {}
      }
      use_mtls {
        tls_certificates {
          blindfold = { id = "server", certificate_file = var.certificate_file, private_key_file = var.private_key_file }
        }
      }
      use_server_verification {
        trusted_ca_url = "string:///${filebase64(var.origin_ca_file)}"
      }
    }
  }
}
