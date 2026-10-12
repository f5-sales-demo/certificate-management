output "endpoint" {
  value = "https://${var.domain}/get"
}
output "certificate_fingerprint" {
  value = xcsh_certificate.server.blindfold.fingerprint
}
output "certificate_expiration" {
  value = xcsh_certificate.server.blindfold.expires_at
}
output "encryption_context_digest" {
  value = xcsh_certificate.server.blindfold.context_digest
}
