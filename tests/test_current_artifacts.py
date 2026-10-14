"""Reject publication drift and corrupted downloads before qualification."""

# ruff: noqa: PT027 -- Repository unittest contract tests.
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "artifacts", Path(__file__).parents[1] / "scripts/resolve_current_artifacts.py"
)
assert spec is not None
assert spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ArtifactTests(unittest.TestCase):
    def test_digest_mismatch_fails(self):
        with self.assertRaises(ValueError):
            module.verify_digest(b"changed", "sha256:" + "0" * 64)

    def test_publication_drift_fails(self):
        with self.assertRaises(ValueError):
            module.require_same_set(
                {"provider": {"version": "1"}}, {"provider": {"version": "2"}}
            )

    def test_unchanged_set_passes(self):
        module.require_same_set(
            {"provider": {"version": "1"}}, {"provider": {"version": "1"}}
        )


if __name__ == "__main__":
    unittest.main()
