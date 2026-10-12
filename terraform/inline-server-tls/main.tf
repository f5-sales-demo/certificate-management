resource "xcsh_http_loadbalancer" "example" {
  name                             = var.name
  namespace                        = data.xcsh_namespace.existing.name
  description                      = var.description
  labels                           = { certificate-example = "terraform" }
  disable_waf                      = {}
  no_service_policies              = {}
  disable_api_definition           = {}
  disable_api_discovery            = {}
  disable_bot_defense              = {}
  disable_rate_limit               = {}
  disable_ip_reputation            = {}
  disable_malicious_user_detection = {}
  domains                          = [var.domain]
  advertise_on_public_default_vip  = {}
  https {
    port = 443
    tls_parameters {
      no_mtls = {}
      tls_config {
        default_security = {}
      }
      dynamic "tls_certificates" {
        for_each = var.certificates
        content {
          blindfold = {
            id               = tls_certificates.value.id
            certificate_file = tls_certificates.value.certificate_file
            private_key_file = tls_certificates.value.private_key_file
          }
        }
      }
    }
  }
  routes {
    direct_response_route {
      http_method = "GET"
      path {
        path = "/get"
      }
      route_direct_response {
        response_code         = 200
        response_body_encoded = "string:///${base64encode(jsonencode({ example = "terraform-certificate", native_blindfold = true }))}"
      }
    }
  }
}
