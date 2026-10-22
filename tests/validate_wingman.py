"""Validate Wingman with installed published artifacts, without claiming live unseal."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    artifacts = args.artifacts.resolve()
    installed = json.loads((artifacts / "installed.json").read_text())
    work = Path(tempfile.mkdtemp(prefix="wingman-schema-"))
    work.chmod(0o700)
    shutil.copytree(
        root / "wingman",
        work / "wingman",
        ignore=shutil.ignore_patterns(
            ".terraform", ".terraform.lock.hcl", "__pycache__"
        ),
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XCSH_", "TF_VAR_"))
    }
    env.update(TF_CLI_CONFIG_FILE=str(artifacts / "frozen.tfrc"), TF_IN_AUTOMATION="1")
    result = {
        "qualification": "published schema only; real injection and fresh unseal not exercised",
        "artifacts": installed,
        "roots": {},
    }
    for name in ("bootstrap", "runtime", "qualification"):
        directory = work / "wingman" / name
        for command in (
            ["init", "-backend=false", "-input=false"],
            ["validate", "-json"],
        ):
            completed = subprocess.run(  # noqa: S603 -- Frozen verified Terraform and fixed argv.
                [str(artifacts / "terraform"), "-chdir=" + str(directory), *command],
                env=env,
                capture_output=True,
                check=False,
                timeout=300,
            )
            (directory / (command[0] + ".out")).write_bytes(completed.stdout)
            (directory / (command[0] + ".err")).write_bytes(completed.stderr)
            if completed.returncode:
                raise RuntimeError(
                    "Wingman "
                    + name
                    + " "
                    + command[0]
                    + " failed; private diagnostics in "
                    + str(directory)
                )
        versions = json.loads(
            subprocess.check_output(  # noqa: S603 -- Frozen verified Terraform and fixed argv.
                [
                    str(artifacts / "terraform"),
                    "-chdir=" + str(directory),
                    "version",
                    "-json",
                ],
                env=env,
            )
        )
        if (
            name != "qualification"
            and versions["provider_selections"][
                "registry.terraform.io/f5-sales-demo/xcsh"
            ]
            != installed["provider"]["version"]
        ):
            msg = "Wingman source provider pin differs from frozen published selection"
            raise ValueError(msg)
        if (
            name != "bootstrap"
            and versions["provider_selections"][
                "registry.terraform.io/hashicorp/kubernetes"
            ]
            != installed["kubernetes_provider"]["version"]
        ):
            message = "Kubernetes provider differs from frozen published selection"
            raise ValueError(message)
        result["roots"][name] = "valid"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
