resource "xcsh_certificate" "server" {
  name        = var.name
  namespace   = data.xcsh_namespace.existing.name
  description = var.description
  labels      = { certificate-example = "terraform" }
  blindfold   = { pkcs12_file = var.pkcs12_file, passphrase_env = "XCSH_TLS_INPUT_PASSWORD" }
}
