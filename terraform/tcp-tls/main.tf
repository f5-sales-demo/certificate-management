resource "xcsh_tcp_loadbalancer" "example" {
  name                = var.name
  namespace           = data.xcsh_namespace.existing.name
  description         = var.description
  labels              = { certificate-example = "terraform" }
  domains             = [var.domain]
  listen_port         = 443
  do_not_advertise    = {}
  no_sni              = {}
  no_service_policies = {}
  origin_pools_weights {
    pool {
      name      = xcsh_origin_pool.backend.name
      namespace = data.xcsh_namespace.existing.name
    }
    weight   = 1
    priority = 1
  }
  tls_tcp {
    tls_parameters {
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

resource "xcsh_origin_pool" "backend" {
  name      = "${var.name}-origin"
  namespace = data.xcsh_namespace.existing.name
  labels    = { certificate-example = "terraform" }
  port      = var.origin_port
  origin_servers {
    public_name {
      dns_name = var.origin_hostname
    }
  }
  no_tls = {}
}
