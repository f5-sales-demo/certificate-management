"""Freeze published artifacts; install private verified binaries or reject drift."""

import argparse
import base64
import hashlib
import io
import json
import platform
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


def fetch(url: str) -> bytes:
    """Fetch a publication over verified HTTPS."""
    if not url.startswith("https://"):
        message = "Artifact URL must use HTTPS"
        raise ValueError(message)
    with urllib.request.urlopen(url, timeout=180) as response:  # noqa: S310 -- HTTPS publication URL.
        return response.read()


def gh(path: str) -> dict:
    """Read GitHub publication metadata."""
    return json.loads(subprocess.check_output([str(shutil.which("gh")), "api", path]))  # noqa: S603 -- Fixed gh API argv.


def verify_digest(data: bytes, expected: str) -> str:
    """Reject bytes that differ from their published digest."""
    actual = "sha256:" + hashlib.sha256(data).hexdigest()
    if actual != expected:
        message = "Published artifact digest mismatch"
        raise ValueError(message)
    return actual


def require_same_set(frozen: dict, current: dict) -> None:
    """Reject a publication change during qualification."""
    if frozen != current:
        message = "Publications advanced or changed; clean up and repeat affected qualification"
        raise ValueError(message)


def registry_manifest(repository: str, reference: str) -> tuple[bytes, str]:
    """Fetch and verify one public immutable application manifest."""
    token = json.loads(
        fetch("https://ghcr.io/token?scope=repository:" + repository + ":pull")
    )["token"]
    request = urllib.request.Request(
        "https://ghcr.io/v2/" + repository + "/manifests/" + reference,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 -- Fixed public GHCR origin.
        data, digest = response.read(), response.headers["Docker-Content-Digest"]
    verify_digest(data, digest)
    return data, digest


def resolve_wingman() -> dict:
    """Require a successful governed image publication and freeze Kubernetes too."""
    kubernetes = json.loads(
        fetch("https://registry.terraform.io/v1/providers/hashicorp/kubernetes")
    )["version"]
    runs = gh(
        "repos/f5-sales-demo/certificate-management/actions/workflows/certificate-wingman-image.yml/runs?status=success&branch=main&event=push&per_page=1"
    )["workflow_runs"]
    if not runs:
        msg = "No successful Wingman application publication; live qualification remains pending"
        raise ValueError(msg)
    publication = runs[0]
    commit = publication["head_sha"]
    manifest, digest = registry_manifest(
        "f5-sales-demo/certificate-management-wingman", "sha-" + commit
    )
    platforms = json.loads(manifest).get("manifests", [])
    expected = {
        (
            item.get("platform", {}).get("os"),
            item.get("platform", {}).get("architecture"),
        )
        for item in platforms
    }
    if not {("linux", "amd64"), ("linux", "arm64")}.issubset(expected):
        msg = "Wingman publication lacks required Linux architectures"
        raise ValueError(msg)
    return {
        "kubernetes_provider": {
            "version": kubernetes,
            "source_commit": gh(
                "repos/hashicorp/terraform-provider-kubernetes/commits/v" + kubernetes
            )["sha"],
        },
        "application": {
            "image": "ghcr.io/f5-sales-demo/certificate-management-wingman@" + digest,
            "source_commit": commit,
            "publication_run": publication["html_url"],
        },
    }


def resolve(include_wingman: bool = False) -> dict:
    """Resolve immutable identities from current publications."""
    result = {
        "kubernetes_provider": {
            "version": json.loads(
                fetch("https://registry.terraform.io/v1/providers/hashicorp/kubernetes")
            )["version"]
        }
    }
    version = json.loads(
        fetch("https://checkpoint-api.hashicorp.com/v1/check/terraform")
    )["current_version"]
    result["terraform"] = {
        "version": version,
        "source_commit": gh("repos/hashicorp/terraform/commits/v" + version)["sha"],
    }
    for tool, repository in [("provider", "terraform-provider-xcsh"), ("xcsh", "xcsh")]:
        release = gh("repos/f5-sales-demo/" + repository + "/releases/latest")
        tag = release["tag_name"]
        result[tool] = {
            "version": tag.removeprefix("v"),
            "source_commit": gh(
                "repos/f5-sales-demo/" + repository + "/commits/" + tag
            )["sha"],
            "assets": {
                asset["name"]: {
                    "url": asset["browser_download_url"],
                    "digest": asset["digest"],
                }
                for asset in release["assets"]
            },
        }
    registry_token = json.loads(
        fetch("https://ghcr.io/token?scope=repository:f5-sales-demo/docs-builder:pull")
    )["token"]
    request = urllib.request.Request(
        "https://ghcr.io/v2/f5-sales-demo/docs-builder/manifests/latest",
        headers={
            "Authorization": "Bearer " + registry_token,
            "Accept": "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 -- Fixed GHCR HTTPS registry URL.
        manifest = response.read()
        digest = response.headers["Docker-Content-Digest"]
    verify_digest(manifest, digest)
    runs = gh(
        "repos/f5-sales-demo/docs-builder/actions/workflows/build-image.yml/runs?status=success&branch=main&per_page=10"
    )["workflow_runs"]
    publication = None
    for run in runs:
        log = subprocess.check_output(  # noqa: S603 -- Fixed read-only publication argv.
            [
                str(shutil.which("gh")),
                "run",
                "view",
                str(run["id"]),
                "--repo",
                "f5-sales-demo/docs-builder",
                "--log",
            ],
            text=True,
        )
        if (
            "pushing manifest for ghcr.io/f5-sales-demo/docs-builder:latest@" + digest
            in log
        ):
            publication = run
            break
    if publication is None:
        message = "Published builder lacks a matching successful source receipt"
        raise ValueError(message)
    package = gh(
        "repos/f5-sales-demo/docs-builder/contents/package.json?ref="
        + publication["head_sha"]
    )
    builder_version = json.loads(base64.b64decode(package["content"]))["version"]
    result["builder"] = {
        "image": "ghcr.io/f5-sales-demo/docs-builder@" + digest,
        "version": builder_version,
        "source_commit": publication["head_sha"],
        "publication_run": publication["html_url"],
    }
    if include_wingman:
        result.update(resolve_wingman())
    return result


# Each verified tool contributes its archive, binary and provenance to one receipt.
# pylint: disable=too-many-locals
def install(frozen: dict, destination: Path) -> dict:
    """Install verified binaries and an isolated provider mirror."""
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    osname = "darwin" if platform.system() == "Darwin" else "linux"
    arch = "arm64" if platform.machine() in ("arm64", "aarch64") else "amd64"
    target = osname + "_" + arch
    receipts: dict[str, Any] = {"platform": target}
    if "kubernetes_provider" in frozen:
        receipts["kubernetes_provider"] = frozen["kubernetes_provider"]
    for tool in ("terraform", "provider", "xcsh"):
        info = frozen[tool]
        version = info["version"]
        if tool == "terraform":
            name = f"terraform_{version}_{target}.zip"
            base = f"https://releases.hashicorp.com/terraform/{version}/"
            checksums = fetch(base + f"terraform_{version}_SHA256SUMS")
            sums = {
                line.split()[1].lstrip("*"): line.split()[0]
                for line in checksums.decode().splitlines()
            }
            data = fetch(base + name)
            expected = "sha256:" + sums[name]
        else:
            name = (
                f"terraform-provider-xcsh_{version}_{target}.zip"
                if tool == "provider"
                else "xcsh-" + osname + "-" + ("arm64" if arch == "arm64" else "x64")
            )
            asset = info["assets"][name]
            expected = asset["digest"]
            data = fetch(asset["url"])
            if tool == "provider":
                checksum_asset = info["assets"][
                    f"terraform-provider-xcsh_{version}_SHA256SUMS"
                ]
                checksums = fetch(checksum_asset["url"])
                verify_digest(checksums, checksum_asset["digest"])
                sums = {
                    line.split()[1].lstrip("*"): line.split()[0]
                    for line in checksums.decode().splitlines()
                }
                if expected != "sha256:" + sums[name]:
                    message = "Release checksum disagrees with GitHub digest"
                    raise ValueError(message)
        digest = verify_digest(data, expected)
        if tool == "xcsh":
            binary = data
            binary_name = "xcsh"
        else:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                binary_name = next(
                    entry
                    for entry in archive.namelist()
                    if Path(entry).name == "terraform"
                    or Path(entry).name.startswith("terraform-provider-xcsh_v")
                )
                binary = archive.read(binary_name)
        output = destination / Path(binary_name).name
        output.write_bytes(binary)
        output.chmod(0o700)
        receipts[tool] = {
            "version": version,
            "source_commit": info["source_commit"],
            "archive_sha256": digest,
            "binary_sha256": "sha256:" + hashlib.sha256(binary).hexdigest(),
        }
        if tool == "provider":
            mirror = (
                destination
                / "mirror/registry.terraform.io/f5-sales-demo/xcsh"
                / version
                / target
            )
            mirror.mkdir(parents=True, exist_ok=True)
            link = mirror / output.name
            if link.exists():
                if not link.is_symlink() or link.resolve() != output.resolve():
                    message = "Provider mirror contains an unexpected installed file"
                    raise ValueError(message)
            else:
                link.symlink_to(output.resolve())
    config = destination / "frozen.tfrc"
    config.write_text(
        "provider_installation { filesystem_mirror { path = "
        + json.dumps(str((destination / "mirror").resolve()))
        + ' include = ["f5-sales-demo/xcsh"] } direct { exclude = ["f5-sales-demo/xcsh"] } }\n'
    )
    (destination / "installed.json").write_text(json.dumps(receipts, indent=2) + "\n")
    return receipts


def main() -> None:
    """Resolve, install or recheck one artifact set."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--install", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--frozen",
        action="store_true",
        help="Install existing frozen selection without re-resolving",
    )
    parser.add_argument(
        "--wingman",
        action="store_true",
        help="Require the published application image and freeze Kubernetes",
    )
    args = parser.parse_args()
    if args.check:
        frozen = json.loads(args.output.read_text())
        require_same_set(frozen, resolve(args.wingman or "application" in frozen))
    elif args.frozen:
        if not args.install:
            parser.error("--frozen requires --install")
        install(json.loads(args.output.read_text()), args.install)
    else:
        frozen = resolve(args.wingman)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(frozen, indent=2) + "\n")
        if args.install:
            install(frozen, args.install)


if __name__ == "__main__":
    main()
