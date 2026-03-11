"""Check what Claude Code features exist that the user isn't leveraging.

Focuses on *feature discovery* — not just "is it missing" but "why it matters
and what you could do with it based on your usage patterns."
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


@dataclass
class McpMatch:
    """A specific MCP server matched from the catalog."""

    id: str
    name: str
    description: str
    replaces: str
    install: str
    requires_env: list[str]
    docs_url: str
    hit_count: int = 0       # number of conversation sample texts that matched
    matched_keywords: list[str] = field(default_factory=list)


@dataclass
class FeatureGap:
    """A Claude Code feature that is missing or underused."""

    feature: str
    present: bool
    description: str
    why_it_matters: str
    how_to_enable: str
    severity: str  # "high" | "medium" | "low"
    mcp_matches: list[McpMatch] = field(default_factory=list)  # populated for MCP gap


def audit(project_path: Path) -> list[FeatureGap]:
    """Check for underused Claude Code features in *project_path*.

    Returns a list of :class:`FeatureGap` objects, present and missing.
    """
    gaps: list[FeatureGap] = []

    gaps.append(_check_claude_md(project_path))
    gaps.append(_check_skills(project_path))
    gaps.append(_check_mcp(project_path))
    gaps.append(_check_local_claude_md(project_path))

    return gaps


def missing(project_path: Path) -> list[FeatureGap]:
    """Convenience: only return gaps where the feature is absent."""
    return [g for g in audit(project_path) if not g.present]


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_claude_md(project_path: Path) -> FeatureGap:
    present = (project_path / "CLAUDE.md").exists()
    return FeatureGap(
        feature="CLAUDE.md",
        present=present,
        description="Project instructions file loaded into every Claude Code conversation",
        why_it_matters=(
            "Without CLAUDE.md, Claude has no persistent context about your project. "
            "You'll keep re-explaining the same things every session."
        ),
        how_to_enable="Run `claude /init` to generate a starter CLAUDE.md, then use `ai-habits audit` to improve it.",
        severity="high",
    )


def _check_skills(project_path: Path) -> FeatureGap:
    local_skills = project_path / ".claude" / "skills"
    global_skills = Path.home() / ".claude" / "skills"
    present = (
        (local_skills.exists() and any(local_skills.rglob("SKILL.md")))
        or (global_skills.exists() and any(global_skills.rglob("SKILL.md")))
    )

    candidates = _skill_candidates_from_last_scan()
    if candidates:
        n = len(candidates)
        ids = ", ".join(c["id"] for c in candidates[:3])
        more = f" +{n - 3} more" if n > 3 else ""
        why = (
            f"You have {n} repeated pattern{'s' if n != 1 else ''} that would work as skills "
            f"({ids}{more}). Skills let you invoke complex recurring tasks in one command."
        )
        top_label = candidates[0].get("label") or candidates[0]["id"]
        how = (
            f"Run `ai-habits generate skill --id {candidates[0]['id']}` to create a draft "
            f"from your top pattern: \"{top_label[:60]}\"."
        )
        severity = "high" if not present else "medium"
    else:
        why = (
            "Skills let you invoke complex recurring tasks in one command. "
            "Run `ai-habits scan` first to find candidates in your conversation history."
        )
        how = "Run `ai-habits scan` to find skill candidates, then `ai-habits generate skill --id <id>`."
        severity = "medium"

    return FeatureGap(
        feature="Skills",
        present=present,
        description="Reusable prompts that can be invoked with a slash command",
        why_it_matters=why,
        how_to_enable=how,
        severity=severity,
    )


def _skill_candidates_from_last_scan() -> list[dict]:
    scan_path = Path.home() / ".ai-habits" / "last_scan.json"
    if not scan_path.exists():
        return []
    try:
        data = json.loads(scan_path.read_text())
        skill_categories = {"repeatable-workflow", "boilerplate-request", None}
        return [
            p for p in data.get("patterns", [])
            if p.get("category") in skill_categories and p.get("size", 0) >= 3
        ]
    except Exception:
        return []


def _check_mcp(project_path: Path) -> FeatureGap:
    """Check MCP server usage and match conversation history against the catalog."""
    settings_path = Path.home() / ".claude" / "settings.json"
    has_mcp = False
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
            has_mcp = bool(settings.get("mcpServers"))
        except Exception:
            pass

    matches = _mcp_matches_from_last_scan()

    if matches:
        top = matches[0]
        total_hits = sum(m.hit_count for m in matches)
        names = ", ".join(m.name for m in matches[:3])
        more = f" +{len(matches) - 3} more" if len(matches) > 3 else ""

        why = (
            f"Based on your conversations, {len(matches)} MCP server{'s' if len(matches) != 1 else ''} "
            f"could save you ~{total_hits} copy-paste{'s' if total_hits != 1 else ''} per scan window.\n"
            f"Matched: {names}{more}"
        )
        how = (
            f"Highest impact: {top.name}\n"
            f"  What it does: {top.replaces}\n"
            f"  Install:      {top.install}\n"
            f"  Config:       add to ~/.claude/settings.json under 'mcpServers'\n"
            f"  Docs:         {top.docs_url}"
        )
        severity = "high" if not has_mcp else "medium"
    else:
        why = (
            "MCP servers let Claude read GitHub issues, query databases, and access "
            "documentation without you copy-pasting context into the chat.\n"
            "Run `ai-habits scan` first for personalised server suggestions."
        )
        how = (
            "Browse the full catalog: https://github.com/modelcontextprotocol/servers\n"
            "Then add servers to ~/.claude/settings.json under 'mcpServers'."
        )
        severity = "low"

    return FeatureGap(
        feature="MCP Servers",
        present=has_mcp,
        description="Tools that let Claude fetch context automatically instead of you pasting it",
        why_it_matters=why,
        how_to_enable=how,
        severity=severity,
        mcp_matches=matches,
    )


# ---------------------------------------------------------------------------
# MCP catalog matching
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_catalog() -> list[dict]:
    """Load mcp_catalog.json bundled with the package."""
    catalog_path = Path(__file__).parent.parent / "data" / "mcp_catalog.json"
    try:
        return json.loads(catalog_path.read_text())
    except Exception:
        return []


def _mcp_matches_from_last_scan() -> list[McpMatch]:
    """Match last scan patterns against the MCP catalog.

    Returns McpMatch objects sorted by hit_count descending.
    """
    scan_path = Path.home() / ".ai-habits" / "last_scan.json"
    if not scan_path.exists():
        return []

    try:
        data = json.loads(scan_path.read_text())
        patterns = data.get("patterns", [])

        # Collect all sample texts from every pattern
        all_texts = [
            text.lower()
            for p in patterns
            for text in p.get("sample_texts", [])
        ]
        if not all_texts:
            return []

        catalog = _load_catalog()
        matches: list[McpMatch] = []

        for entry in catalog:
            hit_count = 0
            matched_kws: list[str] = []
            for kw in entry["keywords"]:
                kw_lower = kw.lower()
                hits = sum(1 for t in all_texts if kw_lower in t)
                if hits:
                    hit_count += hits
                    matched_kws.append(kw)

            if hit_count > 0:
                matches.append(McpMatch(
                    id=entry["id"],
                    name=entry["name"],
                    description=entry["description"],
                    replaces=entry["replaces"],
                    install=entry["install"],
                    requires_env=entry.get("requires_env", []),
                    docs_url=entry["docs_url"],
                    hit_count=hit_count,
                    matched_keywords=matched_kws,
                ))

        # Deduplicate by install command (e.g. github + github-actions share same server)
        seen_installs: set[str] = set()
        deduped: list[McpMatch] = []
        for m in sorted(matches, key=lambda x: x.hit_count, reverse=True):
            if m.install not in seen_installs:
                seen_installs.add(m.install)
                deduped.append(m)

        return deduped

    except Exception:
        return []


def _check_local_claude_md(project_path: Path) -> FeatureGap:
    local_dir = project_path / ".claude"
    present = local_dir.is_dir() and any(local_dir.glob("*.md"))
    return FeatureGap(
        feature=".claude/ directory",
        present=present,
        description="Project-local Claude Code config directory for skills, settings, and scripts",
        why_it_matters=(
            "The .claude/ directory lets you store project-specific skills and settings "
            "separately from your global ~/.claude/ config."
        ),
        how_to_enable="Create .claude/ in your project root. Add SKILL.md files under .claude/skills/.",
        severity="low",
    )
