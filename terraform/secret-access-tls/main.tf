resource "xcsh_secret_management_access" "example" {
  name          = var.name
  namespace     = data.xcsh_namespace.existing.name
  description   = var.description
  labels        = { certificate-example = "terraform" }
  provider_name = "REST"
  access_info {
    scheme          = "HTTPS"
    server_endpoint = "${var.domain}:443"
    tls_config {
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
}
