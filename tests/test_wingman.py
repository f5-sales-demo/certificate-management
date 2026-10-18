"""Guard probe cleanup against foreign or replaced Kubernetes resources."""

# ruff: noqa: PT027 -- Repository unittest protocol tests.
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

spec = importlib.util.spec_from_file_location(
    "wingman_qualification", Path(__file__).parents[1] / "wingman/qualify.py"
)
assert spec is not None
assert spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

image_spec = importlib.util.spec_from_file_location(
    "wingman_image", Path(__file__).parents[1] / "wingman/resolve_image.py"
)
assert image_spec is not None
assert image_spec.loader is not None
images = importlib.util.module_from_spec(image_spec)
with patch.dict(sys.modules, {"qualify": module}):
    image_spec.loader.exec_module(images)


class RegistryImageTests(unittest.TestCase):
    def test_latest_resolves_verified_index_and_linux_manifests(self):
        body = json.dumps(
            {
                "manifests": [
                    {"digest": "sha256:" + "a" * 64, "platform": {"os": "linux"}},
                    {"digest": "sha256:" + "b" * 64, "platform": {"os": "unknown"}},
                ]
            }
        ).encode()
        digest = "sha256:" + hashlib.sha256(body).hexdigest()
        with patch.object(images, "registry_get", return_value=(200, body, digest)):
            result = images.resolve(images.PREFIX + ":latest")
        assert result["image"] == images.PREFIX + "@" + digest
        assert result["platform_digests"] == "sha256:" + "a" * 64

    def test_registry_digest_mismatch_is_rejected(self):
        with (
            patch.object(
                images, "registry_get", return_value=(200, b"{}", "sha256:" + "a" * 64)
            ),
            self.assertRaises(ValueError),
        ):
            images.resolve(images.PREFIX + ":latest")

    def test_registry_transport_stays_on_https_ghcr(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 302
        response.read.return_value = b""
        response.getheader.return_value = None
        with patch.object(
            images.http.client, "HTTPSConnection", return_value=connection
        ) as factory:
            assert images.registry_get("/v2/example/manifests/latest", {}) == (
                302,
                b"",
                None,
            )
        factory.assert_called_once_with("ghcr.io", timeout=30)
        connection.request.assert_called_once_with(
            "GET", "/v2/example/manifests/latest", headers={}
        )
        connection.close.assert_called_once()

    def test_registry_redirect_is_rejected(self):
        with (
            patch.object(images, "registry_get", return_value=(302, b"", None)),
            self.assertRaises(ValueError),
        ):
            images.resolve(images.PREFIX + ":latest")

    def test_observation_rejects_mutable_or_foreign_planned_image(self):
        selected = images.PREFIX + ":latest"
        inventory = {
            "requested_image": selected,
            "resolved_image": selected,
            "platform_digests": ["sha256:" + "a" * 64],
        }
        with self.assertRaises(ValueError):
            module.planned_image(inventory, selected)
        inventory["resolved_image"] = images.PREFIX + "@sha256:" + "b" * 64
        with self.assertRaises(ValueError):
            module.planned_image(inventory, images.PREFIX + "@sha256:" + "c" * 64)


class ApplicationImageTests(unittest.TestCase):
    def test_public_deployment_uses_kubernetes_probe_ports(self):
        document = json.loads(
            (
                Path(__file__).parents[1]
                / "docs/assets/configurations/wingman-deployment.json"
            ).read_text()
        )
        application = document["spec"]["template"]["spec"]["containers"][0]
        assert application["ports"][0]["containerPort"] == 8443
        for probe, handler in [
            ("startupProbe", "httpGet"),
            ("readinessProbe", "httpGet"),
            ("livenessProbe", "tcpSocket"),
        ]:
            assert application[probe][handler]["port"] == "https"
            assert "ports" not in application[probe][handler]

    def test_governed_latest_and_immutable_references(self):
        prefix = "ghcr.io/f5-sales-demo/certificate-management-wingman"
        module.require_image(prefix + ":latest")
        module.require_image(prefix + "@sha256:" + "a" * 64)
        for reference in [
            prefix + ":dev",
            prefix + "@sha256:" + "a" * 63,
            "ghcr.io/other/application:latest",
            prefix + ":latest@sha256:" + "a" * 64,
        ]:
            with self.assertRaises(ValueError):
                module.require_image(reference)


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


class TerraformInventoryTests(unittest.TestCase):
    def inventory(self):
        run = "wingman-q-012345abcdef"
        return {
            "run": run,
            "entries": [
                {
                    "name": run + "-" + str(i),
                    "namespace": "demo",
                    "uid": "owned-" + str(i),
                    "kind": "deployment",
                    "mode": mode,
                    "source": source,
                }
                for i, (mode, source) in enumerate(
                    [
                        ("probe-authorized", "encrypted-location"),
                        ("probe-authorized", "encrypted-location-xcsh"),
                        ("probe-denied", "encrypted-location"),
                    ]
                )
            ],
        }

    def test_exact_terraform_inventory_is_accepted(self):
        document = self.inventory()
        run, entries = module.terraform_inventory(document, "demo")
        assert run == document["run"]
        assert len(entries) == 3
        assert all(entry["pods"] == {} for entry in entries)

    def test_partial_foreign_and_mislabelled_inventory_is_rejected(self):
        for key, value in [
            ("namespace", "other"),
            ("uid", ""),
            ("name", "retained"),
            ("mode", "probe-authorized"),
            ("kind", "job"),
        ]:
            document = self.inventory()
            document["entries"][2][key] = value
            with self.assertRaises(ValueError):
                module.terraform_inventory(document, "demo")
        document = self.inventory()
        document["entries"].pop()
        with self.assertRaises(ValueError):
            module.terraform_inventory(document, "demo")


class ProbeContractTests(unittest.TestCase):
    def pod(self):
        return {
            "metadata": {"labels": {"app": "demo-wingman"}},
            "spec": {
                "containers": [
                    {
                        "name": "application",
                        "image": "image@sha256:digest",
                        "command": ["/wingman-app", "probe-authorized"],
                        "env": [
                            {"name": "TLS_HOSTNAME", "value": "demo.example.com"},
                            {
                                "name": "PROBE_LOCATION_FILE",
                                "value": "/material/encrypted-location",
                            },
                        ],
                    }
                ]
            },
        }

    def check(self, pod):
        module.require_probe_contract(
            pod,
            "probe-authorized",
            "encrypted-location",
            "image@sha256:digest",
            "demo.example.com",
            {"app": "demo-wingman"},
        )

    def test_live_probe_matches_expected_invocation(self):
        self.check(self.pod())

    def test_changed_source_image_command_or_policy_label_is_rejected(self):
        for key, value in [
            ("image", "other@sha256:digest"),
            ("command", ["/wingman-app", "probe-denied"]),
            ("env", [{"name": "PROBE_LOCATION_FILE", "value": "/material/other"}]),
        ]:
            pod = self.pod()
            pod["spec"]["containers"][0][key] = value
            with self.assertRaises(ValueError):
                self.check(pod)
        pod = self.pod()
        pod["metadata"]["labels"]["app"] = "unselected"
        with self.assertRaises(ValueError):
            self.check(pod)


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
    def test_cri_transport_error_with_exit_zero_uses_other_container_log(self):
        command = Mock(
            side_effect=[
                module.subprocess.CompletedProcess(
                    [], 0, "unable to retrieve container logs for cri-o://owned", ""
                ),
                module.subprocess.CompletedProcess(
                    [], 0, '{"denied":true,"http_status":403}', ""
                ),
            ]
        )
        with TemporaryDirectory() as directory:
            output = Path(directory) / "probe.log"
            assert (
                module.read_probe_output(command, "probe", True, output)["http_status"]
                == 403
            )
            assert (
                "cri-o://owned" in (Path(directory) / "probe-transport.log").read_text()
            )

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


class ImmutableIndexIdentityTests(unittest.TestCase):
    def test_probe_accepts_planned_index_or_platform_digest(self):
        source = (Path(__file__).parents[1] / "wingman/qualify.py").read_text()
        assert (
            'for digest in [*platform_digests, resolved_image.split("@", 1)[1]]'
            in source
        )
