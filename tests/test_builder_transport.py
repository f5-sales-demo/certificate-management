"""Verify builder transport works without shared runner/daemon filesystem paths."""

# ruff: noqa: PT027 -- Match repository unittest conventions.
import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "customization", Path(__file__).parents[1] / "tests/validate_customization.py"
)
assert spec is not None
assert spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BuilderTransportTests(unittest.TestCase):
    def test_content_and_output_use_copy_transport(self):
        with (
            patch.object(module.subprocess, "check_output", return_value="abc123\n"),
            patch.object(module.subprocess, "run") as run,
        ):
            module.build_published_image(
                "/usr/bin/docker",
                "image@sha256:fake",
                Path("/runner/content"),
                Path("/runner/build"),
            )
        commands = [call.args[0] for call in run.call_args_list]
        assert all("-v" not in command for command in commands)
        assert commands[0] == [
            "/usr/bin/docker",
            "cp",
            "/runner/content",
            "abc123:/content",
        ]
        assert commands[-2] == [
            "/usr/bin/docker",
            "cp",
            "abc123:/app/dist/.",
            "/runner/build",
        ]
        assert commands[-1] == ["/usr/bin/docker", "rm", "-f", "abc123"]

    def test_failed_build_removes_only_created_container(self):
        def invoke(command, **_):
            if command[1] == "start":
                raise subprocess.CalledProcessError(1, command)

        with (
            patch.object(module.subprocess, "check_output", return_value="abc123\n"),
            patch.object(module.subprocess, "run", side_effect=invoke) as run,
            self.assertRaises(subprocess.CalledProcessError),
        ):
            module.build_published_image(
                "/usr/bin/docker",
                "image@sha256:fake",
                Path("/runner/content"),
                Path("/runner/build"),
            )
        assert run.call_args_list[-1].args[0] == [
            "/usr/bin/docker",
            "rm",
            "-f",
            "abc123",
        ]


if __name__ == "__main__":
    unittest.main()
