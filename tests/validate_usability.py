"""Check task completeness, current navigation, and unique canonical ownership."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("prerequisites", "configuration", "configure", "verify", "maintain", "remove")
CASES = ("xcsh", "terraform", "client-mtls", "wingman")


def validate() -> None:
    """Check a workflow across pages instead of requiring one long document."""
    pages = list((ROOT / "docs/en").rglob("*.md"))
    sources = {page: page.read_text() for page in pages}
    for case in CASES:
        directory = ROOT / "docs/en" / case
        overview = sources[directory / "index.md"]
        assert "```" not in overview, case
        assert "Previous bookmarks" not in overview, case
        positions = [overview.index(f"](./{stage}/)") for stage in STAGES]
        assert positions == sorted(positions), case
        for index, stage in enumerate(STAGES):
            source = sources[directory / (stage + ".md")]
            assert f"  label: {stage.capitalize()}" in source, (case, stage)
            assert f"  order: {index + 1}" in source, (case, stage)
            assert "tableOfContents:" in source
            assert "maxHeadingLevel: 3" in source
            previous = "../" if index == 0 else "../" + STAGES[index - 1] + "/"
            following = "../" if index == 5 else "../" + STAGES[index + 1] + "/"
            assert f"prev:\n  link: {previous}\n" in source
            assert f"next:\n  link: {following}\n" in source
            assert re.search(r"^## ", source, re.MULTILINE), (case, stage)
            if stage == "configuration":
                assert "```bash" not in source, case
    all_source = "\n".join(sources.values())
    for artifact in (ROOT / "docs/assets/configurations").glob("*.json"):
        public = artifact.read_text().rstrip()
        # Every public configuration is visible once, including the xcsh manifest.
        assert all_source.count("```json\n" + public + "\n```") == 1, artifact
        json.loads(public)
    for name in ("bootstrap", "runtime", "qualification"):
        complete = "\n".join(
            path.read_text().rstrip()
            for path in sorted((ROOT / "wingman" / name).glob("*.tf"))
        )
        assert all_source.count("```hcl\n" + complete + "\n```") == 1, name
    named = ROOT / "terraform/named-certificate"
    filenames = " ".join(path.name for path in sorted(named.glob("*.tf")))
    configure = sources[ROOT / "docs/en/terraform/configure.md"]
    assert "for file in " + filenames + "; do" in configure
    complete_hcl = "\n".join(
        path.read_text().rstrip() for path in sorted(named.glob("*.tf"))
    )
    assert all_source.count("```hcl\n" + complete_hcl + "\n```") == 1
    prerequisites = sources[ROOT / "docs/en/client-mtls/prerequisites.md"]
    assert "no_crl" in prerequisites
    assert "revocation is excluded" in prerequisites
    assert "unchanged" in sources[ROOT / "docs/en/xcsh/configure.md"]
    assert "READY" in sources[ROOT / "docs/en/wingman/verify.md"]
    print(  # noqa: T201 -- Command-line validation summary.
        f"Usability checks passed: {len(pages)} English routes, four complete workflows."
    )


if __name__ == "__main__":
    validate()
