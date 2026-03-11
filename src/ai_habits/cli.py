"""Click CLI entry point for ai-habits."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
from rich.console import Console

from ai_habits import __version__

console = Console()


def _parse_since(last: str) -> datetime:
    """Parse a duration string like '30d', '7d', '90d' into a datetime."""
    try:
        days = int(last.rstrip("d"))
    except ValueError:
        raise click.BadParameter(f"Invalid duration: {last!r}. Use format like '30d'.")
    return datetime.now(tz=timezone.utc) - timedelta(days=days)


@click.group()
@click.version_option(__version__, prog_name="ai-habits")
def cli() -> None:
    """AI workflow efficiency tool — find patterns in how you use Claude.

    Run `ai-habits scan` to get started.
    """


# ---------------------------------------------------------------------------
# ai-habits scan
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--last", default="30d", show_default=True, help="Lookback window (e.g. 30d, 90d)")
@click.option("--min-occurrences", default=3, show_default=True, help="Min messages to form a pattern")
@click.option("--similarity", default=0.75, show_default=True, type=float, help="Clustering similarity threshold (0–1)")
@click.option("--project", default=None, type=click.Path(path_type=Path), help="Filter to a specific project path")
@click.option("--no-llm", is_flag=True, help="Skip LLM classification pass")
def scan(
    last: str,
    min_occurrences: int,
    similarity: float,
    project: Path | None,
    no_llm: bool,
) -> None:
    """Scan conversation history for repeated patterns.

    Reads Claude Code logs, embeds and clusters your messages,
    then classifies clusters into actionable categories.
    Results are saved to ~/.ai-habits/last_scan.json.

    \b
    Examples:
      ai-habits scan
      ai-habits scan --last 90d --min-occurrences 2
      ai-habits scan --project /path/to/my-project
    """
    from ai_habits.scanners.claude_code import ClaudeCodeScanner
    from ai_habits.patterns import clustering, classifier, anti_patterns
    from ai_habits.generators.report import print_scan_report, save_scan_results

    from ai_habits.utils.embeddings import neural_available
    if not neural_available():
        console.print(
            "[dim]Using TF-IDF clustering (keyword-based). "
            "For better accuracy: [bold]pip install 'ai-habits[ml]'[/bold][/dim]\n"
        )

    since = _parse_since(last)

    console.print(f"[dim]Scanning conversations since {since.strftime('%Y-%m-%d')}...[/dim]")

    scanner = ClaudeCodeScanner()
    messages = scanner.all_messages(
        project_path=project.resolve() if project else None,
        since=since,
    )

    if not messages:
        console.print(
            "[yellow]No messages found.[/yellow]\n"
            "Make sure Claude Code has been used and logs exist at ~/.claude/projects/"
        )
        return

    # Filter noise before clustering:
    # - Short acknowledgements ("done", "yes", "git stash them")
    # - System-injected preambles from Claude Code skill/agent mechanism
    _MIN_MSG_LEN = 25
    _NOISE_PREFIXES = (
        "base directory for this skill",
        "[request interrupted",
        "<local-command",
        "<task-notification",
        "this session is being continued",
        "conversation so far:",
    )
    clusterable = [
        m for m in messages
        if len(m.text.strip()) >= _MIN_MSG_LEN
        and not m.text.strip().lower().startswith(_NOISE_PREFIXES)
    ]

    console.print(f"[dim]Found {len(messages)} messages ({len(clusterable)} substantial). Clustering...[/dim]")

    patterns = clustering.cluster(
        clusterable,
        similarity_threshold=similarity,
        min_cluster_size=min_occurrences,
    )

    # Always assign heuristic labels (uses representative_text, no API needed)
    for pat in patterns:
        if not pat.label:
            pat.label = classifier._infer_label(pat)

    if patterns and not no_llm:
        console.print("[dim]Running classification pass...[/dim]")
        patterns = classifier.classify(patterns)

    anti_pattern_matches = anti_patterns.detect(messages)

    # Count sessions
    session_ids = {m.session_id for m in messages}

    print_scan_report(
        patterns=patterns,
        anti_pattern_matches=anti_pattern_matches,
        scanned_sessions=len(session_ids),
        scanned_messages=len(messages),
        since=f"last {last}",
    )

    if patterns:
        saved = save_scan_results(patterns)
        console.print(f"[dim]Results saved to {saved}[/dim]\n")


# ---------------------------------------------------------------------------
# ai-habits discover
# ---------------------------------------------------------------------------

@cli.command()
@click.argument(
    "project_dir",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
def discover(project_dir: Path) -> None:
    """Show underused Claude Code features based on your setup.

    Checks for: CLAUDE.md, skills directory, MCP servers, .claude/ directory.

    \b
    Examples:
      ai-habits discover
      ai-habits discover /path/to/my-project
    """
    from ai_habits.auditors import feature_auditor
    from ai_habits.generators.report import print_discover_report

    project_dir = project_dir.resolve()
    gaps = feature_auditor.audit(project_dir)
    print_discover_report(gaps, project_dir)


# ---------------------------------------------------------------------------
# ai-habits audit
# ---------------------------------------------------------------------------

@cli.command()
@click.argument(
    "project_dir",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
def audit(project_dir: Path) -> None:
    """Audit your CLAUDE.md against actual conversation behavior.

    Flags stale entries (contradicted by recent conversations) and missing
    entries (context you keep re-explaining that isn't in the file).

    Requires CLAUDE.md to exist — run `claude /init` first if needed.

    \b
    Examples:
      ai-habits audit
      ai-habits audit /path/to/my-project
    """
    from ai_habits.auditors import claude_md_auditor
    from ai_habits.generators.report import print_audit_report, load_scan_results

    project_dir = project_dir.resolve()

    claude_md = project_dir / "CLAUDE.md"
    if not claude_md.exists():
        console.print(
            "[red]⛔ No CLAUDE.md found.[/red]\n"
            "Run [bold]claude /init[/bold] to generate one, "
            "then use [bold]ai-habits audit[/bold] to improve it."
        )
        raise SystemExit(1)

    # Load last scan results if available
    scan_data = load_scan_results()
    findings = claude_md_auditor.audit(project_dir)
    print_audit_report(findings, project_dir)

    if not scan_data:
        console.print(
            "[dim]Tip: Run [bold]ai-habits scan[/bold] first for deeper audit results.[/dim]\n"
        )


# ---------------------------------------------------------------------------
# ai-habits explain
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--id", "pattern_id", required=True, help="Pattern ID from last scan (e.g. pat-001)")
def explain(pattern_id: str) -> None:
    """Show how a detected pattern would have been helped by a skill/config.

    Loads the last scan results and shows the conversations where the pattern
    appeared, with an explanation of what the generated artifact would have done.

    \b
    Examples:
      ai-habits explain --id pat-001
    """
    from ai_habits.generators.report import load_scan_results

    patterns = load_scan_results()
    if not patterns:
        console.print(
            "[yellow]No scan results found.[/yellow]\n"
            "Run [bold]ai-habits scan[/bold] first."
        )
        return

    match = next((p for p in patterns if p["id"] == pattern_id), None)
    if not match:
        available = ", ".join(p["id"] for p in patterns)
        console.print(
            f"[red]Pattern '{pattern_id}' not found.[/red]\n"
            f"Available IDs: {available}"
        )
        return

    console.print(f"\n[bold]Pattern: {match.get('label', pattern_id)}[/bold]")
    console.print(f"[dim]ID: {match['id']} | Category: {match.get('category', 'unclassified')} | {match['size']} occurrences[/dim]\n")

    console.print("[bold]Sample messages:[/bold]")
    for i, text in enumerate(match.get("sample_texts", [])[:5], 1):
        console.print(f"  {i}. {text[:100]}")

    console.print()
    category = match.get("category")
    if category in ("repeatable-workflow", "boilerplate-request"):
        console.print(
            f"[green]💡 This is a skill candidate.[/green]\n"
            f"Run: [bold]ai-habits generate skill --id {pattern_id}[/bold]"
        )
    elif category == "context-re-explanation":
        console.print(
            f"[green]💡 This context should be in your CLAUDE.md.[/green]\n"
            f"Run: [bold]ai-habits generate patch --id {pattern_id}[/bold]"
        )
    else:
        console.print(
            f"[dim]No specific action available for category: {category}[/dim]"
        )
    console.print()


# ---------------------------------------------------------------------------
# ai-habits generate
# ---------------------------------------------------------------------------

@cli.group()
def generate() -> None:
    """Generate draft artifacts from detected patterns."""


@generate.command("skill")
@click.option("--id", "pattern_id", required=True, help="Pattern ID from last scan")
@click.option("--output-dir", default=None, type=click.Path(path_type=Path))
def generate_skill(pattern_id: str, output_dir: Path | None) -> None:
    """Generate a SKILL.md draft from a detected pattern.

    \b
    Examples:
      ai-habits generate skill --id pat-001
    """
    pattern = _load_pattern(pattern_id)
    if pattern is None:
        return

    from ai_habits.patterns.clustering import Pattern
    from ai_habits.generators.skill_generator import generate_skill as _gen
    import numpy as np

    pat_obj = _dict_to_pattern(pattern)
    path = _gen(pat_obj, output_dir=output_dir)
    console.print(f"[green]Skill draft written:[/green] {path}")
    console.print("[dim]Review and customise before committing.[/dim]\n")


@generate.command("patch")
@click.option("--id", "pattern_id", default=None, help="Pattern ID (optional — uses all context-re-explanation patterns)")
@click.argument("project_dir", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path))
def generate_patch(pattern_id: str | None, project_dir: Path) -> None:
    """Generate a CLAUDE.md patch with missing context.

    \b
    Examples:
      ai-habits generate patch
      ai-habits generate patch --id pat-002
    """
    from ai_habits.generators.claude_md_patch import generate_patch as _gen
    from ai_habits.patterns.clustering import Pattern

    all_patterns = load_patterns_from_scan()
    if pattern_id:
        pats = [p for p in all_patterns if p["id"] == pattern_id]
    else:
        pats = [p for p in all_patterns if p.get("category") == "context-re-explanation"]

    pat_objs = [_dict_to_pattern(p) for p in pats]
    project_dir = project_dir.resolve()
    try:
        path = _gen(project_dir, pat_objs)
        console.print(f"[green]Patch written:[/green] {path}")
        console.print("[dim]Review the patch, then apply it to your CLAUDE.md.[/dim]\n")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")


@generate.command("script")
@click.option("--id", "pattern_id", required=True, help="Pattern ID from last scan")
@click.option("--output-dir", default=None, type=click.Path(path_type=Path))
def generate_script(pattern_id: str, output_dir: Path | None) -> None:
    """Generate a shell script from a sequential workflow pattern.

    \b
    Examples:
      ai-habits generate script --id pat-003
    """
    pattern = _load_pattern(pattern_id)
    if pattern is None:
        return

    from ai_habits.generators.script_generator import generate_script as _gen
    pat_obj = _dict_to_pattern(pattern)
    path = _gen(pat_obj, output_dir=output_dir)
    console.print(f"[green]Script written:[/green] {path}")
    console.print("[dim]Review the script before running it.[/dim]\n")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_pattern(pattern_id: str) -> dict | None:
    """Load a single pattern by ID from the last scan. Prints error if missing."""
    from ai_habits.generators.report import load_scan_results
    patterns = load_scan_results()
    if not patterns:
        console.print(
            "[yellow]No scan results found.[/yellow]\n"
            "Run [bold]ai-habits scan[/bold] first."
        )
        return None
    match = next((p for p in patterns if p["id"] == pattern_id), None)
    if not match:
        available = ", ".join(p["id"] for p in patterns)
        console.print(
            f"[red]Pattern '{pattern_id}' not found.[/red]\n"
            f"Available: {available}"
        )
        return None
    return match


def load_patterns_from_scan() -> list[dict]:
    from ai_habits.generators.report import load_scan_results
    return load_scan_results()


def _dict_to_pattern(d: dict):
    """Reconstruct a lightweight Pattern-like object from a persisted dict."""
    from ai_habits.patterns.clustering import Pattern
    import numpy as np
    from ai_habits.scanners.base import Message
    from datetime import datetime, timezone

    # Build stub Message objects so Pattern.dates / sample_texts work
    msgs = []
    for i, text in enumerate(d.get("sample_texts", [])):
        msgs.append(Message(
            uuid=f"stub-{i}",
            session_id="stub",
            project_path=Path("."),
            timestamp=datetime.now(tz=timezone.utc),
            text=text,
        ))

    pat = Pattern(
        id=d["id"],
        messages=msgs,
        centroid=np.zeros(384, dtype=np.float32),
        category=d.get("category"),
        label=d.get("label"),
    )
    return pat
