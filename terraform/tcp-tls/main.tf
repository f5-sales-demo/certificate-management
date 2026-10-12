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
