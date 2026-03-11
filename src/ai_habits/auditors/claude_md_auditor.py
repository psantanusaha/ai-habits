"""Parse existing CLAUDE.md and flag stale or missing entries.

v0.2 feature — stubs present, full implementation ships in v0.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AuditFinding:
    """A single stale or missing entry in CLAUDE.md."""

    kind: str           # "stale" | "missing"
    section: str        # Which section of CLAUDE.md this relates to
    description: str    # Human-readable explanation
    evidence: list[str] = field(default_factory=list)  # Supporting conversation snippets
    suggestion: str = ""


def audit(
    project_path: Path,
    conversation_messages: list | None = None,
) -> list[AuditFinding]:
    """Compare CLAUDE.md against conversation history.

    Args:
        project_path: Root of the project.
        conversation_messages: List of Message objects from the scanner.
            If None or empty, only checks for presence/structure.

    Returns:
        List of findings (stale + missing entries).
    """
    claude_md = project_path / "CLAUDE.md"
    if not claude_md.exists():
        return [
            AuditFinding(
                kind="missing",
                section="CLAUDE.md",
                description="No CLAUDE.md found. Run `claude /init` to create one.",
                suggestion="claude /init",
            )
        ]

    # v0.2: full implementation will parse CLAUDE.md sections and compare
    # against conversation content using embeddings.
    # For now, return an empty list (no findings) as a stub.
    return []
