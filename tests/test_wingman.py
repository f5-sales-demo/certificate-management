"""Guard probe cleanup against foreign or replaced Kubernetes resources."""

# ruff: noqa: PT027 -- Repository unittest protocol tests.
import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

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


class ProbeDeadlineTests(unittest.TestCase):
    def test_late_pod_start_gets_a_full_execution_window(self):
        waiting = {
            "status": {
                "containerStatuses": [
                    {
                        "name": "application",
                        "state": {"waiting": {"reason": "ContainerCreating"}},
                    }
                ]
            }
        }
        assert module.probe_deadline(waiting, 250, 600, None) == (600, None)
        running = {
            "status": {
                "containerStatuses": [
                    {
                        "name": "application",
                        "state": {"running": {"startedAt": "observed"}},
                    }
                ]
            }
        }
        assert module.probe_deadline(running, 590, 600, None) == (770, 770)
        assert module.probe_deadline(running, 700, 600, 770) == (770, 770)

    def test_sidecar_start_does_not_start_application_deadline(self):
        pod = {
            "status": {
                "containerStatuses": [
                    {"name": "wingman", "state": {"running": {"startedAt": "observed"}}}
                ]
            }
        }
        assert module.probe_deadline(pod, 590, 600, None) == (600, None)

    def test_completed_application_counts_as_started(self):
        pod = {
            "status": {
                "containerStatuses": [
                    {
                        "name": "application",
                        "lastState": {"terminated": {"exitCode": 0}},
                    }
                ]
            }
        }
        assert module.probe_deadline(pod, 500, 600, None) == (680, 680)


class ProbeLogTests(unittest.TestCase):
    def test_empty_current_log_reads_completed_previous_container(self):
        command = Mock(
            side_effect=[
                module.subprocess.CompletedProcess([], 0, "", ""),
                module.subprocess.CompletedProcess(
                    [], 0, '{"denied":true,"http_status":403}', ""
                ),
            ]
        )
        with TemporaryDirectory() as directory:
            output = Path(directory) / "probe.log"
            assert module.read_probe_output(command, "probe", False, output) == {
                "denied": True,
                "http_status": 403,
            }
            assert "--previous" in command.call_args_list[1].args
            assert output.read_text().strip() == '{"denied":true,"http_status":403}'

    def test_malformed_nonempty_log_is_preserved_and_rejected(self):
        command = Mock(
            return_value=module.subprocess.CompletedProcess([], 0, "invalid", "")
        )
        with TemporaryDirectory() as directory:
            output = Path(directory) / "probe.log"
            with self.assertRaises(ValueError):
                module.read_probe_output(command, "probe", False, output)
            assert output.read_text() == "invalid"
            assert command.call_count == 1


if __name__ == "__main__":
    unittest.main()
