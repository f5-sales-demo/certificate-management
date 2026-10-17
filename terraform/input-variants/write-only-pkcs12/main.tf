resource "xcsh_certificate" "server" {
  name        = var.name
  namespace   = data.xcsh_namespace.existing.name
  description = var.description
  labels      = { certificate-example = "terraform" }
  blindfold   = { pkcs12_wo = var.pkcs12_base64, passphrase_wo = var.passphrase, material_version = "1" }
}
