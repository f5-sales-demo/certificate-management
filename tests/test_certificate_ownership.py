"""Ensure live qualification cannot adopt or clean up another owner's resources."""

# ruff: noqa: PT027 -- Match repository unittest conventions.
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "qualification", Path(__file__).parents[1] / "scripts/qualify_certificates.py"
)
assert spec is not None
assert spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OwnershipTests(unittest.TestCase):
    def test_retained_name_is_rejected(self):
        with self.assertRaises(ValueError):
            module.require_run_ownership(
                "certificate-management", "demo", "cert-q-test", "demo"
            )

    def test_foreign_namespace_is_rejected(self):
        with self.assertRaises(ValueError):
            module.require_run_ownership(
                "cert-q-test-owned", "system", "cert-q-test", "demo"
            )

    def test_permission_failure_is_not_absence(self):
        with self.assertRaises(ValueError):
            module.require_typed_absence(403)
        module.require_typed_absence(404)

    def test_changed_identity_prevents_cleanup(self):
        observed = {
            "metadata": {"labels": {"qualification-run": "cert-q-test"}},
            "system_metadata": {"uid": "new-owner"},
        }
        with self.assertRaises(ValueError):
            module.require_cleanup_owner({"uid": "old-owner"}, observed, "cert-q-test")

    def test_foreign_label_prevents_cleanup(self):
        observed = {"metadata": {"labels": {"qualification-run": "another-run"}}}
        with self.assertRaises(ValueError):
            module.require_cleanup_owner({}, observed, "cert-q-test")


if __name__ == "__main__":
    unittest.main()
