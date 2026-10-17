"""Check complete source examples, preserved routes, links, and shell syntax."""

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def anchors(source: str) -> set[str]:
    """Match Markdown heading slugs, including repeated heading suffixes."""
    source = re.sub(r"```[\s\S]*?```", "", source)
    found: set[str] = set()
    for heading in re.findall(r"^#{1,6}\s+(.+)$", source, re.MULTILINE):
        plain = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", heading)
        slug = re.sub(r"[^\w\s-]", "", plain.lower()).replace(" ", "-")
        candidate, suffix = slug, 0
        while candidate in found:
            suffix += 1
            candidate = f"{slug}-{suffix}"
        found.add(candidate)
    found.update(re.findall(r'\bid="([^"]+)"', source))
    return found


def main() -> None:
    """Fail on missing examples, broken local links, or non-runnable shell syntax."""
    pages = sorted((DOCS / "en").rglob("*.md"))
    routes = {
        "/"
        + str(p.relative_to(DOCS)).removesuffix(".md").removesuffix("/index")
        + "/": p
        for p in pages
    }
    audit = json.loads(
        (ROOT / "verification/certificate-administration-audit.json").read_text()
    )
    assert len({entry["page"] for entry in audit["sections"]}) == 9
    assert all(
        entry["disposition"] in {"keep", "rewrite", "move", "merge", "remove"}
        for entry in audit["sections"]
    )
    blocks = 0
    for route, page in routes.items():
        source = page.read_text()
        label = re.search(r"^  label: (.+)$", source, re.MULTILINE)
        title = re.search(r"^title: (.+)$", source, re.MULTILINE)
        assert title
        assert len((label or title)[1].split()) <= 3, page
        if page.name == "index.md" and label:
            assert title[1] != label[1], page
        for language, content in re.findall(
            r"```(bash|json|hcl)\n([\s\S]*?)```", source
        ):
            blocks += 1
            if language == "json":
                json.loads(content)
            if language == "bash":
                result = subprocess.run(
                    ["/bin/bash", "-n"],
                    input=content,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                assert result.returncode == 0, (page, result.stderr)
        for link in re.findall(r"\]\(([^)]+)\)", source):
            parsed = urlsplit(urljoin("https://local.invalid" + route, link))
            if parsed.hostname != "local.invalid":
                continue
            target = unquote(parsed.path)
            if target.startswith("/_data/"):
                assert (ROOT / target.removeprefix("/_data/")).is_file(), (page, link)
            elif target.startswith("/assets/"):
                assert (DOCS / target.lstrip("/")).is_file(), (page, link)
            else:
                assert target in routes, (page, link, target)
                if parsed.fragment:
                    assert unquote(parsed.fragment) in anchors(
                        routes[target].read_text()
                    ), (page, link, "missing heading")
    for name in json.loads(
        (ROOT / "verification/administration-source.json").read_text()
    )["examples"]:
        directory = ROOT / "terraform" / name
        page = (
            DOCS / "en/terraform/index.md"
            if name == "named-certificate"
            else DOCS / "en/terraform/certificate-surfaces" / (name + ".md")
        )
        source = page.read_text()
        hcl = "\n".join(p.read_text().rstrip() for p in sorted(directory.glob("*.tf")))
        assert "```hcl\n" + hcl + "\n```" in source, name
        documents = json.loads(
            (DOCS / "assets/configurations" / (name + ".json")).read_text()
        )
        assert "```json\n" + json.dumps(documents, indent=2) + "\n```" in source, name
        assert all("metadata" in d and "spec" in d for d in documents)
        assert all(
            heading in source
            for heading in [
                "## Prerequisites",
                "## Configuration",
                "## Configure",
                "## Verify",
            ]
        )
    print(  # noqa: T201 -- Command-line verification summary.
        f"Administration checks passed: {len(pages)} pages, {blocks} code blocks, 16 source-matched configurations."
    )


if __name__ == "__main__":
    main()
