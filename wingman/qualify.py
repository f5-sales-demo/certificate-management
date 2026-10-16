"""Qualify real injected Wingman probe pods and delete only this run's exact UIDs."""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

DIGEST_LENGTH = 64
HTTP_FORBIDDEN = 403
PROBE_COUNT = 3


def raw_resource_uri(server: str, path: str) -> str:
    """Keep the scoped vK8s server prefix when kubectl uses a raw URI."""
    parsed = urlsplit(server)
    if (
        parsed.scheme != "https"
        or parsed.query
        or parsed.fragment
        or not path.startswith("/")
    ):
        message = "Unsafe scoped Kubernetes resource URI"
        raise ValueError(message)
    return parsed.path.rstrip("/") + path


def require_owner(pod: dict, name: str, namespace: str, run: str, uid: str = "") -> str:
    """Reject changed or foreign identities before deleting a probe."""
    meta = pod.get("metadata", {})
    actual = meta.get("uid", "")
    if (
        (
            meta.get("name"),
            meta.get("namespace"),
            meta.get("labels", {}).get("qualification-run"),
        )
        != (name, namespace, run)
        or not actual
        or (uid and actual != uid)
    ):
        msg = "Probe ownership changed; cleanup refused"
        raise ValueError(msg)
    return actual


# Preserve sequential qualification and reverse cleanup in one visible ownership transaction.
# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def main() -> None:
    """Run scoped probes and verify their exact owned cleanup."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubeconfig", type=Path, required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--name")
    parser.add_argument("--image")
    parser.add_argument("--domain")
    parser.add_argument("--fingerprint")
    parser.add_argument("--private-directory", type=Path, required=True)
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Resume exact-UID cleanup from the existing private journal",
    )
    args = parser.parse_args()
    if not args.cleanup_only and not all(
        (args.name, args.image, args.domain, args.fingerprint)
    ):
        parser.error(
            "qualification requires --name, --image, --domain and --fingerprint"
        )
    if not args.cleanup_only and not re.fullmatch(r"[a-f0-9]{64}", args.fingerprint):
        parser.error("fingerprint must be a SHA-256 hex digest")
    if not args.kubeconfig.is_absolute() or not args.kubeconfig.is_file():
        msg = "An explicit private kubeconfig file is required"
        raise ValueError(msg)
    contract = json.loads((Path(__file__).parent / "contract.json").read_text())
    image_prefix = "ghcr.io/f5-sales-demo/certificate-management-wingman@sha256:"
    digest = (args.image or "").removeprefix(image_prefix)
    if not args.cleanup_only and (
        not (args.image or "").startswith(image_prefix)
        or len(digest) != DIGEST_LENGTH
        or any(c not in "0123456789abcdef" for c in digest)
    ):
        msg = "An immutable governed application image is required"
        raise ValueError(msg)
    if args.cleanup_only:
        document = json.loads((args.private_directory / "journal.json").read_text())
        run, journal = document["run"], document["entries"]
        if not re.fullmatch(r"wingman-q-[a-f0-9]{12}", run):
            msg_0 = "Invalid run-owned cleanup journal"
            raise ValueError(msg_0)
        if any(entry.get("namespace") != args.namespace for entry in journal):
            msg_0 = "Cleanup namespace differs from private journal"
            raise ValueError(msg_0)
    else:
        args.private_directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        run = "wingman-q-" + uuid.uuid4().hex[:12]
        journal = []
    results: dict = {
        "qualification": "cleanup only; unseal not exercised"
        if args.cleanup_only
        else "fresh live Wingman unseal",
        "run": run,
        "probes": [],
    }
    kubectl = [
        "kubectl",
        "--kubeconfig",
        str(args.kubeconfig),
        "--context",
        args.context,
        "--namespace",
        args.namespace,
    ]

    def command(*argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(  # noqa: S603 -- Fixed kubectl argv and explicit context; no shell.
            [*kubectl, *argv], capture_output=True, text=True, timeout=30, check=False
        )

    config = command("config", "view", "--minify", "-o", "json")
    if config.returncode:
        message = "Explicit kubeconfig server could not be verified"
        raise RuntimeError(message)
    clusters = json.loads(config.stdout)["clusters"]
    if len(clusters) != 1:
        message = "Explicit kubeconfig must select one cluster"
        raise ValueError(message)
    server = clusters[0]["cluster"]["server"]

    def get(name: str, kind: str = "deployment") -> dict | None:
        result = command("get", kind, name, "--ignore-not-found", "-o", "json")
        if result.returncode:
            msg = "Probe read failed; permission or transport errors are not absence"
            raise RuntimeError(msg)
        return json.loads(result.stdout) if result.stdout.strip() else None

    def pods(entry: dict, kind: str = "pods") -> list[dict]:
        result = command(
            "get",
            kind,
            "-l",
            "qualification-run=" + run + ",qualification-probe=" + entry["name"],
            "-o",
            "json",
        )
        if result.returncode:
            message = "Probe pod listing failed; absence is unverified"
            raise RuntimeError(message)
        return json.loads(result.stdout)["items"]

    def save() -> None:
        path = args.private_directory / "journal.json"
        path.write_text(json.dumps({"run": run, "entries": journal}, indent=2) + "\n")
        path.chmod(0o600)

    succeeded = False
    try:
        cases = (
            []
            if args.cleanup_only
            else [
                ("probe-authorized", "encrypted-location"),
                ("probe-authorized", "encrypted-location-xcsh"),
                ("probe-denied", "encrypted-location"),
            ]
        )
        for mode, source in cases:
            name = run + "-" + str(len(journal))
            entry: dict[str, Any] = {
                "name": name,
                "namespace": args.namespace,
                "uid": "",
                "kind": "deployment",
                "pods": {},
            }
            journal.append(entry)
            save()  # Journal intent before one create; reconcile an ambiguous result by exact GET.
            app = (
                args.name + contract["suffixes"]["application"]
                if mode == "probe-authorized"
                else name
            )
            manifest: dict[str, Any] = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": name,
                    "namespace": args.namespace,
                    "labels": {
                        contract["app_label"]: app,
                        "qualification-run": run,
                        "qualification-probe": name,
                    },
                    "annotations": {"ves.io/wingman-injection-mode": "enable"},
                },
                "spec": {
                    "restartPolicy": "Always",
                    "containers": [
                        {
                            "name": "application",
                            "image": args.image,
                            "command": ["/wingman-app", mode],
                            "resources": {
                                "requests": {"cpu": "50m", "memory": "32Mi"},
                                "limits": {"cpu": "250m", "memory": "128Mi"},
                            },
                            "env": [
                                {"name": "TLS_HOSTNAME", "value": args.domain},
                                {
                                    "name": "PROBE_LOCATION_FILE",
                                    "value": "/material/" + source,
                                },
                            ],
                            "volumeMounts": [
                                {
                                    "name": "material",
                                    "mountPath": "/material",
                                    "readOnly": True,
                                }
                            ],
                        }
                    ],
                    "volumes": [
                        {
                            "name": "material",
                            "configMap": {
                                "name": args.name + contract["suffixes"]["material"]
                            },
                        }
                    ],
                },
            }
            # Use Deployments: observed Job pods disable Wingman injection.
            manifest = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": name,
                    "namespace": args.namespace,
                    "labels": manifest["metadata"]["labels"],
                },
                "spec": {
                    "replicas": 1,
                    "selector": {"matchLabels": manifest["metadata"]["labels"]},
                    "template": {
                        "metadata": {
                            "labels": manifest["metadata"]["labels"],
                            "annotations": manifest["metadata"]["annotations"],
                        },
                        "spec": manifest["spec"],
                    },
                },
            }
            path = args.private_directory / (name + ".json")
            path.write_text(json.dumps(manifest))
            created = command("create", "-f", str(path), "-o", "json")
            pod = get(name)
            if pod is None:
                msg = "Probe create has no named readback; no replay occurred"
                raise RuntimeError(msg)
            entry["uid"] = require_owner(pod, name, args.namespace, run)
            save()
            if created.returncode:
                msg = "Probe create outcome was ambiguous; owned readback journaled for cleanup"
                raise RuntimeError(msg)
            deadline = time.monotonic() + 180
            while True:
                job = get(name)
                if job is None:
                    msg = "Probe disappeared before qualification"
                    raise RuntimeError(msg)
                require_owner(job, name, args.namespace, run, entry["uid"])
                observed = pods(entry)
                if len(observed) > 1:
                    message = "Probe Deployment produced more than one pod; site cardinality is unqualified"
                    raise RuntimeError(message)
                if not observed:
                    if time.monotonic() >= deadline:
                        message = (
                            "Probe Deployment did not produce a pod before deadline"
                        )
                        raise RuntimeError(message)
                    time.sleep(2)
                    continue
                pod = observed[0]
                pod_name = pod["metadata"]["name"]
                pod_uid = require_owner(
                    pod, pod_name, args.namespace, run, entry["pods"].get(pod_name, "")
                )
                entry["pods"][pod_name] = pod_uid
                save()
                injected = [
                    c
                    for c in pod.get("spec", {}).get("containers", [])
                    if "wingman" in c.get("name", "").lower()
                    and c.get("name") != "application"
                ]
                terminated = next(
                    (
                        (
                            c.get("state", {}).get("terminated")
                            or c.get("lastState", {}).get("terminated")
                        )
                        for c in pod.get("status", {}).get("containerStatuses", [])
                        if c.get("name") == "application"
                    ),
                    None,
                )
                if terminated:
                    if terminated.get("exitCode") != 0 or not injected:
                        msg = "Real injected Wingman probe failed"
                        raise RuntimeError(msg)
                    break
                if time.monotonic() >= deadline:
                    msg = "Real Wingman probe did not finish before deadline"
                    raise RuntimeError(msg)
                time.sleep(2)
            container_status = next(
                c
                for c in pod["status"]["containerStatuses"]
                if c["name"] == "application"
            )
            previous = (
                []
                if container_status.get("state", {}).get("terminated")
                else ["--previous"]
            )
            log = command("logs", pod_name, "-c", "application", *previous)
            if log.returncode:
                msg = "Probe evidence read failed"
                raise RuntimeError(msg)
            evidence = json.loads(log.stdout)
            if (
                mode == "probe-authorized"
                and evidence.get("certificate_sha256") != args.fingerprint
            ):
                msg = "Unsealed application material differs from retained fingerprint"
                raise RuntimeError(msg)
            if mode == "probe-denied" and (
                evidence.get("http_status") != HTTP_FORBIDDEN
                or evidence.get("denied") is not True
            ):
                msg = "Unselected pod did not prove denial"
                raise RuntimeError(msg)
            identities = evidence.get("identities", {})
            if set(identities) != {"client_identity_sha256", "server_identity_sha256"}:
                msg = "Pod identity trust evidence missing"
                raise RuntimeError(msg)
            results["probes"].append(
                {
                    "mode": mode,
                    "source": source,
                    "evidence": evidence,
                    "sidecar_injected": True,
                }
            )
        succeeded = True
    finally:
        for entry in reversed(journal):
            pod = get(entry["name"], entry.get("kind", "job"))
            if pod is not None:
                uid = require_owner(
                    pod, entry["name"], args.namespace, run, entry["uid"]
                )
                entry["uid"] = uid
                save()
                # API-server UID precondition closes the read/delete ownership race.
                options = args.private_directory / "delete-options.json"
                options.write_text(
                    json.dumps(
                        {
                            "apiVersion": "v1",
                            "kind": "DeleteOptions",
                            "preconditions": {"uid": uid},
                            "propagationPolicy": "Background",
                        }
                    )
                )
                deleted = command(
                    "delete",
                    "--raw",
                    raw_resource_uri(
                        server,
                        (
                            "/apis/apps/v1/namespaces/"
                            if entry.get("kind") == "deployment"
                            else "/apis/batch/v1/namespaces/"
                        )
                        + args.namespace
                        + (
                            "/deployments/"
                            if entry.get("kind") == "deployment"
                            else "/jobs/"
                        )
                        + entry["name"],
                    ),
                    "-f",
                    str(options),
                )
                if deleted.returncode:
                    msg = "Owned probe cleanup failed; private journal retained"
                    raise RuntimeError(msg)
            for generated in pods(entry):
                generated_name = generated["metadata"]["name"]
                generated_uid = require_owner(
                    generated,
                    generated_name,
                    args.namespace,
                    run,
                    entry.get("pods", {}).get(generated_name, ""),
                )
                entry.setdefault("pods", {})[generated_name] = generated_uid
                save()
                options = args.private_directory / "delete-options.json"
                options.write_text(
                    json.dumps(
                        {
                            "apiVersion": "v1",
                            "kind": "DeleteOptions",
                            "preconditions": {"uid": generated_uid},
                        }
                    )
                )
                deleted = command(
                    "delete",
                    "--raw",
                    raw_resource_uri(
                        server,
                        "/api/v1/namespaces/"
                        + args.namespace
                        + "/pods/"
                        + generated_name,
                    ),
                    "-f",
                    str(options),
                )
                if deleted.returncode and get(generated_name, "pod") is not None:
                    message = "Generated probe pod cleanup failed"
                    raise RuntimeError(message)
        for check in range(2):
            deadline = time.monotonic() + 90
            while any(
                get(entry["name"], entry.get("kind", "job")) is not None
                or pods(entry)
                or (entry.get("kind") == "deployment" and pods(entry, "replicasets"))
                for entry in journal
            ):
                if time.monotonic() >= deadline:
                    msg = "Probe cleanup absence not verified"
                    raise RuntimeError(msg)
                time.sleep(2)
            results["cleanup_pass_" + str(check + 1)] = "typed absence"
        results["status"] = "passed" if succeeded else "failed"
        output = args.private_directory / (
            "cleanup-result.json" if args.cleanup_only else "result.json"
        )
        output.write_text(json.dumps(results, indent=2) + "\n")
        output.chmod(0o600)
    if not args.cleanup_only and len(results["probes"]) != PROBE_COUNT:
        msg = "Fresh qualification incomplete"
        raise RuntimeError(msg)
    sys.stdout.write(
        "Owned cleanup verified twice. Receipt is in private session storage.\n"
        if args.cleanup_only
        else "Fresh Wingman probes passed; cleanup verified twice. Receipt is in private session storage.\n"
    )


if __name__ == "__main__":
    os.umask(0o077)
    main()
