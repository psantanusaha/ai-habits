"""Anthropic API wrapper for classification and generation passes.

This is the ONLY module that makes network calls. It degrades gracefully:
if no API key is available, callers receive None and should handle accordingly.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"  # cheap + fast for classification


def classify_cluster(
    messages: list[str],
    model: str = _DEFAULT_MODEL,
) -> Optional[str]:
    """Classify a cluster of messages into one of four categories.

    Categories:
        repeatable-workflow     — A multi-step task the user does regularly
        boilerplate-request     — A request to generate recurring scaffolding
        context-re-explanation  — User keeps re-explaining the same context
        one-off-task            — Unique, non-recurring task (not interesting)

    Returns:
        The category string, or None if API is unavailable or call fails.
    """
    client = _get_client()
    if client is None:
        return None

    sample = messages[:10]  # avoid large prompts
    sample_text = "\n---\n".join(f"• {m}" for m in sample)

    prompt = f"""\
You are analyzing patterns in a developer's AI assistant usage.

Here are {len(messages)} similar user messages (sample shown):
{sample_text}

Classify this cluster into exactly one category:
- repeatable-workflow: A multi-step workflow the user runs repeatedly (e.g. "lint, test, commit")
- boilerplate-request: Recurring scaffolding/template requests (e.g. "set up FastAPI with Docker")
- context-re-explanation: User keeps re-explaining the same project context Claude should already know
- one-off-task: Unique, non-recurring task — not useful to optimize

Respond with ONLY the category name, nothing else."""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        category = response.content[0].text.strip().lower()
        valid = {"repeatable-workflow", "boilerplate-request", "context-re-explanation", "one-off-task"}
        if category in valid:
            return category
        logger.debug("Unexpected category from LLM: %r", category)
        return None
    except Exception as e:
        logger.warning("LLM classification failed: %s", e)
        return None


def generate_skill_draft(
    pattern_summary: str,
    sample_messages: list[str],
    model: str = _DEFAULT_MODEL,
) -> Optional[str]:
    """Generate a SKILL.md draft from a pattern cluster.

    Returns:
        Markdown string for the skill file, or None if unavailable.
    """
    client = _get_client()
    if client is None:
        return None

    sample = "\n".join(f"- {m}" for m in sample_messages[:5])
    prompt = f"""\
Generate a Claude Code SKILL.md file for the following recurring pattern.

Pattern: {pattern_summary}

Example user messages that triggered this pattern:
{sample}

A SKILL.md file:
1. Has a concise title
2. Has a description explaining what the skill does
3. Has a "Usage" section showing how to invoke it
4. Has a "Context" section with the key information Claude needs every time
5. Includes inline HTML comments explaining why each section was included

Generate the full SKILL.md content now:"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning("Skill generation failed: %s", e)
        return None


def _get_client():
    """Return an Anthropic client if an API key is available, else None."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.debug(
            "ANTHROPIC_API_KEY not set — skipping LLM classification. "
            "Set the key for better pattern categorization."
        )
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        logger.warning("anthropic package not installed — LLM features disabled.")
        return None
