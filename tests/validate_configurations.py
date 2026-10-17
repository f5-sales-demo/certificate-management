"""Validate every published configuration with the frozen current published artifacts."""

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--artifacts", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
work = Path(tempfile.mkdtemp(prefix="certificate-configurations-"))
work.chmod(0o700)
installed = json.loads((args.artifacts / "installed.json").read_text())
config = args.artifacts / "frozen.tfrc"
env = {
    **os.environ,
    "TF_CLI_CONFIG_FILE": str(config.resolve()),
    "TF_IN_AUTOMATION": "1",
}
env = {key: value for key, value in env.items() if not key.startswith("XCSH_")}
receipt: dict[str, Any] = {"runnable": {}, "reference": {}, "inputs": {}}
TERRAFORM_PATH = str(args.artifacts / "terraform")
assert TERRAFORM_PATH is not None
TERRAFORM = str(Path(TERRAFORM_PATH).resolve())
for group, directories in [
    ("runnable", sorted((root / "terraform").glob("*/versions.tf"))),
    ("reference", sorted((root / "terraform/reference").glob("*/versions.tf.example"))),
    ("inputs", sorted((root / "terraform/input-variants").glob("*/versions.tf"))),
]:
    for version in directories:
        source = version.parent
        dest = work / group / source.name
        dest.mkdir(parents=True)
        for file in source.glob("*.tf.example" if group == "reference" else "*.tf"):
            shutil.copyfile(file, dest / file.name.removesuffix(".example"))
        assert not re.search(
            r'^\s*version\s*=\s*"\s*(?:=\s*)?\d+\.\d+\.\d+\s*"',
            (dest / "versions.tf").read_text(),
            re.MULTILINE,
        )
        for command in [
            ["init", "-upgrade", "-backend=false", "-input=false"],
            ["validate", "-json"],
        ]:
            result = subprocess.run(  # noqa: S603 -- fixed Terraform subcommands and repository-owned paths.
                [TERRAFORM, "-chdir=" + str(dest), *command],
                env=env,
                capture_output=True,
                check=False,
                timeout=300,
            )
            (dest / (command[0] + ".out")).write_bytes(result.stdout)
            (dest / (command[0] + ".err")).write_bytes(result.stderr)
            if result.returncode:
                message = (
                    f"{group}/{source.name} {command[0]} failed; private logs in {dest}"
                )
                raise RuntimeError(message)
        versions = json.loads(
            subprocess.check_output(  # noqa: S603 -- Frozen executable and fixed Terraform argv.
                [TERRAFORM, "-chdir=" + str(dest), "version", "-json"], env=env
            )
        )
        assert versions["terraform_version"] == installed["terraform"]["version"]
        assert (
            versions["provider_selections"]["registry.terraform.io/f5-sales-demo/xcsh"]
            == installed["provider"]["version"]
        )
        receipt[group][source.name] = 0
assert len(receipt["runnable"]) == 16
assert len(receipt["reference"]) == 9
assert len(receipt["inputs"]) == 4
args.output.parent.mkdir(parents=True, exist_ok=True)
receipt["artifacts"] = installed
receipt["qualification"] = (
    "credential-free schema validation; live encryption and served TLS not exercised"
)
args.output.write_text(json.dumps(receipt, indent=2) + "\n")
