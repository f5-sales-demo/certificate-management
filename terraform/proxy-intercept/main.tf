resource "xcsh_proxy" "example" {
  name                    = var.name
  namespace               = data.xcsh_namespace.existing.name
  description             = var.description
  labels                  = { certificate-example = "terraform" }
  do_not_advertise        = {}
  site_local_network      = {}
  no_forward_proxy_policy = {}
  http_proxy {
    enable_http {

    }
  }
  tls_intercept {
    enable_for_all_domains = {}
    volterra_trusted_ca    = {}
    custom_certificate {
      blindfold = { id = "signing-ca", certificate_file = var.certificate_file, private_key_file = var.private_key_file }
    }
  }
}
