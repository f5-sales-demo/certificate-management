resource "xcsh_virtual_host" "example" {
  name                            = var.name
  namespace                       = data.xcsh_namespace.existing.name
  description                     = var.description
  labels                          = { certificate-example = "terraform" }
  domains                         = [var.domain]
  proxy                           = "SMA_PROXY"
  no_authentication               = {}
  no_challenge                    = {}
  default_loadbalancer            = {}
  default_header                  = {}
  enable_path_normalize           = {}
  no_request_limit_per_connection = {}
  tls_parameters {
    no_client_certificate = {}
    common_params {
      tls_certificates {
        blindfold = { id = "server", certificate_file = var.certificate_file, private_key_file = var.private_key_file }
      }
    }
  }
}
