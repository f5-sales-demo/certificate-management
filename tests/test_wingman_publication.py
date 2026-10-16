"""Keep public TLS trust distinct from the Wingman backend certificate."""

import hashlib
import importlib.util
import json
import ssl
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "publication", ROOT / "scripts/check_publication.py"
)
assert SPEC is not None
assert SPEC.loader is not None
publication = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publication)


class WingmanPublicHealthTests(unittest.TestCase):
    """Reject conflation of the frontend and backend certificate identities."""

    def check_response(self, fingerprint: str) -> dict:
        """Exercise the checker with a distinct public TLS connection."""
        public = ROOT / "docs/assets/certificate-management.pem"
        backend = ROOT / "docs/assets/wingman-certificate.pem"
        connection = Mock()
        connection.sock.getpeercert.return_value = ssl.PEM_cert_to_DER_cert(
            public.read_text()
        )
        response = Mock()
        response.status = 200
        response.read.return_value = json.dumps(
            {
                "example": "wingman-certificate",
                "certificate_sha256": fingerprint,
            }
        ).encode()
        connection.getresponse.return_value = response
        with patch.object(
            publication.http.client, "HTTPSConnection", return_value=connection
        ):
            return publication.wingman_endpoint(public, backend)

    def test_separate_backend_leaf_and_public_certificate_are_accepted(self):
        """Accept the published backend leaf while trusting public TLS separately."""
        chain = (ROOT / "docs/assets/wingman-certificate.pem").read_text()
        leaf = (
            chain.split("-----END CERTIFICATE-----", 1)[0]
            + "-----END CERTIFICATE-----\n"
        )
        backend_hash = hashlib.sha256(ssl.PEM_cert_to_DER_cert(leaf)).hexdigest()
        result = self.check_response(backend_hash)
        assert result["application_certificate_sha256"] == backend_hash
        assert result["public_certificate_sha256"] != backend_hash

    def test_public_certificate_fingerprint_cannot_replace_backend_fingerprint(self):
        """Reject a response that incorrectly reports the public edge certificate."""
        public = (ROOT / "docs/assets/certificate-management.pem").read_text()
        public_hash = hashlib.sha256(ssl.PEM_cert_to_DER_cert(public)).hexdigest()
        with self.assertRaises(ValueError):  # noqa: PT027 -- Repository unittest protocol tests.
            self.check_response(public_hash)


class WingmanDownloadTests(unittest.TestCase):
    """Reject stale public Wingman certificate downloads."""

    def test_stale_ca_or_leaf_download_is_rejected(self):
        """Require both public PEM downloads to match the reviewed source."""
        for stale in ["wingman-ca.pem", "wingman-certificate.pem"]:
            with self.subTest(stale=stale), TemporaryDirectory() as directory:
                root = Path(directory)
                assets = root / "docs/assets"
                assets.mkdir(parents=True)
                (root / "docs/_imports").write_text("")
                for name in ["wingman-ca.pem", "wingman-certificate.pem"]:
                    (assets / name).write_bytes(b"reviewed public certificate")

                def response(url, stale_name=stale, **_kwargs):
                    """Return a changed public file for one requested asset."""
                    stream = Mock()
                    value = (
                        b"stale certificate"
                        if url.endswith(stale_name)
                        else b"reviewed public certificate"
                    )
                    stream.__enter__ = Mock(return_value=stream)
                    stream.__exit__ = Mock(return_value=False)
                    stream.read.return_value = value
                    return stream

                with (
                    patch.object(
                        publication.urllib.request, "urlopen", side_effect=response
                    ),
                    self.assertRaises(ValueError),  # noqa: PT027 -- Repository unittest tests.
                ):
                    publication.downloads(root, "https://example.test")


if __name__ == "__main__":
    unittest.main()
