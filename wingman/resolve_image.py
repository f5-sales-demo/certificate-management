"""Resolve a governed public image to a verified immutable registry reference."""

import hashlib
import http.client
import json
import sys
import urllib.parse
from typing import Any

from qualify import require_image

REPOSITORY = "f5-sales-demo/certificate-management-wingman"
PREFIX = "ghcr.io/" + REPOSITORY
ACCEPT = (
    "application/vnd.oci.image.index.v1+json, "
    "application/vnd.docker.distribution.manifest.list.v2+json, "
    "application/vnd.oci.image.manifest.v1+json, "
    "application/vnd.docker.distribution.manifest.v2+json"
)


def registry_get(path: str, headers: dict[str, str]) -> tuple[int, bytes, str | None]:
    """Use HTTPS only, with a fixed registry host and no redirect handling."""
    connection = http.client.HTTPSConnection("ghcr.io", timeout=30)
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        return (
            response.status,
            response.read(),
            response.getheader("Docker-Content-Digest"),
        )
    finally:
        connection.close()


def resolve(image: str) -> dict[str, str]:
    """Verify the registry response and retain its platform digests for acceptance."""
    require_image(image)
    reference = "latest" if image.endswith(":latest") else image.split("@", 1)[1]
    path = "/v2/" + REPOSITORY + "/manifests/" + reference
    headers = {"Accept": ACCEPT}
    status, body, registry_digest = registry_get(path, headers)
    if status == http.HTTPStatus.UNAUTHORIZED:
        token_path = "/token?" + urllib.parse.urlencode(
            {"service": "ghcr.io", "scope": "repository:" + REPOSITORY + ":pull"}
        )
        token_status, token_body, _ = registry_get(token_path, {})
        if token_status != http.HTTPStatus.OK:
            message = "Public registry authorization failed"
            raise ValueError(message)
        headers["Authorization"] = "Bearer " + json.loads(token_body)["token"]
        status, body, registry_digest = registry_get(path, headers)
    if status != http.HTTPStatus.OK:
        message = "Registry manifest request failed with HTTP " + str(status)
        raise ValueError(message)
    digest = "sha256:" + hashlib.sha256(body).hexdigest()
    if registry_digest != digest:
        message = "Registry manifest digest does not match its bytes"
        raise ValueError(message)
    if reference not in ("latest", digest):
        message = "Registry returned a different immutable image"
        raise ValueError(message)
    document: dict[str, Any] = json.loads(body)
    platforms = [
        item["digest"]
        for item in document.get("manifests", [])
        if item.get("platform", {}).get("os") == "linux"
    ] or [digest]
    for platform in platforms:
        require_image(PREFIX + "@" + platform)
    return {
        "digest": digest,
        "image": PREFIX + "@" + digest,
        "platform_digests": ",".join(platforms),
    }


def main() -> None:
    """Implement Terraform external data's string-only JSON interface."""
    selected = json.load(sys.stdin)["image"]
    sys.stdout.write(json.dumps(resolve(selected)) + "\n")


if __name__ == "__main__":
    main()
