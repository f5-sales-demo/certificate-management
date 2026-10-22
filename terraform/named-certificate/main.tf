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
  no_service_policies              = local.active_client_mtls == null ? {} : null
  disable_api_definition           = {}
  disable_api_discovery            = {}
  disable_bot_defense              = {}
  disable_rate_limit               = {}
  disable_ip_reputation            = {}
  disable_malicious_user_detection = {}
  dynamic "active_service_policies" {
    for_each = local.active_client_mtls == null ? [] : [1]
    content {
      policies {
        name      = xcsh_service_policy.client_write[0].name
        namespace = data.xcsh_namespace.existing.name
      }
    }
  }
  lifecycle {
    precondition {
      condition     = local.active_client_mtls == null || local.active_wingman != null
      error_message = "Qualify and configure the Wingman origin before enabling client mTLS."
    }
  }
  https {
    port = 443
    tls_cert_params {
      no_mtls = local.active_client_mtls == null ? {} : null
      dynamic "use_mtls" {
        for_each = local.active_client_mtls == null ? [] : [local.active_client_mtls]
        content {
          client_certificate_optional = true
          trusted_ca {
            name      = xcsh_trusted_ca_list.client[0].name
            namespace = data.xcsh_namespace.existing.name
          }
          no_crl = {}
          xfcc_options {
            xfcc_header_elements = ["XFCC_CERT", "XFCC_CHAIN"]
          }
        }
      }
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
    for_each = local.active_wingman == null ? [] : [local.active_wingman]
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

  dynamic "routes" {
    for_each = local.active_client_mtls == null ? [] : ["/mtls/identity", "/mtls/write"]
    content {
      simple_route {
        http_method          = "ANY"
        disable_host_rewrite = {}
        path { path = routes.value }
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
  dynamic "routes" {
    for_each = local.client_crls
    content {
      direct_response_route {
        http_method = "GET"
        path { path = "/mtls/crl/${routes.key}.pem" }
        route_direct_response {
          response_code         = 200
          response_body_encoded = "string:///${filebase64(routes.value)}"
        }
      }
    }
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
