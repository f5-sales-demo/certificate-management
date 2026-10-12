resource "xcsh_advertise_policy" "example" {
  name        = var.name
  namespace   = data.xcsh_namespace.existing.name
  description = var.description
  labels      = { certificate-example = "terraform" }
  protocol    = "TCP"
  port        = 8443
  ipv4        = {}
  tls_parameters {
    no_client_certificate = {}
    common_params {
      minimum_protocol_version = "TLS_AUTO"
      maximum_protocol_version = "TLS_AUTO"
      tls_certificates {
        blindfold = { id = "server", certificate_file = var.certificate_file, private_key_file = var.private_key_file }
      }
    }
  }
}
