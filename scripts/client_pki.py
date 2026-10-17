"""Manage a private synthetic OpenSSL CA; print only public certificate receipts."""

# ruff: noqa: S603, S607 -- Fixed OpenSSL executable and exact argv; no shell.
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


def openssl(*arguments: str) -> str:
    """Run OpenSSL without printing material or private diagnostics."""
    result = subprocess.run(
        ["openssl", *arguments], capture_output=True, text=True, check=False
    )
    if result.returncode:
        msg = "OpenSSL failed; check the private CA configuration and inputs"
        raise RuntimeError(msg)
    return result.stdout.strip()


def receipt(path: Path) -> dict:
    """Return public certificate identity only."""
    der = subprocess.run(
        ["openssl", "x509", "-in", str(path), "-outform", "DER"],
        capture_output=True,
        check=True,
    ).stdout
    return {
        "certificate_file": str(path),
        "certificate_sha256": hashlib.sha256(der).hexdigest(),
        "serial": openssl("x509", "-in", str(path), "-noout", "-serial").split("=", 1)[
            1
        ],
    }


def main() -> None:
    """Execute one lifecycle operation in an owner-only private database."""
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "issue", "revoke", "crl"])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--name", default="Synthetic client mTLS CA")
    parser.add_argument("--client")
    parser.add_argument("--revision")
    args = parser.parse_args()
    root = args.directory.resolve()
    if args.action == "init":
        if not re.fullmatch(r"[A-Za-z0-9 ._-]{1,64}", args.name):
            msg = "Use a simple synthetic CA name"
            raise ValueError(msg)
        root.mkdir(mode=0o700, parents=True, exist_ok=False)
        for name in ["newcerts", "clients", "crls"]:
            (root / name).mkdir(mode=0o700)
        (root / "index.txt").write_text("")
        (root / "index.txt.attr").write_text("unique_subject = no\n")
        (root / "serial").write_text("1000\n")
        (root / "crlnumber").write_text("1000\n")
        # The config lives inside the private database; only public bundles enter Terraform.
        (root / "openssl.cnf").write_text(f"""[ca]
default_ca = synthetic
[synthetic]
dir = {root}
database = $dir/index.txt
new_certs_dir = $dir/newcerts
certificate = $dir/ca.pem
private_key = $dir/ca.key
serial = $dir/serial
crlnumber = $dir/crlnumber
default_md = sha256
default_days = 30
default_crl_days = 7
policy = policy
x509_extensions = client
unique_subject = no
[policy]
commonName = supplied
[client]
basicConstraints = critical,CA:false
keyUsage = critical,digitalSignature
extendedKeyUsage = clientAuth
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
""")
        openssl(
            "req",
            "-x509",
            "-newkey",
            "rsa:3072",
            "-nodes",
            "-keyout",
            str(root / "ca.key"),
            "-out",
            str(root / "ca.pem"),
            "-days",
            "365",
            "-subj",
            "/CN=" + args.name,
            "-addext",
            "basicConstraints=critical,CA:true",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
        )
        result = receipt(root / "ca.pem")
    elif args.action in ["issue", "revoke"]:
        if not args.client or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.client):
            msg = "Supply a lower-case synthetic client name"
            raise ValueError(msg)
        client = root / "clients" / args.client
        if args.action == "issue":
            client.mkdir(mode=0o700, exist_ok=False)
            openssl(
                "req",
                "-new",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                str(client / "key.pem"),
                "-out",
                str(client / "request.pem"),
                "-subj",
                "/CN=Synthetic client",
            )
            openssl(
                "ca",
                "-batch",
                "-config",
                str(root / "openssl.cnf"),
                "-in",
                str(client / "request.pem"),
                "-out",
                str(client / "certificate.pem"),
                "-notext",
            )
        else:
            openssl(
                "ca",
                "-batch",
                "-config",
                str(root / "openssl.cnf"),
                "-revoke",
                str(client / "certificate.pem"),
                "-crl_reason",
                "superseded",
            )
        result = receipt(client / "certificate.pem")
    else:
        if not args.revision or not re.fullmatch(
            r"[a-z0-9][a-z0-9-]{0,31}", args.revision
        ):
            msg = "Supply an immutable lower-case CRL revision"
            raise ValueError(msg)
        path = root / "crls" / (args.revision + ".pem")
        if path.exists():
            msg = "CRL revision already exists; use a new revision"
            raise ValueError(msg)
        openssl(
            "ca",
            "-batch",
            "-config",
            str(root / "openssl.cnf"),
            "-gencrl",
            "-out",
            str(path),
        )
        openssl(
            "crl",
            "-in",
            str(path),
            "-noout",
            "-verify",
            "-CAfile",
            str(root / "ca.pem"),
        )
        result = {
            "crl_file": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "revision": args.revision,
            "validity": openssl(
                "crl", "-in", str(path), "-noout", "-lastupdate", "-nextupdate"
            ),
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
