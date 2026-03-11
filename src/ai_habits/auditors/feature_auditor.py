"""Check what Claude Code features exist that the user isn't leveraging.

Focuses on *feature discovery* — not just "is it missing" but "why it matters
and what you could do with it based on your usage patterns."
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FeatureGap:
    """A Claude Code feature that is missing or underused."""

    feature: str
    present: bool
    description: str
    why_it_matters: str
    how_to_enable: str
    severity: str  # "high" | "medium" | "low"


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
    # Skills can be in ~/.claude/skills/ (global) or .claude/skills/ (local)
    local_skills = project_path / ".claude" / "skills"
    global_skills = Path.home() / ".claude" / "skills"
    present = (
        (local_skills.exists() and any(local_skills.rglob("SKILL.md")))
        or (global_skills.exists() and any(global_skills.rglob("SKILL.md")))
    )

    # Cross-reference last scan for concrete evidence
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
    """Load last_scan.json and return patterns that are skill candidates."""
    scan_path = Path.home() / ".ai-habits" / "last_scan.json"
    if not scan_path.exists():
        return []
    try:
        import json
        data = json.loads(scan_path.read_text())
        skill_categories = {"repeatable-workflow", "boilerplate-request", None}
        return [
            p for p in data.get("patterns", [])
            if p.get("category") in skill_categories and p.get("size", 0) >= 3
        ]
    except Exception:
        return []


def _check_mcp(project_path: Path) -> FeatureGap:
    # MCP config in ~/.claude/settings.json under mcpServers key
    settings_path = Path.home() / ".claude" / "settings.json"
    has_mcp = False
    if settings_path.exists():
        try:
            import json
            settings = json.loads(settings_path.read_text())
            has_mcp = bool(settings.get("mcpServers"))
        except Exception:
            pass

    suggestions = _mcp_suggestions_from_last_scan()

    if suggestions:
        why = (
            "Based on your conversation history, you're manually providing context "
            "that MCP servers could fetch automatically — saving tokens every session.\n"
            + "\n".join(f"  • {s}" for s in suggestions)
        )
        how = (
            "Add the relevant servers to ~/.claude/settings.json under 'mcpServers'.\n"
            "Browse available servers: https://github.com/modelcontextprotocol/servers"
        )
        severity = "medium"
    else:
        why = (
            "MCP servers let Claude read GitHub issues, query databases, and access "
            "documentation without you copy-pasting context into the chat."
        )
        how = (
            "Run `ai-habits scan` first to get personalised MCP suggestions, or browse "
            "available servers: https://github.com/modelcontextprotocol/servers"
        )
        severity = "low"

    return FeatureGap(
        feature="MCP Servers",
        present=has_mcp,
        description="Tools that let Claude fetch context automatically instead of you pasting it",
        why_it_matters=why,
        how_to_enable=how,
        severity=severity,
    )


# MCP server detection rules: (keyword_patterns, server_name, what_it_does)
_MCP_RULES: list[tuple[list[str], str, str]] = [
    (
        ["github", "issue", "pull request", "pr #", "repo", "commit"],
        "GitHub MCP",
        "You reference GitHub content repeatedly — GitHub MCP lets Claude read issues/PRs directly",
    ),
    (
        ["select ", "from ", "query", "database", "sql", "postgres", "mysql"],
        "Database MCP",
        "You paste query results into conversations — a DB MCP lets Claude query directly",
    ),
    (
        ["docs", "documentation", "api reference", "read the docs", "rtfd"],
        "Fetch/Browser MCP",
        "You reference external documentation — Fetch MCP lets Claude read URLs without copy-paste",
    ),
    (
        ["jira", "ticket", "sprint", "confluence"],
        "Atlassian MCP",
        "You reference Jira/Confluence content — Atlassian MCP lets Claude access it directly",
    ),
    (
        ["slack", "message", "channel", "dm"],
        "Slack MCP",
        "You reference Slack messages — Slack MCP lets Claude read them without copy-paste",
    ),
]


def _mcp_suggestions_from_last_scan() -> list[str]:
    """Analyse last scan patterns to suggest specific MCP servers."""
    scan_path = Path.home() / ".ai-habits" / "last_scan.json"
    if not scan_path.exists():
        return []

    try:
        import json
        data = json.loads(scan_path.read_text())
        patterns = data.get("patterns", [])

        # Collect all sample texts from patterns
        all_text = " ".join(
            text.lower()
            for p in patterns
            for text in p.get("sample_texts", [])
        )

        suggestions: list[str] = []
        for keywords, server_name, description in _MCP_RULES:
            if any(kw in all_text for kw in keywords):
                suggestions.append(description)

        return suggestions
    except Exception:
        return []


def _check_local_claude_md(project_path: Path) -> FeatureGap:
    """Check if user knows about .claude/CLAUDE.md for sub-directory context."""
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
