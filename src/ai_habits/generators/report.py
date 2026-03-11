"""Rich-formatted terminal output for ai-habits commands."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from ai_habits.patterns.clustering import Pattern
from ai_habits.patterns.anti_patterns import AntiPatternMatch
from ai_habits.auditors.feature_auditor import FeatureGap

console = Console()

# Category metadata: category → (emoji, label, action hint)
_CATEGORY_DISPLAY: dict[str, tuple[str, str, str]] = {
    "repeatable-workflow":    ("🔁", "Repeated workflow",    "generate skill"),
    "boilerplate-request":    ("📋", "Boilerplate/scaffold", "generate skill"),
    "context-re-explanation": ("🔄", "Context re-explained", "generate patch"),
    "one-off-task":           ("✨", "One-off task",         ""),
    None:                     ("📌", "Uncategorized",        "generate skill"),
}


def print_scan_report(
    patterns: list[Pattern],
    anti_pattern_matches: list[AntiPatternMatch],
    scanned_sessions: int,
    scanned_messages: int,
    since: str,
) -> None:
    """Print the full `ai-habits scan` report."""
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]ai-habits scan[/bold cyan]  [dim]{since}[/dim]",
        border_style="cyan",
    ))
    console.print(
        f"[dim]Scanned [bold]{scanned_sessions}[/bold] conversations, "
        f"[bold]{scanned_messages}[/bold] user messages[/dim]\n"
    )

    if not patterns and not anti_pattern_matches:
        console.print("[yellow]No patterns found.[/yellow]")
        console.print(
            "[dim]Try lowering --min-occurrences or widening --last window.[/dim]"
        )
        return

    if patterns:
        console.print("[bold]🔁 REPEATED PATTERNS[/bold]")
        for i, pat in enumerate(patterns, 1):
            _print_pattern(pat, i)

    if anti_pattern_matches:
        console.print("\n[bold]⚠️  ANTI-PATTERNS[/bold]")
        for match in anti_pattern_matches:
            _print_anti_pattern(match)

    console.print(
        "\n[dim]Run [bold]ai-habits generate skill --id <id>[/bold] "
        "or [bold]ai-habits generate patch --id <id>[/bold] to act on a pattern.[/dim]\n"
    )


def _print_pattern(pat: Pattern, index: int) -> None:
    emoji, label_str, action = _CATEGORY_DISPLAY.get(
        pat.category, _CATEGORY_DISPLAY[None]
    )
    category_tag = f"[bold]{emoji} {pat.category or 'unclassified'}[/bold]"

    header = Text()
    header.append(f"  {index}. ", style="bold white")
    header.append(f"{pat.label or pat.id}", style="bold yellow")
    header.append(f" — {pat.size} occurrence{'s' if pat.size != 1 else ''}", style="dim")
    console.print(header)

    console.print(f"     │ Type: {category_tag}")

    # Dates summary
    dates = pat.dates
    if dates:
        date_strs = [d.strftime("%b %-d") for d in dates[:6]]
        more = f" +{len(dates)-6} more" if len(dates) > 6 else ""
        console.print(f"     │ Dates: [dim]{', '.join(date_strs)}{more}[/dim]")

    # Sample message
    if pat.sample_texts:
        sample = pat.sample_texts[0][:80].replace("\n", " ")
        console.print(f"     │ Sample: [italic dim]\"{sample}\"[/italic dim]")

    # Action hint
    if action:
        console.print(
            f"     └─ [green]💡 {_action_hint(pat, action)}[/green]"
        )
    console.print()


def _action_hint(pat: Pattern, action: str) -> str:
    if action == "generate skill":
        return f"Skill candidate → [bold]ai-habits generate skill --id {pat.id}[/bold]"
    elif action == "generate patch":
        return f"Add to CLAUDE.md → [bold]ai-habits generate patch --id {pat.id}[/bold]"
    return ""


def _print_anti_pattern(match: AntiPatternMatch) -> None:
    console.print(f"  [bold yellow]{match.name}[/bold yellow] ({match.count} occurrences)")
    console.print(f"  {match.description}")
    console.print(f"  [green]💡 {match.suggestion}[/green]")
    console.print()


def print_discover_report(gaps: list[FeatureGap], project_path: Path) -> None:
    """Print the `ai-habits discover` report."""
    console.print()
    console.print(Panel.fit(
        "[bold yellow]ai-habits discover[/bold yellow]",
        border_style="yellow",
    ))
    console.print(f"[dim]Project: {project_path}[/dim]\n")

    present = [g for g in gaps if g.present]
    missing = [g for g in gaps if not g.present]

    if present:
        for gap in present:
            console.print(f"[green]✓[/green] [bold]{gap.feature}[/bold]")

    if missing:
        console.print()
        for gap in missing:
            sev_color = {"high": "red", "medium": "yellow", "low": "dim"}.get(gap.severity, "white")
            console.print(f"[{sev_color}]✗[/{sev_color}] [bold]{gap.feature}[/bold]")
            console.print(f"  {gap.why_it_matters}")
            console.print(f"  [green]→ {gap.how_to_enable}[/green]")
            console.print()
    else:
        console.print("\n[green]All tracked Claude Code features are present![/green]\n")


def print_audit_report(findings: list, project_path: Path) -> None:
    """Print the `ai-habits audit` report."""
    console.print()
    console.print(Panel.fit(
        "[bold magenta]ai-habits audit[/bold magenta]",
        border_style="magenta",
    ))
    console.print(f"[dim]Project: {project_path}[/dim]\n")

    if not findings:
        console.print("[green]✓ CLAUDE.md looks good — no stale or missing entries detected.[/green]")
        console.print("[dim](Full audit requires conversation history — run ai-habits scan first)[/dim]\n")
        return

    for finding in findings:
        icon = "⚠️" if finding.kind == "stale" else "❌"
        console.print(f"{icon}  [bold]{finding.kind.upper()}[/bold]: {finding.section}")
        console.print(f"   {finding.description}")
        if finding.suggestion:
            console.print(f"   [green]→ {finding.suggestion}[/green]")
        console.print()


# ---------------------------------------------------------------------------
# Scan result persistence
# ---------------------------------------------------------------------------

AI_HABITS_DIR = Path.home() / ".ai-habits"


def save_scan_results(patterns: list[Pattern]) -> Path:
    """Persist scan results to ~/.ai-habits/last_scan.json.

    Returns the path of the saved file.
    """
    AI_HABITS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = AI_HABITS_DIR / "last_scan.json"

    data = {
        "saved_at": datetime.utcnow().isoformat() + "Z",
        "patterns": [_pattern_to_dict(p) for p in patterns],
    }
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return output_path


def load_scan_results() -> list[dict]:
    """Load the last scan results from ~/.ai-habits/last_scan.json.

    Returns a list of pattern dicts, or empty list if none exist.
    """
    path = AI_HABITS_DIR / "last_scan.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())["patterns"]
    except Exception:
        return []


def _pattern_to_dict(pat: Pattern) -> dict:
    return {
        "id": pat.id,
        "label": pat.label,
        "category": pat.category,
        "size": pat.size,
        "sample_texts": pat.sample_texts,
        "dates": [d.isoformat() for d in pat.dates[:10]],
    }
