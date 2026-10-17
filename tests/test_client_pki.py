"""Exercise real OpenSSL issuance, renewal and revocation in a private CA database."""

# ruff: noqa: S603, S607 -- Fixed executables and disposable owned fixture argv.
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/client_pki.py"


class ClientPKITests(unittest.TestCase):
    def run_pki(self, *args):
        result = subprocess.run(
            ["python3", str(SCRIPT), *map(str, args)],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_renewal_and_revocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "ca"
            self.run_pki("init", root, "--name", "Synthetic test CA")
            old = self.run_pki("issue", root, "--client", "client-old")
            renewed = self.run_pki("issue", root, "--client", "client-renewed")
            assert old["serial"] != renewed["serial"]
            assert old["certificate_sha256"] != renewed["certificate_sha256"]
            self.run_pki("crl", root, "--revision", "before")
            for client in ["client-old", "client-renewed"]:
                subprocess.run(
                    [
                        "openssl",
                        "verify",
                        "-purpose",
                        "sslclient",
                        "-crl_check",
                        "-CAfile",
                        str(root / "ca.pem"),
                        "-CRLfile",
                        str(root / "crls/before.pem"),
                        str(root / "clients" / client / "certificate.pem"),
                    ],
                    capture_output=True,
                    check=True,
                )
            self.run_pki("revoke", root, "--client", "client-old")
            self.run_pki("crl", root, "--revision", "after")
            old_check = subprocess.run(
                [
                    "openssl",
                    "verify",
                    "-crl_check",
                    "-CAfile",
                    str(root / "ca.pem"),
                    "-CRLfile",
                    str(root / "crls/after.pem"),
                    str(root / "clients/client-old/certificate.pem"),
                ],
                capture_output=True,
                check=False,
            )
            assert old_check.returncode != 0
            subprocess.run(
                [
                    "openssl",
                    "verify",
                    "-crl_check",
                    "-CAfile",
                    str(root / "ca.pem"),
                    "-CRLfile",
                    str(root / "crls/after.pem"),
                    str(root / "clients/client-renewed/certificate.pem"),
                ],
                capture_output=True,
                check=True,
            )
            assert root.stat().st_mode & 511 == 448
            assert (root / "ca.key").stat().st_mode & 511 == 384
            duplicate = subprocess.run(
                ["python3", str(SCRIPT), "crl", str(root), "--revision", "after"],
                capture_output=True,
                check=False,
            )
            assert duplicate.returncode != 0


if __name__ == "__main__":
    unittest.main()
