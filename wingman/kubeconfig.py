"""Issue or revoke one scoped one-day kubeconfig outside Terraform state."""

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from email.message import Message
from http.client import HTTPResponse
from pathlib import Path


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    """Never forward a session token to a redirected credential endpoint."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: HTTPResponse,
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> None:
        """Reject every redirect before another request is sent."""
        msg_0 = "Credential API redirect rejected"
        raise RuntimeError(msg_0)


def request(base: str, token: str, path: str, body: dict | None = None) -> dict:
    """Send one HTTPS credential request and omit private response content from errors."""
    if urllib.parse.urlsplit(base).scheme != "https":
        message = "Credential API origin must use HTTPS"
        raise ValueError(message)
    headers = {"Authorization": "APIToken " + token}
    data = None if body is None else json.dumps(body).encode()
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=headers)  # noqa: S310 -- HTTPS origin checked before construction.
    try:
        # No application retry: ambiguous issuance must be reconciled by exact name.
        with urllib.request.build_opener(RejectRedirects()).open(
            req, timeout=30
        ) as response:
            result = response.read(2 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as error:
        raise RuntimeError("Credential API returned HTTP " + str(error.code)) from None
    except urllib.error.URLError:
        msg = "Credential API unavailable; no replay occurred"
        raise RuntimeError(msg) from None
    if len(result) > 2 * 1024 * 1024:
        msg = "Credential response exceeds limit"
        raise RuntimeError(msg)
    try:
        return json.loads(result)
    except (UnicodeError, ValueError):
        msg = "Credential API returned an invalid JSON document"
        raise RuntimeError(msg) from None


def main() -> None:
    """Issue or revoke one journaled scoped credential without storing it in state."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["issue", "revoke"])
    parser.add_argument("--private-directory", type=Path, required=True)
    parser.add_argument("--namespace")
    parser.add_argument("--vk8s")
    args = parser.parse_args()
    base = os.environ["XCSH_API_URL"].rstrip("/").removesuffix("/api")
    token = os.environ["XCSH_API_TOKEN"]
    parsed = urllib.parse.urlsplit(base)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path
    ):
        msg = "Use an HTTPS tenant console origin"
        raise ValueError(msg)
    if not args.private_directory.is_absolute():
        msg = "Private session directory must be an absolute path"
        raise ValueError(msg)
    journal = args.private_directory / "credential.json"
    if args.operation == "issue":
        if not args.namespace or not args.vk8s:
            parser.error("issue requires --namespace and --vk8s")
        args.private_directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        name = "wingman-session-" + uuid.uuid4().hex[:16]
        record = {
            "api_origin": base,
            "name": name,
            "namespace": args.namespace,
            "vk8s": args.vk8s,
            "status": "issuance-pending",
        }
        journal.write_text(json.dumps(record, indent=2) + "\n")
        response = request(
            base,
            token,
            "/api/web/namespaces/system/api_credentials",
            {
                "name": name,
                "namespace": "system",
                "expiration_days": 1,
                "spec": {
                    "type": "KUBE_CONFIG",
                    "virtual_k8s_name": args.vk8s,
                    "virtual_k8s_namespace": args.namespace,
                },
            },
        )
        if response.get("name") != name or response.get("active") is not True:
            msg = "Credential issuance identity or activation not verified; preserve journal"
            raise RuntimeError(msg)
        expiry = datetime.fromisoformat(response["expiration_timestamp"])
        now = datetime.now(UTC)
        if not now < expiry <= now + timedelta(hours=25):
            msg = (
                "Issued credential exceeds one-day scope; revoke the journaled identity"
            )
            raise RuntimeError(msg)
        data = base64.b64decode(response["data"], validate=True)
        if not data:
            msg = "Credential API returned an empty kubeconfig"
            raise RuntimeError(msg)
        config = args.private_directory / "kubeconfig"
        with config.open("xb") as file:
            file.write(data)
        config.chmod(0o600)
        record.update(
            status="issued", expiration_timestamp=response["expiration_timestamp"]
        )
        journal.write_text(json.dumps(record, indent=2) + "\n")
        sys.stdout.write(
            "One-day kubeconfig issued into private session storage; verify its namespace and select an explicit context.\n"
        )
    else:
        record = json.loads(journal.read_text())
        if not re.fullmatch(r"wingman-session-[a-f0-9]{16}", record.get("name", "")):
            msg = "Refusing revocation outside the run-owned credential journal"
            raise ValueError(msg)
        if record.get("api_origin") != base:
            msg = "Credential journal belongs to another tenant origin"
            raise ValueError(msg)
        observed = request(
            base, token, "/api/web/namespaces/system/api_credentials/" + record["name"]
        )
        spec = observed.get("spec", {}).get("gc_spec", {})
        metadata = observed.get("metadata", {})
        if (
            metadata.get("name") != record["name"]
            or spec.get("type") != "KUBE_CONFIG"
            or spec.get("virtual_k8s_name") != record["vk8s"]
            or spec.get("virtual_k8s_namespace") != record["namespace"]
        ):
            msg = "Credential identity or scope differs from private journal; revocation refused"
            raise ValueError(msg)
        if spec.get("active") is not False:
            request(
                base,
                token,
                "/api/web/namespaces/system/revoke/api_credentials",
                {"name": record["name"], "namespace": "system"},
            )
            observed = request(
                base,
                token,
                "/api/web/namespaces/system/api_credentials/" + record["name"],
            )
            spec = observed.get("spec", {}).get("gc_spec", {})
        if spec.get("active") is not False:
            msg = "Credential revocation readback is not inactive; keep private storage"
            raise RuntimeError(msg)
        record["status"] = "revoked-inactive-readback"
        journal.write_text(json.dumps(record, indent=2) + "\n")
        (args.private_directory / "kubeconfig").unlink(missing_ok=True)
        sys.stdout.write(
            "Credential revocation verified by inactive readback; local kubeconfig removed.\n"
        )


if __name__ == "__main__":
    os.umask(0o077)
    main()
