"""Credential-free trusted endpoint and download consistency checks."""

# ruff: noqa: PLR2004 -- HTTP status and default TLS port contracts.
import argparse
import hashlib
import http.client
import json
import ssl
import urllib.parse
import urllib.request
from pathlib import Path


def endpoints(certificate: Path) -> dict:
    """Verify trust, hostname, fingerprint, response and HTTP redirection."""
    context = ssl.create_default_context(cafile=str(certificate))
    expected = ssl.PEM_cert_to_DER_cert(certificate.read_text())
    results = {}
    for host in (
        "certificate-management.f5-sales-demo.com",
        "certificate-management-terraform.f5-sales-demo.com",
    ):
        connection = http.client.HTTPSConnection(host, context=context, timeout=30)
        connection.connect()
        fingerprint = connection.sock.getpeercert(binary_form=True)
        if fingerprint != expected:
            message = "Served certificate differs from published trust certificate"
            raise ValueError(message)
        connection.request("GET", "/get")
        response = connection.getresponse()
        body = json.loads(response.read())
        if response.status != 200:
            message = "Endpoint did not return HTTP 200 JSON"
            raise ValueError(message)
        if "terraform" in host and body != {
            "example": "terraform-certificate",
            "native_blindfold": True,
        }:
            message = "Terraform response marker mismatch"
            raise ValueError(message)
        if "terraform" not in host and (
            body.get("url") != "https://httpbin.org/get"
            or body.get("args") != {}
            or body.get("headers", {}).get("Host") != "httpbin.org"
        ):
            message = "xcsh HTTPbin response contract mismatch"
            raise ValueError(message)
        connection.close()
        redirect = http.client.HTTPConnection(host, timeout=30)
        redirect.request("GET", "/get")
        response = redirect.getresponse()
        location = urllib.parse.urlsplit(response.getheader("Location", ""))
        valid_target = (
            location.scheme == "https"
            and location.hostname == host
            and location.port in (None, 443)
        )
        if (
            response.status not in (301, 302, 307, 308)
            or not valid_target
            or location.path != "/get"
            or location.query
        ):
            message = "HTTP redirection mismatch"
            raise ValueError(message)
        response.read()
        redirect.close()
        results[host] = {
            "trusted_hostname": True,
            "served_sha256": hashlib.sha256(fingerprint).hexdigest(),
            "expected_response": True,
            "http_redirect": response.status,
        }
    return results


def downloads(root: Path, base: str) -> dict:
    """Compare all published Terraform downloads with source bytes."""
    if urllib.parse.urlsplit(base).scheme not in ("http", "https"):
        message = "Publication URL must use HTTP or HTTPS"
        raise ValueError(message)
    results = {}
    for source in sorted((root / "terraform").rglob("*.tf*")):
        if source.suffix not in (".tf", ".example"):
            continue
        relative = source.relative_to(root).as_posix()
        with urllib.request.urlopen(  # noqa: S310 -- Scheme checked and repository-owned relative path.
            base.rstrip("/") + "/_data/" + relative, timeout=30
        ) as response:
            data = response.read()
        if data != source.read_bytes():
            message = "Published download differs from source: " + relative
            raise ValueError(message)
        results[relative] = hashlib.sha256(data).hexdigest()
    return results


def main() -> None:
    """Check credential-free public acceptance gates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--base", default="https://f5-sales-demo.github.io/certificate-management"
    )
    parser.add_argument("--skip-downloads", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    receipt = {
        "qualification": "credential-free published endpoints and source/download consistency",
        "endpoints": endpoints(root / "docs/assets/certificate-management.pem"),
    }
    if not args.skip_downloads:
        receipt["downloads"] = downloads(root, args.base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
