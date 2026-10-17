"""Observe Terraform-owned Wingman probes; preserve legacy exact-UID cleanup."""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit


def require_image(image: str) -> None:
    """Accept only governed latest and immutable application references."""
    if not re.fullmatch(
        r"ghcr.io/f5-sales-demo/certificate-management-wingman(?::latest|@sha256:[a-f0-9]{64})",
        image,
    ):
        message = "A governed latest or immutable application image is required"
        raise ValueError(message)


def planned_image(inventory: dict, selected: str) -> tuple[str, list[str]]:
    """Bind observation to the immutable image recorded by the reviewed plan."""
    resolved = inventory.get("resolved_image", "")
    require_image(resolved)
    platforms = inventory.get("platform_digests", [])
    if (
        inventory.get("requested_image") != selected
        or "@sha256:" not in resolved
        or not platforms
    ):
        message = "Planned application image differs from the selected publication"
        raise ValueError(message)
    for digest in platforms:
        require_image("ghcr.io/f5-sales-demo/certificate-management-wingman@" + digest)
    return resolved, platforms


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


def terraform_inventory(document: dict, namespace: str) -> tuple[str, list[dict]]:
    """Accept only the three exact Deployment identities exported by Terraform."""
    run = document.get("run", "")
    entries = document.get("entries", [])
    expected = [
        ("probe-authorized", "encrypted-location"),
        ("probe-authorized", "encrypted-location-xcsh"),
        ("probe-denied", "encrypted-location"),
    ]
    if not re.fullmatch(r"wingman-q-[a-f0-9]{12}", run) or len(entries) != PROBE_COUNT:
        message = "Invalid Terraform qualification inventory"
        raise ValueError(message)
    for index, (entry, case) in enumerate(zip(entries, expected, strict=True)):
        if (
            entry.get("name") != run + "-" + str(index)
            or entry.get("namespace") != namespace
            or entry.get("kind") != "deployment"
            or not entry.get("uid")
            or (entry.get("mode"), entry.get("source")) != case
        ):
            message = "Terraform inventory identity or probe case differs"
            raise ValueError(message)
        entry.setdefault("pods", {})
    return run, entries


def require_probe_contract(
    pod: dict, mode: str, source: str, image: str, domain: str, selector: dict
) -> None:
    """Reject a changed image, probe invocation, material source, or policy label."""
    containers = [
        item
        for item in pod.get("spec", {}).get("containers", [])
        if item.get("name") == "application"
    ]
    if len(containers) != 1:
        message = "Expected one application probe container"
        raise ValueError(message)
    container = containers[0]
    environment = {item["name"]: item.get("value") for item in container.get("env", [])}
    if (
        container.get("image") != image
        or container.get("command") != ["/wingman-app", mode]
        or environment.get("TLS_HOSTNAME") != domain
        or environment.get("PROBE_LOCATION_FILE") != "/material/" + source
        or any(
            pod.get("metadata", {}).get("labels", {}).get(key) != value
            for key, value in selector.items()
        )
    ):
        message = "Live probe differs from the planned qualification contract"
        raise ValueError(message)


def probe_deadline(
    pod: dict, now: float, startup_deadline: float, execution_deadline: float | None
) -> tuple[float, float | None]:
    """Give container creation a separate bound without extending a running probe."""
    started = any(
        c.get("name") == "application"
        and (
            c.get("started")
            or c.get("state", {}).get("running")
            or c.get("state", {}).get("terminated")
            or c.get("lastState", {}).get("terminated")
        )
        for c in pod.get("status", {}).get("containerStatuses", [])
    )
    if started and execution_deadline is None:
        execution_deadline = now + 180
    return (
        startup_deadline if execution_deadline is None else execution_deadline,
        execution_deadline,
    )


def read_probe_output(
    command: Callable[..., subprocess.CompletedProcess],
    pod_name: str,
    previous: bool,
    output_file: Path,
) -> dict:
    """Collect completed container logs across a restart without invoking the probe."""
    choices = (previous, not previous)
    deadline = time.monotonic() + 10
    while True:
        errors = 0
        for use_previous in choices:
            options = ["--previous"] if use_previous else []
            log = command("logs", pod_name, "-c", "application", *options)
            output_file.write_text(log.stdout + log.stderr)
            output_file.chmod(0o600)
            if log.returncode or log.stdout.startswith(
                "unable to retrieve container logs for "
            ):
                # The observed vK8s log proxy can return its CRI error with exit 0.
                # Preserve transport diagnostics separately from application output.
                transport = output_file.with_name(output_file.stem + "-transport.log")
                with transport.open("a") as stream:
                    stream.write(log.stdout + log.stderr)
                transport.chmod(0o600)
                errors += 1
            elif log.stdout.strip():
                return json.loads(log.stdout)
        if errors == len(choices) or time.monotonic() >= deadline:
            message = "Completed probe output unavailable; private diagnostics retained"
            raise RuntimeError(message)
        time.sleep(0.5)


def probe_timeout(
    directory: Path, name: str, pod: dict, execution_deadline: float | None
) -> str:
    """Retain private phase diagnostics before exact owned cleanup."""
    phase = "pod startup" if execution_deadline is None else "probe execution"
    diagnostic = directory / (name + "-timeout.json")
    diagnostic.write_text(
        json.dumps({"phase": phase, "status": pod.get("status", {})}, indent=2) + "\n"
    )
    diagnostic.chmod(0o600)
    return (
        "Probe pod did not start before startup deadline"
        if execution_deadline is None
        else "Real Wingman probe did not finish before execution deadline"
    )


# Preserve sequential qualification and reverse cleanup in one visible ownership transaction.
# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def main() -> None:
    """Run scoped probes and verify their exact owned cleanup."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubeconfig", type=Path, required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument(
        "--inventory", type=Path, help="Terraform output -json probe_inventory"
    )
    parser.add_argument(
        "--verify-owned",
        action="store_true",
        help="Read-only UID check before a saved destroy plan",
    )
    parser.add_argument(
        "--verify-cleanup",
        action="store_true",
        help="Read-only absence check after Terraform destroy",
    )
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
    observe = not (args.cleanup_only or args.verify_cleanup or args.verify_owned)
    if sum((args.cleanup_only, args.verify_cleanup, args.verify_owned)) > 1:
        parser.error("Select only one recovery or verification mode")
    if not args.cleanup_only and args.inventory is None:
        parser.error(
            "Terraform --inventory is required; this tool does not create probes"
        )
    if observe and not all((args.name, args.image, args.domain, args.fingerprint)):
        parser.error(
            "qualification requires --name, --image, --domain and --fingerprint"
        )
    if observe and not re.fullmatch(r"[a-f0-9]{64}", args.fingerprint):
        parser.error("fingerprint must be a SHA-256 hex digest")
    if not args.kubeconfig.is_absolute() or not args.kubeconfig.is_file():
        msg = "An explicit private kubeconfig file is required"
        raise ValueError(msg)
    contract = json.loads((Path(__file__).parent / "contract.json").read_text())
    if observe:
        require_image(args.image)
    resolved_image = ""
    platform_digests: list[str] = []
    if args.cleanup_only or args.verify_cleanup or args.verify_owned:
        document = json.loads((args.private_directory / "journal.json").read_text())
        run, journal = document["run"], document["entries"]
        if args.inventory:
            inventory_run, inventory_entries = terraform_inventory(
                json.loads(args.inventory.read_text()), args.namespace
            )
            if inventory_run != run or [e["uid"] for e in inventory_entries] != [
                e["uid"] for e in journal
            ]:
                message = "Terraform inventory differs from observation journal"
                raise ValueError(message)
        if not re.fullmatch(r"wingman-q-[a-f0-9]{12}", run):
            message = "Invalid run-owned cleanup journal"
            raise ValueError(message)
        if any(entry.get("namespace") != args.namespace for entry in journal):
            message = "Cleanup namespace differs from private journal"
            raise ValueError(message)
        if args.cleanup_only and document.get("ownership") == "terraform":
            parser.error(
                "Terraform-owned probes require a saved destroy plan, then --verify-cleanup"
            )
    else:
        inventory = json.loads(args.inventory.read_text())
        resolved_image, platform_digests = planned_image(inventory, args.image)
        run, journal = terraform_inventory(inventory, args.namespace)
        args.private_directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    results: dict = {
        "qualification": "cleanup only; unseal not exercised"
        if not observe
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
        path.write_text(
            json.dumps(
                {
                    "run": run,
                    "entries": journal,
                    "ownership": "legacy" if args.cleanup_only else "terraform",
                },
                indent=2,
            )
            + "\n"
        )
        path.chmod(0o600)

    def retain_failure(name: str, pod_name: str) -> None:
        """Save failed application logs privately before cleanup."""
        failure = command("logs", pod_name, "-c", "application", "--previous")
        if failure.returncode:
            failure = command("logs", pod_name, "-c", "application")
        diagnostic = args.private_directory / (name + "-failure.log")
        diagnostic.write_text(failure.stdout + failure.stderr)
        diagnostic.chmod(0o600)

    succeeded = False
    try:
        save()
        if args.verify_owned:
            for entry in journal:
                deployed = get(entry["name"])
                if deployed is None:
                    message = "Terraform-owned Deployment disappeared before destroy"
                    raise RuntimeError(message)
                require_owner(
                    deployed, entry["name"], args.namespace, run, entry["uid"]
                )
                for generated in pods(entry):
                    if generated["metadata"]["name"] not in entry["pods"]:
                        message = "Probe pod identity changed before destroy"
                        raise RuntimeError(message)
                    require_owner(
                        generated,
                        generated["metadata"]["name"],
                        args.namespace,
                        run,
                        entry["pods"].get(generated["metadata"]["name"], ""),
                    )
        for entry in journal if observe else []:
            name, mode, source = entry["name"], entry["mode"], entry["source"]
            startup_deadline = time.monotonic() + 600
            execution_deadline = None
            deadline = startup_deadline
            while True:
                job = get(name)
                if job is None:
                    msg = "Probe disappeared before qualification"
                    raise RuntimeError(msg)
                require_owner(job, name, args.namespace, run, entry["uid"])
                observed = pods(entry)
                if len(observed) > 1:
                    message = (
                        "Probe Deployment produced more than one pod; "
                        "site cardinality is unqualified"
                    )
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
                require_probe_contract(
                    pod,
                    mode,
                    source,
                    resolved_image,
                    args.domain,
                    {
                        contract["app_label"]: args.name
                        + contract["suffixes"]["application"]
                        if mode == "probe-authorized"
                        else name
                    },
                )
                pod_name = pod["metadata"]["name"]
                pod_uid = require_owner(
                    pod, pod_name, args.namespace, run, entry["pods"].get(pod_name, "")
                )
                entry["pods"][pod_name] = pod_uid
                save()
                deadline, execution_deadline = probe_deadline(
                    pod, time.monotonic(), startup_deadline, execution_deadline
                )
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
                        retain_failure(name, pod_name)
                        msg = "Real injected Wingman probe failed"
                        raise RuntimeError(msg)
                    break
                if time.monotonic() >= deadline:
                    msg = probe_timeout(
                        args.private_directory, name, pod, execution_deadline
                    )
                    raise RuntimeError(msg)
                time.sleep(2)
            container_status = next(
                c
                for c in pod["status"]["containerStatuses"]
                if c["name"] == "application"
            )
            image_id = container_status.get("imageID", "")
            if not any(image_id.endswith(digest) for digest in platform_digests):
                message = "Resolved application image digest is missing"
                raise RuntimeError(message)
            evidence = read_probe_output(
                command,
                pod_name,
                not bool(container_status.get("state", {}).get("terminated")),
                args.private_directory / (name + "-output.log"),
            )
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
                    "resolved_image_id": image_id,
                }
            )
        succeeded = True
    finally:
        for entry in reversed(journal) if args.cleanup_only else []:
            legacy_workload = get(entry["name"], entry.get("kind", "job"))
            if legacy_workload is not None:
                uid = require_owner(
                    legacy_workload, entry["name"], args.namespace, run, entry["uid"]
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
        for check in range(2) if args.cleanup_only or args.verify_cleanup else []:
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
            "cleanup-result.json"
            if args.cleanup_only or args.verify_cleanup
            else "ownership-result.json"
            if args.verify_owned
            else "result.json"
        )
        output.write_text(json.dumps(results, indent=2) + "\n")
        output.chmod(0o600)
    if observe and len(results["probes"]) != PROBE_COUNT:
        msg = "Fresh qualification incomplete"
        raise RuntimeError(msg)
    sys.stdout.write(
        "Owned cleanup verified twice. Receipt is in private session storage.\n"
        if args.cleanup_only or args.verify_cleanup
        else "Terraform-owned identities verified.\n"
        if args.verify_owned
        else "Fresh Wingman probes passed. Destroy through the saved Terraform plan, then verify cleanup.\n"
    )


if __name__ == "__main__":
    os.umask(0o077)
    main()
