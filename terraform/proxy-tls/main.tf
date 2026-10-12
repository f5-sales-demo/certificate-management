resource "xcsh_proxy" "example" {
  name                    = var.name
  namespace               = data.xcsh_namespace.existing.name
  description             = var.description
  labels                  = { certificate-example = "terraform" }
  do_not_advertise        = {}
  site_local_network      = {}
  no_forward_proxy_policy = {}
  no_interception         = {}
  dynamic_proxy {
    domains                = [var.domain]
    disable_dns_masquerade = {}
    https_proxy {
      tls_params {
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
