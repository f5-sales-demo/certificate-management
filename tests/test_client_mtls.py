"""Check frontend client trust, exact policy scope, and CRL publication ordering."""

import json
import re
import subprocess
import sys
import tempfile
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
        assert 'resource "xcsh_crl"' not in text
        main = (ROOT / "terraform/named-certificate/main.tf").read_text()
        assert "no_crl = {}" in main

    def test_detachment_retains_owned_policy_and_trust(self):
        main = (ROOT / "terraform/named-certificate/main.tf").read_text()
        client = (ROOT / "terraform/named-certificate/client-mtls.tf").read_text()
        wingman = (ROOT / "terraform/named-certificate/wingman.tf").read_text()
        assert "local.active_client_mtls" in main
        assert "local.active_wingman" in main
        assert "var.client_mtls.enabled ? var.client_mtls : null" in client
        assert "var.wingman.enabled ? var.wingman : null" in wingman
        # Keeping an input object while disabled must keep its resources owned.
        assert "count          = var.client_mtls == null ? 0 : 1" in client
        assert re.search(r"count\s*=\s*var.client_mtls == null \? 0 : 1", client)
        assert re.search(r"count\s*=\s*var.wingman == null \? 0 : 1", wingman)

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

    def test_task_pages_reuse_server_owner_state(self):
        configure = (ROOT / "docs/en/client-mtls/configure.md").read_text()
        verify = (ROOT / "docs/en/client-mtls/verify.md").read_text()
        assert 'configuration="$XCSH_WORKDIR/deployment"' in configure
        assert 'configuration="$XCSH_WORKDIR/deployment"' in verify
        assert 'configuration="$XCSH_WORKDIR/named-certificate"' not in configure

    def test_documented_python_configuration_executes(self):
        page = (ROOT / "docs/en/client-mtls/configure.md").read_text()
        match = re.search(r"<<'PY'\n([\s\S]*?)\nPY", page)
        assert match is not None
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "client.json"
            subprocess.run(  # noqa: S603 -- Fixed Python and canonical documented snippet, no shell.
                [
                    sys.executable,
                    "-",
                    str(path),
                    "/private/ca.pem",
                    "/private/crl.pem",
                    "revision",
                ],
                input=match[1],
                text=True,
                check=True,
            )
            result = json.loads(path.read_text())
            assert result["client_mtls"]["active_crl_revision"] == "revision"
            assert result["client_mtls"]["crl_revisions"] == {
                "revision": "/private/crl.pem"
            }


if __name__ == "__main__":
    unittest.main()
