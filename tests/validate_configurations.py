"""Validate every published configuration with the pinned installed provider."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
work = Path(tempfile.mkdtemp(prefix="certificate-configurations-"))
work.chmod(0o700)
config = work / "direct.tfrc"
config.write_text("provider_installation { direct {} }\n")
env = {**os.environ, "TF_CLI_CONFIG_FILE": str(config), "TF_IN_AUTOMATION": "1"}
env.pop("XCSH_API_TOKEN", None)
env.pop("XCSH_API_URL", None)
receipt = {"runnable": {}, "reference": {}}
for group, directories in [
    ("runnable", sorted((root / "terraform").glob("*/versions.tf"))),
    ("reference", sorted((root / "terraform/reference").glob("*/versions.tf.example"))),
]:
    for version in directories:
        source = version.parent
        dest = work / group / source.name
        dest.mkdir(parents=True)
        for file in source.glob("*.tf" if group == "runnable" else "*.tf.example"):
            shutil.copyfile(file, dest / file.name.removesuffix(".example"))
        assert "15.7.2" in (dest / "versions.tf").read_text()
        for command in [
            ["init", "-backend=false", "-input=false"],
            ["validate", "-json"],
        ]:
            result = subprocess.run(  # noqa: S603 -- fixed Terraform subcommands and repository-owned paths.
                [str(Path(shutil.which("terraform")).resolve()), "-chdir=" + str(dest), *command],
                env=env,
                capture_output=True,
                check=False,
                timeout=300,
            )
            (dest / (command[0] + ".out")).write_bytes(result.stdout)
            (dest / (command[0] + ".err")).write_bytes(result.stderr)
            if result.returncode:
                message = f"{group}/{source.name} {command[0]} failed; private logs in {dest}"
                raise RuntimeError(message)
        receipt[group][source.name] = 0
assert len(receipt["runnable"]) == 16
assert len(receipt["reference"]) == 9
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(receipt, indent=2) + "\n")
