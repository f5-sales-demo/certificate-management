resource "xcsh_certificate" "server" {
  name        = var.name
  namespace   = data.xcsh_namespace.existing.name
  description = var.description
  labels      = { certificate-example = "terraform" }
  blindfold   = { certificate_file = var.certificate_file, private_key_file = var.private_key_file }
}

resource "xcsh_http_loadbalancer" "https" {
  name                             = var.name
  namespace                        = data.xcsh_namespace.existing.name
  description                      = var.description
  labels                           = { certificate-example = "terraform" }
  domains                          = [var.domain]
  advertise_on_public_default_vip  = {}
  disable_waf                      = {}
  no_service_policies              = {}
  disable_api_definition           = {}
  disable_api_discovery            = {}
  disable_bot_defense              = {}
  disable_rate_limit               = {}
  disable_ip_reputation            = {}
  disable_malicious_user_detection = {}
  https {
    port = 443
    tls_cert_params {
      no_mtls = {}
      tls_config {
        default_security = {}
      }
      certificates {
        name      = xcsh_certificate.server.name
        namespace = data.xcsh_namespace.existing.name
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
  dynamic "routes" {
    for_each = var.wingman == null ? [] : [var.wingman]
    content {
      simple_route {
        http_method          = "GET"
        disable_host_rewrite = {}
        path {
          prefix = local.wingman_contract.route_prefix
        }
        origin_pools {
          weight   = 1
          priority = 1
          pool {
            name      = xcsh_origin_pool.wingman[0].name
            namespace = data.xcsh_namespace.existing.name
          }
        }
      }
    }
  }

}

resource "xcsh_http_loadbalancer" "http" {
  name                             = "${var.name}-http"
  namespace                        = data.xcsh_namespace.existing.name
  description                      = var.description
  labels                           = { certificate-example = "terraform" }
  domains                          = [var.domain]
  advertise_on_public_default_vip  = {}
  disable_waf                      = {}
  no_service_policies              = {}
  disable_api_definition           = {}
  disable_api_discovery            = {}
  disable_bot_defense              = {}
  disable_rate_limit               = {}
  disable_ip_reputation            = {}
  disable_malicious_user_detection = {}
  http {
    port                 = 80
    dns_volterra_managed = true
  }
  routes {
    redirect_route {
      http_method = "ANY"
      path {
        prefix = "/"
      }
      route_redirect {
        proto_redirect = "https"
        host_redirect  = var.domain
        response_code  = 301
      }
    }
  }
}
