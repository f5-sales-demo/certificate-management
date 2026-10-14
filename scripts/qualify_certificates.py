"""Private-session lifecycle qualification of repository configurations with typed cleanup."""

# ruff: noqa: PLR2004, TRY301 -- HTTP codes and sequential lifecycle orchestration.
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

KINDS = {
    "xcsh_certificate": "certificates",
    "xcsh_http_loadbalancer": "http_loadbalancers",
    "xcsh_tcp_loadbalancer": "tcp_loadbalancers",
    "xcsh_cluster": "clusters",
    "xcsh_proxy": "proxys",
    "xcsh_network_connector": "network_connectors",
    "xcsh_advertise_policy": "advertise_policys",
    "xcsh_secret_management_access": "secret_management_accesss",
    "xcsh_virtual_host": "virtual_hosts",
    "xcsh_cdn_loadbalancer": "cdn_loadbalancers",
    "xcsh_bigip_http_proxy": "bigip_http_proxys",
    "xcsh_workload": "workloads",
    "xcsh_virtual_site": "virtual_sites",
    "xcsh_origin_pool": "origin_pools",
    "xcsh_nfv_service": "nfv_services",
}


def require_run_ownership(
    name: str, namespace: str, run: str, expected_namespace: str
) -> None:
    """Reject any plan object outside the current run and namespace."""
    if not name.startswith(run + "-") or namespace != expected_namespace:
        message = "Plan includes an object outside this run's ownership"
        raise ValueError(message)


def require_typed_absence(status: int) -> None:
    """Require an exact typed absence, including before every creation."""
    if status != 404:
        message = "Typed absence prerequisite returned HTTP " + str(status)
        raise ValueError(message)


def require_cleanup_owner(owned: dict, observed: dict, run: str) -> None:
    """Refuse cleanup when an ownership label or recorded identity changed."""
    labels = observed["metadata"].get("labels", {})
    if labels.get("qualification-run") != run:
        message = "Cleanup refused: ownership label mismatch"
        raise ValueError(message)
    if (
        owned.get("uid")
        and (observed.get("system_metadata") or {}).get("uid") != owned["uid"]
    ):
        message = "Cleanup refused: identity changed"
        raise ValueError(message)


# The lifecycle checkpoints stay sequential so cleanup always follows the observed write.
# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def main() -> None:
    """Qualify run-owned configurations without adopting retained resources."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument(
        "--work", type=Path, required=True, help="Private directory outside Git"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--examples", nargs="+")
    args = parser.parse_args()
    os.umask(0o077)
    root = Path(__file__).resolve().parents[1]
    if root.resolve() in args.work.resolve().parents:
        parser.error("Private work must be outside the repository")
    args.work.mkdir(parents=True, exist_ok=True, mode=0o700)
    token = os.environ["XCSH_API_TOKEN"]
    base = os.environ["XCSH_API_URL"].rstrip("/")
    if not base.startswith("https://"):
        message = "Live tenant URL must use HTTPS"
        raise ValueError(message)
    artifacts = args.artifacts.resolve()
    installed = json.loads((artifacts / "installed.json").read_text())
    env = {
        **os.environ,
        "TF_CLI_CONFIG_FILE": str(artifacts / "frozen.tfrc"),
        "TF_IN_AUTOMATION": "1",
    }
    runid = "cert-q-" + uuid.uuid4().hex[:10]
    receipt: dict[str, Any] = {
        "artifacts": installed,
        "qualification": "encrypted configuration lifecycles; served TLS requires separate proof",
        "run": runid,
        "examples": {},
    }
    journal: list[dict[str, Any]] = []

    def api(
        kind: str,
        name: str,
        method: str = "GET",
        body: dict | None = None,
        *,
        complete: bool = True,
    ) -> tuple[int, dict]:
        request = urllib.request.Request(  # noqa: S310 -- Tenant HTTPS and fixed typed routes.
            base
            + "/api/config/namespaces/"
            + args.namespace
            + "/"
            + kind
            + "/"
            + name
            + ("?response_format=2" if method == "GET" and complete else ""),
            method=method,
            data=json.dumps(body).encode() if body else None,
            headers={
                "Authorization": "APIToken " + token,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 -- Verified tenant HTTPS route.
                value = json.load(response)
                return response.status, value.get("replace_form") or value
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def save() -> None:
        (args.work / (runid + "-ownership-journal.json")).write_text(
            json.dumps(journal, indent=2) + "\n"
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        public = json.dumps(receipt, indent=2) + "\n"
        if token in public or "PRIVATE KEY-----" in public:
            message = "Secret found in receipt"
            raise ValueError(message)
        args.output.write_text(public)

    def terraform(directory: Path, stage: str, *command: str) -> bytes:
        process = subprocess.run(  # noqa: S603 -- Frozen executable and fixed Terraform argv.
            [str(artifacts / "terraform"), "-chdir=" + str(directory), *command],
            env=env,
            capture_output=True,
            timeout=600,
            check=False,
        )
        (directory / (stage + ".log")).write_bytes(process.stdout + process.stderr)
        if process.returncode:
            message = (
                stage
                + ": exit "
                + str(process.returncode)
                + "; private logs in "
                + str(directory)
            )
            raise RuntimeError(message)
        return process.stdout

    def generate(directory: Path, label: str, *, ca: bool = False) -> None:
        command = [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "2",
            "-subj",
            "/CN=tls.example.com",
            "-addext",
            "subjectAltName=DNS:tls.example.com",
            "-addext",
            "basicConstraints=critical,CA:" + ("TRUE" if ca else "FALSE"),
            "-addext",
            "keyUsage=critical,"
            + ("keyCertSign,cRLSign" if ca else "digitalSignature,keyEncipherment"),
            "-keyout",
            str(directory / (label + ".key")),
            "-out",
            str(directory / (label + ".pem")),
        ]
        if not ca:
            command.extend(["-addext", "extendedKeyUsage=serverAuth,clientAuth"])
        if label == "beta" and not ca:
            start = command.index("-newkey")
            command[start : start + 2] = [
                "-newkey",
                "ec",
                "-pkeyopt",
                "ec_paramgen_curve:P-256",
            ]
        subprocess.run(command, capture_output=True, check=True)  # noqa: S603 -- Fixed OpenSSL argv with private output paths.

    def inventory(plan: Path, directory: Path) -> None:
        changes = json.loads(
            terraform(directory, "plan-show", "show", "-json", str(plan))
        )["resource_changes"]
        for change in changes:
            if change["mode"] != "managed" or change["change"]["actions"] == ["no-op"]:
                continue
            after = change["change"]["after"]
            kind = KINDS[change["type"]]
            name = after["name"]
            require_run_ownership(name, after["namespace"], runid, args.namespace)
            if any(
                entry["kind"] == kind and entry["name"] == name for entry in journal
            ):
                continue
            status, _ = api(kind, name)
            require_typed_absence(status)
            journal.append(
                {
                    "kind": kind,
                    "name": name,
                    "namespace": args.namespace,
                    "source": str(directory),
                    "absence_before_create": 404,
                    "run": runid,
                }
            )
            save()

    def encrypted(entries: list[dict]) -> list[str]:
        found = []

        def walk(node: object) -> None:
            if isinstance(node, dict):
                if "blindfold" in node:
                    message = "Provider inputs leaked into API"
                    raise ValueError(message)
                private = node.get("private_key", {})
                if private.get("clear_secret_info"):
                    message = "Plaintext key in API"
                    raise ValueError(message)
                location = private.get("blindfold_secret_info", {}).get("location")
                if location:
                    found.append(hashlib.sha256(location.encode()).hexdigest())
                for child in node.values():
                    walk(child)
            elif isinstance(node, list):
                for child in node:
                    walk(child)

        for entry in entries:
            status, value = api(entry["kind"], entry["name"])
            if status != 200:
                message = "Owned resource readback failed"
                raise ValueError(message)
            _, identity = api(entry["kind"], entry["name"], complete=False)
            entry["uid"] = (identity.get("system_metadata") or {}).get("uid")

            walk(value.get("spec", {}))
        if not found:
            message = "No encrypted certificate material in typed API readback"
            raise ValueError(message)
        return sorted(found)

    sources = args.examples or sorted(
        path.parent.name for path in (root / "terraform").glob("*/versions.tf")
    )
    for source in sources:
        entry: dict[str, Any] = {
            "configuration_lifecycle": "failed",
            "cleanup": "pending",
            "served_tls": "not_exercised",
        }
        receipt["examples"][source] = entry
        directory = args.work / (runid + "-" + source.replace("/", "-"))
        directory.mkdir()
        source_dir = root / "terraform" / source
        reference = not (source_dir / "versions.tf").exists()
        for file in source_dir.glob("*.tf.example" if reference else "*.tf"):
            shutil.copyfile(file, directory / file.name.removesuffix(".example"))
        entry["source_sha256"] = {
            file.name: hashlib.sha256(file.read_bytes()).hexdigest()
            for file in sorted(source_dir.glob("*.tf*"))
        }
        mainfile = directory / "main.tf"
        original = mainfile.read_text()
        text = re.sub(
            r'labels\s*=\s*\{ certificate-example = "terraform" \}',
            'labels = { certificate-example = "terraform", qualification-run = "'
            + runid
            + '" }',
            original,
        )
        if source == "named-certificate":
            text = text[: text.index('resource "xcsh_http_loadbalancer" "http"')]
        text = re.sub(
            r"advertise_on_public_default_vip\s*=\s*\{\}", "do_not_advertise = {}", text
        )
        mainfile.write_text(text)
        entry["qualification_adaptations"] = [
            "No public advertisement or DNS registration",
            "Run-owned names and labels",
            "Empty CE selector for workload lifecycle only",
        ]
        generate(directory, "alpha", ca="intercept" in source)
        generate(directory, "beta", ca="intercept" in source)
        generate(directory, "trust", ca=True)
        generate(directory, "renewed", ca="intercept" in source)
        variables = {
            "namespace": args.namespace,
            "name": runid
            + "-"
            + source.replace("reference/", "").replace("_", "-")[:35].rstrip("-"),
            "domain": "tls.example.com",
            "certificate_file": str(directory / "alpha.pem"),
            "private_key_file": str(directory / "alpha.key"),
            "origin_hostname": "tls.example.com",
            "origin_ca_file": str(directory / "trust.pem"),
            "virtual_site_name": runid
            + "-"
            + source.replace("reference/", "").replace("_", "-")[:25].rstrip("-")
            + "-selector",
            "virtual_site_namespace": args.namespace,
        }
        declared = re.findall(
            r'variable "([^"]+)"', (directory / "variables.tf").read_text()
        )
        variables = {key: value for key, value in variables.items() if key in declared}
        if "certificates" in declared:
            variables["certificates"] = [
                {
                    "id": "alpha",
                    "certificate_file": str(directory / "alpha.pem"),
                    "private_key_file": str(directory / "alpha.key"),
                }
            ]
        if "virtual_site_name" in declared:
            (directory / "selector.tf").write_text(
                'resource "xcsh_virtual_site" "qualification" {\n name = var.virtual_site_name\n namespace = var.namespace\n labels = { qualification-run = "'
                + runid
                + '" }\n site_type = "CUSTOMER_EDGE"\n site_selector { expressions = ["example.test/certificate-qualification=never-match"] }\n}\n'
            )
        varsfile = directory / "owner.auto.tfvars.json"

        def write_vars(values: dict = variables, destination: Path = varsfile) -> None:
            destination.write_text(json.dumps(values))

        owned = []
        previous: list[str] = []
        try:
            write_vars()
            terraform(directory, "init", "init", "-upgrade", "-input=false")
            versions = json.loads(terraform(directory, "versions", "version", "-json"))
            if (
                versions["provider_selections"][
                    "registry.terraform.io/f5-sales-demo/xcsh"
                ]
                != installed["provider"]["version"]
            ):
                message = "Provider selection differs from frozen publication"
                raise ValueError(message)
            stages = (
                ("initial", "insert", "reorder", "remove", "metadata", "renewal")
                if "certificates" in declared
                else ("initial", "metadata", "renewal")
            )
            for stage in stages:
                if stage == "insert":
                    variables["certificates"].append(
                        {
                            "id": "beta",
                            "certificate_file": str(directory / "beta.pem"),
                            "private_key_file": str(directory / "beta.key"),
                        }
                    )
                if stage == "reorder":
                    variables["certificates"].reverse()
                if stage == "remove":
                    variables["certificates"] = [
                        certificate
                        for certificate in variables["certificates"]
                        if certificate["id"] == "alpha"
                    ]
                if stage == "metadata":
                    variables["description"] = "Run-owned certificate metadata edit"
                if stage == "renewal":
                    variables["certificate_file"] = str(directory / "renewed.pem")
                    variables["private_key_file"] = str(directory / "renewed.key")
                    if "certificates" in declared:
                        variables["certificates"] = [
                            {
                                "id": "alpha",
                                "certificate_file": str(directory / "renewed.pem"),
                                "private_key_file": str(directory / "renewed.key"),
                            }
                        ]
                write_vars()
                plan = directory / (stage + ".plan")
                terraform(
                    directory,
                    stage + "-plan",
                    "plan",
                    "-input=false",
                    "-out=" + str(plan),
                )
                inventory(plan, directory)
                owned = [
                    value for value in journal if value["source"] == str(directory)
                ]
                terraform(
                    directory, stage + "-apply", "apply", "-input=false", str(plan)
                )
                terraform(
                    directory,
                    stage + "-empty",
                    "plan",
                    "-input=false",
                    "-detailed-exitcode",
                )
                current = encrypted(owned)
                if stage in ("metadata", "reorder") and current != previous:
                    message = "Metadata edit changed encrypted material"
                    raise ValueError(message)
                if stage == "insert" and not set(previous).issubset(current):
                    message = "Insertion changed existing encrypted material"
                    raise ValueError(message)
                if stage == "remove" and not set(current).issubset(previous):
                    message = "Removal changed retained encrypted material"
                    raise ValueError(message)
                if stage == "renewal" and current == previous:
                    message = "Renewal did not change encrypted material"
                    raise ValueError(message)
                previous = current
                entry[stage] = "passed"
                save()
            terraform(
                directory, "restart-empty", "plan", "-input=false", "-detailed-exitcode"
            )
            state = (directory / "terraform.tfstate").read_bytes()
            if token.encode() in state or b"PRIVATE KEY-----" in state:
                message = "Secret found in state"
                raise ValueError(message)
            entry["configuration_lifecycle"] = "passed"
            entry["encryption_readback"] = "passed"
            entry["secret_containment"] = "passed"  # noqa: S105 -- Public gate marker, not a credential.
        except (
            RuntimeError,
            ValueError,
            AssertionError,
            OSError,
            KeyError,
            subprocess.SubprocessError,
        ) as error:
            entry["failure"] = str(error).split("; private logs", maxsplit=1)[0]
        finally:
            owned = [value for value in journal if value["source"] == str(directory)]
            if owned:
                try:
                    terraform(
                        directory,
                        "destroy-plan",
                        "plan",
                        "-destroy",
                        "-input=false",
                        "-out=" + str(directory / "destroy.plan"),
                    )
                    terraform(
                        directory,
                        "destroy",
                        "apply",
                        "-input=false",
                        str(directory / "destroy.plan"),
                    )
                except (
                    RuntimeError,
                    ValueError,
                    AssertionError,
                    OSError,
                    KeyError,
                    subprocess.SubprocessError,
                ) as cleanup_error:
                    entry["terraform_cleanup_failure"] = str(cleanup_error).split(
                        "; private logs", maxsplit=1
                    )[0]
                for value in reversed(owned):
                    status, body = api(value["kind"], value["name"], complete=False)
                    if status == 200:
                        require_cleanup_owner(value, body, runid)
                        status, _ = api(value["kind"], value["name"], "DELETE", {})
                        if status not in (200, 202):
                            message = "Typed cleanup DELETE failed"
                            raise ValueError(message)
                for pass_number in (1, 2):
                    for value in owned:
                        if api(value["kind"], value["name"])[0] != 404:
                            message = "Typed cleanup absence check failed"
                            raise ValueError(message)
                        value["absence_" + str(pass_number)] = 404
                    time.sleep(1)
            entry["cleanup"] = "typed_absence_twice" if owned else "no_objects_created"
            save()
        print(
            source + ": " + entry["configuration_lifecycle"] + "; " + entry["cleanup"],
            flush=True,
        )
    if any(
        value["configuration_lifecycle"] != "passed"
        for value in receipt["examples"].values()
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
