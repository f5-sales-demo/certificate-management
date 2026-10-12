resource "xcsh_cluster" "example" {
  name                            = var.name
  namespace                       = data.xcsh_namespace.existing.name
  description                     = var.description
  labels                          = { certificate-example = "terraform" }
  auto_http_config                = {}
  disable_proxy_protocol          = {}
  no_request_limit_per_connection = {}
  no_panic_threshold              = {}
  tls_parameters {
    sni = var.domain
    common_params {
      minimum_protocol_version = "TLS_AUTO"
      maximum_protocol_version = "TLS_AUTO"
      tls_certificates {
        blindfold = { id = "server", certificate_file = var.certificate_file, private_key_file = var.private_key_file }
      }
    }
  }
}
