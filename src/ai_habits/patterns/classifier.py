"""LLM classification pass for pattern clusters.

Takes raw clusters from clustering.py and adds a human-readable category
and label. Falls back gracefully if no API key is available.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_habits.patterns.clustering import Pattern

if TYPE_CHECKING:
    pass  # Pattern already imported above
from ai_habits.utils import llm

logger = logging.getLogger(__name__)

# Category → emoji + description shown in the report
CATEGORY_META: dict[str, tuple[str, str]] = {
    "repeatable-workflow":    ("🔁", "Repeated workflow"),
    "boilerplate-request":    ("📋", "Boilerplate/scaffolding"),
    "context-re-explanation": ("🔄", "Context re-explained"),
    "one-off-task":           ("✨", "One-off task"),
}


def classify(patterns: list[Pattern]) -> list[Pattern]:
    """Add category + label to each pattern in *patterns*.

    Modifies patterns in-place and returns the list with one-off tasks removed.

    If the Anthropic API is unavailable, patterns get category=None and are
    not filtered — all are shown with a note that classification was skipped.
    """
    api_available = _check_api()

    for pat in patterns:
        if api_available:
            category = llm.classify_cluster(pat.sample_texts)
            pat.category = category
            pat.label = _infer_label(pat)
        else:
            pat.category = None
            pat.label = _infer_label(pat)

    if not api_available:
        logger.info(
            "LLM classification skipped (no ANTHROPIC_API_KEY). "
            "Showing all clusters — set key for better filtering."
        )
        return patterns

    # Filter out one-off tasks — not actionable
    filtered = [p for p in patterns if p.category != "one-off-task"]
    removed = len(patterns) - len(filtered)
    if removed:
        logger.info("Filtered %d one-off-task clusters.", removed)
    return filtered


def _infer_label(pat: "Pattern") -> str:
    """Infer a short label from the pattern's representative text."""
    text = pat.representative_text or (pat.sample_texts[0] if pat.sample_texts else "")
    if not text:
        return "Unknown pattern"
    label = text.split("\n")[0][:80].strip()
    return label or "Unknown pattern"


def _check_api() -> bool:
    """Return True if the Anthropic API is likely accessible."""
    import os
    return bool(os.environ.get("ANTHROPIC_API_KEY"))
