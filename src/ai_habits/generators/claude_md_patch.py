"""Generate additions to an existing CLAUDE.md.

We NEVER replace the file. We only produce new sections that the user
can append/merge. Every section has a comment explaining the evidence.

v0.3 feature — stub present, full implementation ships in v0.3.
"""

from __future__ import annotations

from pathlib import Path

from ai_habits.patterns.clustering import Pattern


def generate_patch(
    project_path: Path,
    patterns: list[Pattern],
    output_path: Path | None = None,
) -> Path:
    """Generate a CLAUDE.md.patch file with suggested additions.

    Args:
        project_path: Root of the project (CLAUDE.md must exist here).
        patterns: Classified patterns from the scan.
        output_path: Where to write the patch (default: CLAUDE.md.patch).

    Returns:
        Path of the written patch file.
    """
    claude_md = project_path / "CLAUDE.md"
    if not claude_md.exists():
        raise FileNotFoundError(
            f"No CLAUDE.md found at {claude_md}. "
            "Run `claude /init` to create one first."
        )

    if output_path is None:
        output_path = project_path / "CLAUDE.md.patch"

    sections: list[str] = [_header()]

    context_patterns = [p for p in patterns if p.category == "context-re-explanation"]
    if context_patterns:
        sections.append(_context_section(context_patterns))

    if not context_patterns:
        sections.append(
            "<!-- No context re-explanation patterns detected. "
            "Run `ai-habits scan` with more history for better suggestions. -->"
        )

    output_path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    return output_path


def _header() -> str:
    return """\
<!-- ai-habits CLAUDE.md patch — REVIEW BEFORE APPLYING -->
<!-- Append these sections to your CLAUDE.md or merge them manually. -->
<!-- Evidence for each suggestion is noted inline. -->
"""


def _context_section(patterns: list[Pattern]) -> str:
    lines = [
        "## Project Context",
        "<!-- SUGGESTED ADDITION — You re-explained this context in multiple conversations. -->",
        "<!-- ai-habits evidence: found in the following patterns: "
        + ", ".join(p.id for p in patterns)
        + " -->",
        "",
        "<!-- TODO: Fill in the actual details — these are placeholders based on pattern analysis -->",
    ]
    for pat in patterns:
        if pat.sample_texts:
            lines.append(f"<!-- Pattern '{pat.id}' sample: {pat.sample_texts[0][:100]} -->")
    lines += [
        "",
        "- TODO: [Add the context you keep re-explaining]",
    ]
    return "\n".join(lines)
