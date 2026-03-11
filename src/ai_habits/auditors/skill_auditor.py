"""Identify where skills should exist but don't.

v0.2 feature — stubs present, full implementation ships in v0.2.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_habits.patterns.clustering import Pattern


@dataclass
class SkillGap:
    """A pattern cluster that should be a skill but isn't."""

    pattern: Pattern
    reason: str
    suggested_name: str
    suggested_path: str  # e.g. ".claude/skills/fastapi-scaffold/SKILL.md"


def find_gaps(
    patterns: list[Pattern],
    project_path: Path,
) -> list[SkillGap]:
    """Return patterns that are strong skill candidates.

    A pattern is a skill candidate if:
    - It is classified as repeatable-workflow or boilerplate-request
    - It occurs >= 3 times
    - No corresponding skill already exists

    v0.2: full implementation. For now, return basic candidates.
    """
    gaps: list[SkillGap] = []
    skill_candidates = {"repeatable-workflow", "boilerplate-request"}

    for pat in patterns:
        if pat.size < 3:
            continue
        if pat.category not in skill_candidates and pat.category is not None:
            continue

        # Derive a slug from the label
        label = pat.label or f"pattern-{pat.id}"
        slug = _to_slug(label)
        skill_path = f".claude/skills/{slug}/SKILL.md"

        # Check if skill already exists
        if (project_path / skill_path).exists():
            continue

        gaps.append(
            SkillGap(
                pattern=pat,
                reason=(
                    f"Occurred {pat.size} times "
                    f"({pat.category or 'unclassified'}) — "
                    "consistent enough to be a skill."
                ),
                suggested_name=slug,
                suggested_path=skill_path,
            )
        )
    return gaps


def _to_slug(text: str) -> str:
    """Convert text to a lowercase hyphenated slug."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:50].strip("-") or "pattern"
