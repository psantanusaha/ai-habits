"""Pre-built catalog of common AI assistant anti-patterns.

These are heuristic checks that don't require clustering — they look for
known bad behaviors in raw message text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai_habits.scanners.base import Message


@dataclass
class AntiPatternMatch:
    """A detected anti-pattern instance."""

    name: str
    description: str
    suggestion: str
    matching_messages: list[Message]

    @property
    def count(self) -> int:
        return len(self.matching_messages)


# ---------------------------------------------------------------------------
# Anti-pattern rules
# Each rule: (name, description, suggestion, regex_pattern)
# ---------------------------------------------------------------------------

_RULES: list[tuple[str, str, str, str]] = [
    (
        "no-context-preamble",
        "You start many conversations by re-explaining the same project context.",
        "Add your stack, architecture, and conventions to CLAUDE.md so Claude always has this context.",
        r"(?i)(this project (uses|is|has)|we (use|are using)|our (stack|setup|project) (is|uses)|i('m| am) working on)",
    ),
    (
        "do-it-same-as-before",
        'You frequently ask Claude to "do it the same way as last time" — but Claude has no memory.',
        "Create a skill or add recurring patterns to CLAUDE.md so Claude has the context without you re-stating it.",
        r"(?i)(same (way|approach|style|format) (as|like) (before|last time|previously)|like you did (before|last time))",
    ),
    (
        "version-specification",
        "You repeatedly specify version numbers for the same tools/frameworks.",
        "Document your pinned versions in CLAUDE.md so you don't need to repeat them.",
        r"(?i)(python 3\.\d+|node (v?\d+)|react \d+|fastapi \d+|next\.?js \d+)",
    ),
    (
        "auth-setup-repeat",
        "You frequently describe your auth setup to Claude.",
        "Document your auth architecture in CLAUDE.md — it's clearly a core system Claude needs to know about.",
        r"(?i)(jwt|oauth|auth(entication|orization)|session (token|cookie)|api key|bearer token)",
    ),
    (
        "test-framework-clarify",
        "You keep telling Claude which test framework to use.",
        'Add "Use pytest (not unittest)" or equivalent to your CLAUDE.md.',
        r"(?i)(use pytest|don('t| not) use unittest|use jest (not|instead)|use vitest)",
    ),
]


def detect(messages: list[Message]) -> list[AntiPatternMatch]:
    """Run anti-pattern rules over *messages*.

    Returns only anti-patterns that match at least 2 messages.
    """
    results: list[AntiPatternMatch] = []
    for name, description, suggestion, pattern in _RULES:
        regex = re.compile(pattern)
        matches = [m for m in messages if regex.search(m.text)]
        if len(matches) >= 2:
            results.append(
                AntiPatternMatch(
                    name=name,
                    description=description,
                    suggestion=suggestion,
                    matching_messages=matches,
                )
            )
    return sorted(results, key=lambda r: r.count, reverse=True)
