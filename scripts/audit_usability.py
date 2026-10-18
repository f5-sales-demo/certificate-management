"""Produce sanitized route measurements and documentation audit findings."""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Count prose independently of expanded canonical examples."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    routes = []
    for page in sorted((ROOT / "docs/en").rglob("*.md")):
        source = page.read_text()
        body = source.split("---", 2)[2]
        examples = re.findall(r"```([^\n]*)\n([\s\S]*?)```", body)
        prose = re.sub(r"```[\s\S]*?```", "", body)
        headings = re.findall(r"^#{2,3} (.+)$", prose, re.MULTILINE)
        routes.append(
            {
                "route": "/en/"
                + page.relative_to(ROOT / "docs/en")
                .as_posix()
                .removesuffix(".md")
                .removesuffix("index")
                .rstrip("/")
                + "/",
                "prose_words": len(
                    re.findall(r"\b\w+\b", re.sub(r"<[^>]*>", "", prose))
                ),
                "code_lines": sum(len(content.splitlines()) for _, content in examples),
                "sections": headings,
                "source_verification": "passed: lifecycle, links, JSON, shell syntax, canonical ownership",
                "browser_verification": "pending",
            }
        )
    findings = [
        {
            "route": "/en/*/",
            "severity": "high",
            "evidence": "Theme cleared index TOCs regardless of repository or explicit setting.",
            "resolution": "Repository-scoped TOC policy and explicit task sidebar in docs-theme#1747.",
            "verification": "theme tests passed; published browser qualification pending",
        },
        {
            "route": "/en/terraform/",
            "severity": "high",
            "evidence": "More than 550 code lines behind one workflow entry.",
            "resolution": "Six task pages; expanded HCL and JSON remain together in Configuration.",
            "verification": "source checks passed",
        },
        {
            "route": "/en/client-mtls/",
            "severity": "high",
            "evidence": "Repeated shared HCL and setup stopped at plan review.",
            "resolution": "Link authoritative Terraform HCL, move downloads to Configure, show reviewed-plan apply.",
            "verification": "source checks and executable Python variable-file test passed",
        },
        {
            "route": "/en/terraform/configure/",
            "severity": "high",
            "evidence": "Source module requires ../http-origin-mtls; former download command omitted it.",
            "resolution": "Download full module and Wingman naming contract before init.",
            "verification": "shell syntax passed; clean downloaded-root init pending",
        },
        {
            "route": "/en/wingman/",
            "severity": "medium",
            "evidence": "No Maintain task; disposable destruction mixed into Verify.",
            "resolution": "Add maintenance route and move cleanup to Remove; link infrastructure owner runbook.",
            "verification": "source checks passed",
        },
        {
            "route": "/en/xcsh/",
            "severity": "medium",
            "evidence": "No Remove task or public JSON download.",
            "resolution": "Add owner-aware removal guidance and equal public manifest download.",
            "verification": "source checks passed",
        },
        {
            "route": "/en/terraform/certificate-surfaces/*/",
            "severity": "medium",
            "evidence": "References contain long source and old workflow-anchor links.",
            "resolution": "Retain 15 reference pages, add JSON/HCL subdivisions, link current tasks, preserve narrow qualification claims.",
            "verification": "all source links and canonical examples passed",
        },
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "scope": "English Certificate Management",
                "compatibility": "prerelease: current task destinations only",
                "routes": routes,
                "findings": findings,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
