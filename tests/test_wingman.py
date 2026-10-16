"""Guard probe cleanup against foreign or replaced Kubernetes resources."""

# ruff: noqa: PT027 -- Repository unittest protocol tests.
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "wingman_qualification", Path(__file__).parents[1] / "wingman/qualify.py"
)
assert spec is not None
assert spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProbeOwnershipTests(unittest.TestCase):
    def test_exact_identity_is_required(self):
        pod = {
            "metadata": {
                "name": "probe",
                "namespace": "demo",
                "uid": "owned-uid",
                "labels": {"qualification-run": "run"},
            }
        }
        assert (
            module.require_owner(pod, "probe", "demo", "run", "owned-uid")
            == "owned-uid"
        )
        for arguments in [
            ("other", "demo", "run", "owned-uid"),
            ("probe", "other", "run", "owned-uid"),
            ("probe", "demo", "other", "owned-uid"),
            ("probe", "demo", "run", "replacement-uid"),
        ]:
            with self.assertRaises(ValueError):
                module.require_owner(pod, *arguments)

    def test_missing_uid_cannot_authorize_cleanup(self):
        with self.assertRaises(ValueError):
            module.require_owner(
                {
                    "metadata": {
                        "name": "probe",
                        "namespace": "demo",
                        "labels": {"qualification-run": "run"},
                    }
                },
                "probe",
                "demo",
                "run",
            )


class ScopedRawURITest(unittest.TestCase):
    def test_scoped_server_path_is_preserved(self):
        assert (
            module.raw_resource_uri(
                "https://example.test/api/vk8s/namespaces/demo/demo-wingman",
                "/api/v1/namespaces/demo/pods/probe",
            )
            == "/api/vk8s/namespaces/demo/demo-wingman/api/v1/namespaces/demo/pods/probe"
        )
        assert (
            module.raw_resource_uri("https://example.test/", "/apis/apps/v1")
            == "/apis/apps/v1"
        )

    def test_ambiguous_server_is_rejected(self):
        with self.assertRaises(ValueError):
            module.raw_resource_uri("https://example.test/?token=opaque", "/api/v1")


if __name__ == "__main__":
    unittest.main()
