output "inventory" {
  value = {
    resource               = "xcsh_http_loadbalancer.example"
    name                   = xcsh_http_loadbalancer.example.name
    endpoint               = var.serve ? "${var.frontend_tls == null ? "http" : "https"}://${var.domain}/get" : null
    certificate_role       = "default_pool.use_tls.use_mtls.tls_certificates"
    logical_certificate_id = "server"
    supporting_resources   = var.serve && var.frontend_tls != null ? ["xcsh_http_loadbalancer.dns[0]"] : []
    dependencies           = { origin_hostname = var.origin_hostname, backend_service = var.backend_service }
  }
}
