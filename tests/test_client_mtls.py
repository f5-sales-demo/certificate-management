"""Check frontend client trust, exact policy scope, and CRL publication ordering."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ClientMTLSTests(unittest.TestCase):
    def test_configuration_is_default_off_and_revision_selected(self):
        text = (ROOT / "terraform/named-certificate/client-mtls.tf").read_text()
        assert "default     = null" in text
        assert (
            "contains(keys(var.client_mtls.crl_revisions), var.client_mtls.active_crl_revision)"
            in text
        )
        assert "refresh_interval = 6" in text
        assert "timeout          = 10" in text
        assert "depends_on = [xcsh_http_loadbalancer.http]" in text

    def test_policy_has_exact_path_and_deny_before_allow(self):
        text = (ROOT / "terraform/named-certificate/client-mtls.tf").read_text()
        assert 'exact_values = ["/mtls/write"]' in text
        assert 'methods = ["POST", "PUT", "PATCH"]' in text
        assert text.index('action     = "DENY"') < text.index('action     = "ALLOW"')
        assert "check_not_present = {}" in text

    def test_crl_routes_precede_redirect_and_server_reference_is_retained(self):
        text = (ROOT / "terraform/named-certificate/main.tf").read_text()
        assert text.index("for_each = local.client_crls") < text.index(
            "redirect_route {"
        )
        assert 'path = "/mtls/crl/${routes.key}.pem"' in text
        assert "name      = xcsh_certificate.server.name" in text
        assert 'xfcc_header_elements = ["XFCC_CERT", "XFCC_CHAIN"]' in text


if __name__ == "__main__":
    unittest.main()
