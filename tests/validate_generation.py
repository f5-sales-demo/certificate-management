"""Verify deterministic canonical generation across the complete task-page set."""

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot() -> dict[str, str]:
    """Hash public examples and their canonical generated input variants."""
    paths = [
        *(ROOT / "docs/en").rglob("*.md"),
        *(ROOT / "docs/assets/configurations").glob("*.json"),
        *(ROOT / "terraform/input-variants").rglob("*.tf"),
    ]
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, required=True)
    args = parser.parse_args()
    before = snapshot()
    for _ in range(2):
        subprocess.run(  # noqa: S603 -- Fixed canonical generator with caller-selected schema.
            [
                sys.executable,
                str(ROOT / "scripts/generate_administration.py"),
                "--schema",
                str(args.schema.resolve()),
            ],
            check=True,
        )
        after = snapshot()
        assert before == after, [
            path
            for path in before.keys() | after.keys()
            if before.get(path) != after.get(path)
        ]
    print(  # noqa: T201 -- Verification summary.
        f"Generation consistency passed: {len(before)} public source files, two complete regenerations."
    )


if __name__ == "__main__":
    main()
