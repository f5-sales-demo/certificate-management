"""Resolve a governed public image to a verified immutable registry reference."""

import hashlib
import http
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
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


def resolve(image: str) -> dict[str, str]:
    """Verify the registry response and retain its platform digests for acceptance."""
    require_image(image)
    reference = "latest" if image.endswith(":latest") else image.split("@", 1)[1]
    url = "https://ghcr.io/v2/" + REPOSITORY + "/manifests/" + reference
    headers = {"Accept": ACCEPT}
    request = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(request, timeout=30)  # noqa: S310 -- Fixed public registry.
    except urllib.error.HTTPError as error:
        if error.code != http.HTTPStatus.UNAUTHORIZED:
            raise
        token_url = "https://ghcr.io/token?" + urllib.parse.urlencode(
            {"service": "ghcr.io", "scope": "repository:" + REPOSITORY + ":pull"}
        )
        with urllib.request.urlopen(token_url, timeout=30) as token_response:
            token = json.load(token_response)["token"]
        request.add_header("Authorization", "Bearer " + token)
        response = urllib.request.urlopen(request, timeout=30)  # noqa: S310 -- Fixed public registry.
    with response:
        body = response.read()
        digest = "sha256:" + hashlib.sha256(body).hexdigest()
        if response.headers.get("Docker-Content-Digest") != digest:
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
