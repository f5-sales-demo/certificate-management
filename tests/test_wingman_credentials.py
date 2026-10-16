"""Verify generated credential identity, scoped readback, and revocation."""

import base64
import json
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from wingman import kubeconfig


class CredentialLifecycleTests(unittest.TestCase):
    """Exercise the one-shot issuance and exact-owner revocation contract."""

    def test_server_assigned_identity_is_journaled_and_revoked(self):
        """Accept scoped server names while retaining their UID for cleanup."""
        active = True
        name = ""
        expires = (datetime.now(UTC) + timedelta(days=1)).isoformat()

        def request(_base, _token, path, body=None):
            nonlocal name, active
            if path.endswith("revoke/api_credentials"):
                assert body["name"] == name
                active = False
                return {}
            if body is not None:
                assert len(body["name"]) <= 31
                assert body["spec"]["virtual_k8s_namespace"] == "demo-app"
                name = body["name"] + "-abcdefgh"
                return {
                    "name": name,
                    "active": True,
                    "expiration_timestamp": expires,
                    "data": base64.b64encode(b"synthetic kubeconfig").decode(),
                }
            assert path.endswith("/" + name)
            return {
                "object": {
                    "metadata": {"name": name, "namespace": "system"},
                    "system_metadata": {"uid": "synthetic-uid"},
                    "spec": {
                        "gc_spec": {
                            "type": "KUBE_CONFIG",
                            "virtual_k8s_name": "demo-app-wingman",
                            "virtual_k8s_namespace": "demo-app",
                            "active": active,
                        }
                    },
                }
            }

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "session"
            with (
                patch.dict(
                    os.environ,
                    XCSH_API_URL="https://tenant.example.com",
                    XCSH_API_TOKEN=str(id(self)),
                ),
                patch.object(kubeconfig, "request", side_effect=request),
                patch.object(
                    sys,
                    "argv",
                    [
                        "kubeconfig.py",
                        "issue",
                        "--namespace",
                        "demo-app",
                        "--vk8s",
                        "demo-app-wingman",
                        "--private-directory",
                        str(directory),
                    ],
                ),
            ):
                kubeconfig.main()
            record = json.loads((directory / "credential.json").read_text())
            assert record["name"] == name
            assert record["uid"] == "synthetic-uid"
            assert (directory / "kubeconfig").stat().st_mode & 511 == 384
            with (
                patch.dict(
                    os.environ,
                    XCSH_API_URL="https://tenant.example.com",
                    XCSH_API_TOKEN=str(id(self)),
                ),
                patch.object(kubeconfig, "request", side_effect=request),
                patch.object(
                    sys,
                    "argv",
                    ["kubeconfig.py", "revoke", "--private-directory", str(directory)],
                ),
            ):
                kubeconfig.main()
            assert not (directory / "kubeconfig").exists()
            assert (
                json.loads((directory / "credential.json").read_text())["status"]
                == "revoked-inactive-readback"
            )


if __name__ == "__main__":
    unittest.main()
