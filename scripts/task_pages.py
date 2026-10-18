"""Render generated client task pages without changing stable overview bookmarks."""

import re
from pathlib import Path

STAGES = ("Prerequisites", "Configuration", "Configure", "Verify", "Maintain", "Remove")


def write_client_tasks(directory: Path, text: str) -> None:
    """Update task bodies while preserving descriptive metadata and navigation."""
    body = text.split("---", 2)[2]
    parts = re.split(
        r"^## (Prerequisites|Configuration|Configure|Verify|Maintain|Remove)\n",
        body,
        flags=re.MULTILINE,
    )
    sections = dict(zip(parts[1::2], parts[2::2], strict=True))
    configuration = sections["Configuration"]
    download = re.search(
        r'<div data-xcsh-context="shell"[^>]*>\s*```bash\n[\s\S]*?```\s*</div>',
        configuration,
    )
    if download is None:
        message = "Missing canonical download commands"
        raise ValueError(message)
    sections["Configure"] = (
        "\n## Download the shared configuration\n\n"
        + download[0]
        + "\n"
        + sections["Configure"]
    )
    configuration = configuration.replace(download[0], "")
    configuration = re.sub(
        r"```hcl\n[\s\S]*?```",
        "## Shared Terraform source\n\nThe complete shared HCL appears once in [Terraform Configuration](../terraform/configuration/). "
        "Download that root unchanged; client mTLS is its optional frontend extension.",
        configuration,
    )
    sections["Configuration"] = re.sub(
        r'(<div data-xcsh-context="json"[^>]*>\n+)',
        r"## Public JSON\n\n\1",
        configuration,
        count=1,
    )
    for stage in STAGES:
        page = directory / (stage.lower() + ".md")
        frontmatter = page.read_text().split("---", 2)[1]
        source = sections[stage]
        source = re.sub(
            r"\]\(([^)]+)\)",
            lambda match: (
                "]("
                + ("../" if not re.match(r"(?:https?:|/|#)", match[1]) else "")
                + match[1]
                + ")"
            ),
            source,
        )
        if not re.search(r"^## ", source, re.MULTILINE):
            source = "\n## " + stage + " steps\n" + source
        page.write_text("---" + frontmatter + "---\n\n" + source.strip() + "\n")
