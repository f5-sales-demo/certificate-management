resource "xcsh_http_loadbalancer" "dns" {
  count                            = var.serve && var.frontend_tls != null ? 1 : 0
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
      path { prefix = "/" }
      route_redirect {
        proto_redirect = "https"
        host_redirect  = var.domain
        response_code  = 301
      }
    }
  }
}
