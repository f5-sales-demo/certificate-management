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
from pathlib import Path
from typing import IO


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    """Never forward a session token to a redirected credential endpoint."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
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


# The issue/revoke lifecycle stays sequential so the exact journal governs every mutation.
# pylint: disable=too-many-statements,too-many-locals,too-many-branches
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
    if parsed.scheme != "https" or any(
        (parsed.username, parsed.password, parsed.query, parsed.fragment, parsed.path)
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
        name = "wingman-session-" + uuid.uuid4().hex[:12]
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
        (args.private_directory / "issuance-response-private.json").write_text(
            json.dumps(response)
        )
        actual_name = response.get("name", "")
        record.update(name=actual_name, requested_name=name, status="issuance-observed")
        journal.write_text(json.dumps(record, indent=2) + "\n")
        if not re.fullmatch(re.escape(name) + r"(?:-[a-z0-9]+)?", actual_name):
            msg_0 = "Credential response name is outside the journaled request"
            raise RuntimeError(msg_0)
        observed = request(
            base, token, "/api/web/namespaces/system/api_credentials/" + actual_name
        )
        observed = observed.get("object", observed)
        metadata = observed.get("metadata", {})
        spec = observed.get("spec", {}).get("gc_spec", {})
        record["uid"] = observed.get("system_metadata", {}).get("uid")
        journal.write_text(json.dumps(record, indent=2) + "\n")
        if (
            (
                metadata.get("name"),
                metadata.get("namespace"),
                spec.get("type"),
                spec.get("virtual_k8s_name"),
                spec.get("virtual_k8s_namespace"),
            )
            != (actual_name, "system", "KUBE_CONFIG", args.vk8s, args.namespace)
            or not record["uid"]
            or spec.get("active") is not True
            or response.get("active") is not True
        ):
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
        requested_name = record.get("requested_name", "")
        if (
            not re.fullmatch(r"wingman-session-[a-f0-9]{12}", requested_name)
            or not re.fullmatch(
                re.escape(requested_name) + r"(?:-[a-z0-9]+)?", record.get("name", "")
            )
            or not record.get("uid")
        ):
            msg = "Refusing revocation outside the run-owned credential journal"
            raise ValueError(msg)
        if record.get("api_origin") != base:
            msg = "Credential journal belongs to another tenant origin"
            raise ValueError(msg)

        def readback() -> dict | None:
            try:
                value = request(
                    base,
                    token,
                    "/api/web/namespaces/system/api_credentials/" + record["name"],
                )
                return value.get("object", value)
            except RuntimeError:
                if record.get("status") != "revocation-requested":
                    raise
                # This API returns HTTP 500 for a deleted entry. Only a successful
                # collection read can qualify its exact identity as absent.
                for _ in range(2):
                    listing = request(
                        base, token, "/api/web/namespaces/system/api_credentials"
                    )
                    if not isinstance(listing.get("items"), list):
                        msg_0 = "Credential absence collection is invalid"
                        raise TypeError(msg_0) from None
                    if any(
                        item.get("name") == record["name"]
                        or item.get("uid") == record["uid"]
                        for item in listing["items"]
                    ):
                        msg_0 = "Credential remains in collection; preserve journal"
                        raise RuntimeError(msg_0) from None
                return None

        revoked_observed = readback()
        if revoked_observed is not None:
            spec = revoked_observed.get("spec", {}).get("gc_spec", {})
            metadata = revoked_observed.get("metadata", {})
            if (
                metadata.get("name"),
                metadata.get("namespace"),
                revoked_observed.get("system_metadata", {}).get("uid"),
                spec.get("type"),
                spec.get("virtual_k8s_name"),
                spec.get("virtual_k8s_namespace"),
            ) != (
                record["name"],
                "system",
                record["uid"],
                "KUBE_CONFIG",
                record["vk8s"],
                record["namespace"],
            ):
                msg_0 = "Credential identity or scope differs from private journal; revocation refused"
                raise ValueError(msg_0)
            if spec.get("active") is not False:
                record["status"] = "revocation-requested"
                journal.write_text(json.dumps(record, indent=2) + "\n")
                request(
                    base,
                    token,
                    "/api/web/namespaces/system/revoke/api_credentials",
                    {"name": record["name"], "namespace": "system"},
                )
                revoked_observed = readback()
            if (
                revoked_observed is not None
                and revoked_observed.get("spec", {}).get("gc_spec", {}).get("active")
                is not False
            ):
                msg_0 = "Credential revocation readback is active; keep private storage"
                raise RuntimeError(msg_0)
        record["status"] = (
            "revoked-absent-collection-twice"
            if revoked_observed is None
            else "revoked-inactive-readback"
        )
        journal.write_text(json.dumps(record, indent=2) + "\n")
        (args.private_directory / "kubeconfig").unlink(missing_ok=True)
        (args.private_directory / "issuance-response-private.json").unlink(
            missing_ok=True
        )
        sys.stdout.write(
            "Credential revocation verified; local credential material removed.\n"
        )


if __name__ == "__main__":
    os.umask(0o077)
    main()
