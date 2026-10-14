"""Build the frozen published builder and verify personalized clipboard workflows."""

# ruff: noqa: S603 -- Fixed build/test executables and repository-owned paths.
import argparse
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


def main() -> None:
    """Exercise the current image against source, downloads and browser controls."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts", type=Path, required=True, help="Frozen publication JSON"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    work = Path(tempfile.mkdtemp(prefix="certificate-current-builder-"))
    content = work / "content"
    shutil.copytree(root / "docs", content)
    for line in (root / "docs/_imports").read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        source, destination = line.split(" -> ")
        if (
            Path(source).is_absolute()
            or Path(destination).is_absolute()
            or ".." in Path(source).parts
            or ".." in Path(destination).parts
        ):
            message = "Unsafe documentation import path"
            raise ValueError(message)
        output = content / "_data" / destination
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / source, output)
    build = work / "build"
    build.mkdir()
    frozen = json.loads(args.artifacts.read_text())
    image = frozen["builder"]["image"]
    docker = shutil.which("docker")
    assert docker
    subprocess.run(
        [
            docker,
            "run",
            "--rm",
            "--user",
            "0:0",
            "-e",
            "GITHUB_REPOSITORY=f5-sales-demo/certificate-management",
            "-e",
            "GITHUB_REPOSITORY_OWNER=f5-sales-demo",
            "-e",
            "DOCS_SITE=https://f5-sales-demo.github.io",
            "-e",
            "DOCS_BASE=/certificate-management",
            "-v",
            str(content) + ":/content/docs:ro",
            "-v",
            str(build) + ":/output",
            image,
        ],
        check=True,
    )
    preview = work / "preview"
    preview.mkdir()
    (preview / "certificate-management").symlink_to(build, target_is_directory=True)
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(preview)
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:" + str(server.server_port)
    env = {
        **os.environ,
        "CERT_CUSTOMIZATION_URL": base,
        "CERT_CUSTOMIZATION_ARTIFACTS": str(work / "browser"),
    }
    try:
        subprocess.run(
            [sys.executable, str(root / "tests/customization_browser.py")],
            env=env,
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(root / "scripts/check_publication.py"),
                "--base",
                base + "/certificate-management",
                "--output",
                str(work / "publication.json"),
            ],
            check=True,
        )
    finally:
        server.shutdown()
        server.server_close()
    receipt = {
        "builder_image": image,
        "browser": json.loads((work / "browser/receipt.json").read_text()),
        "publication": json.loads((work / "publication.json").read_text()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
