resource "xcsh_certificate" "server" {
  name        = var.name
  namespace   = data.xcsh_namespace.existing.name
  description = var.description
  labels      = { certificate-example = "terraform" }
  blindfold   = { certificate_file = var.certificate_file, private_key_file = var.private_key_file, passphrase_env = "XCSH_TLS_INPUT_PASSWORD" }
}
