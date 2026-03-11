"""Groq LLM backend for semantic catalog matching.

Uses llama-3.1-8b-instant — extremely fast and essentially free on Groq's
free tier (14,400 req/day).  Activated automatically when GROQ_API_KEY is set.

Primary use: semantic matching of user conversation patterns against catalogs
(MCP servers, community skills) — understanding *intent* rather than keywords.

Install: pip install 'ai-habits[groq]'
Key:     export GROQ_API_KEY=gsk_...  (free at console.groq.com)
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

MODEL = "llama-3.1-8b-instant"
_MAX_CATALOG_ENTRIES = 40   # keep prompt size small


@lru_cache(maxsize=1)
def groq_available() -> bool:
    """Return True if groq package is installed and GROQ_API_KEY is set."""
    if not os.environ.get("GROQ_API_KEY"):
        return False
    try:
        import groq  # noqa: F401
        return True
    except ImportError:
        return False


def semantic_match(
    patterns: list[str],
    catalog: list[dict],
    context: str,
    top_k: int = 6,
) -> list[str]:
    """Return catalog IDs most relevant to *patterns*, ranked by relevance.

    Args:
        patterns: Representative texts from detected conversation patterns.
        catalog:  List of dicts with at least 'id', 'name', 'description'.
        context:  Human label for the catalog type, e.g. "MCP servers".
        top_k:    Max number of IDs to return.

    Returns:
        List of catalog IDs (subset of catalog), ranked best-first.
        Returns [] if Groq is unavailable or on any error.
    """
    if not groq_available() or not patterns or not catalog:
        return []

    try:
        from groq import Groq
        client = Groq(api_key=os.environ["GROQ_API_KEY"])

        # Summarise catalog — id + name + description only (keep prompt small)
        catalog_lines = "\n".join(
            f"  {e['id']}: {e['name']} — {e.get('description', '')}"
            for e in catalog[:_MAX_CATALOG_ENTRIES]
        )

        pattern_lines = "\n".join(f"  - {p}" for p in patterns[:15])

        prompt = f"""You are analyzing a developer's repeated conversation patterns to suggest relevant tools.

The developer keeps asking Claude about:
{pattern_lines}

Available {context}:
{catalog_lines}

Which {context} would most reduce their manual copy-paste work or repetitive requests?
Only include items where there is clear evidence from the patterns above.
Return a JSON array of IDs only, ranked best-first, at most {top_k} items.
Example: ["github", "postgres", "fetch"]
Return ONLY the JSON array, nothing else."""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )

        raw = response.choices[0].message.content.strip()
        # Parse the JSON array — strip any markdown fences
        raw = raw.strip("`").removeprefix("json").strip()
        ids: list[str] = json.loads(raw)

        # Validate: only return IDs that actually exist in the catalog
        valid_ids = {e["id"] for e in catalog}
        result = [i for i in ids if i in valid_ids]

        logger.debug("Groq semantic match (%s): %s", context, result)
        return result[:top_k]

    except Exception as e:
        logger.debug("Groq matching failed, falling back to keywords: %s", e)
        return []


def enrich_labels(patterns: list[dict]) -> list[dict]:
    """Use Groq to generate concise human-readable labels for patterns.

    Takes the raw representative text (often a fragment) and returns a
    5-10 word label that describes what the pattern *is*, e.g.:
      "can you create a fastapi pro..." → "FastAPI + Docker project scaffold"

    Modifies patterns in-place and returns the list.
    Falls back gracefully — labels stay as representative text if Groq is down.
    """
    if not groq_available() or not patterns:
        return patterns

    try:
        from groq import Groq
        client = Groq(api_key=os.environ["GROQ_API_KEY"])

        # Build a single batched prompt to minimise API calls
        numbered = "\n".join(
            f"{i+1}. {p.get('label') or p.get('representative_text', '')[:100]}"
            for i, p in enumerate(patterns[:12])
        )

        prompt = f"""For each developer conversation pattern below, write a concise 4-8 word label
that describes what the developer is repeatedly asking for.
Be specific and use technical terms (e.g. "FastAPI Docker scaffold", "Git commit and push workflow").

Patterns:
{numbered}

Return a JSON array of strings, one label per pattern, in the same order.
Return ONLY the JSON array."""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.strip("`").removeprefix("json").strip()
        labels: list[str] = json.loads(raw)

        for pat, label in zip(patterns, labels):
            if label and isinstance(label, str):
                pat["label"] = label.strip()

        logger.debug("Groq label enrichment: %d patterns labelled", len(labels))
        return patterns

    except Exception as e:
        logger.debug("Groq label enrichment failed: %s", e)
        return patterns
