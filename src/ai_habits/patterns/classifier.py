"""Pattern classification for clusters.

Two strategies, in order of preference:
1. Local (default) — embed each pattern's representative text and find the
   nearest pre-defined category centroid.  Uses the all-MiniLM-L6-v2 model
   already loaded for clustering, so no new dependencies or downloads.
2. LLM (optional, more accurate) — call Claude Haiku when ANTHROPIC_API_KEY
   is set.  Adds nuance and filters noise more aggressively.

The local strategy works out of the box with no API key, no internet, and
near-zero extra cost.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np

from ai_habits.patterns.clustering import Pattern

logger = logging.getLogger(__name__)

# Category → emoji + description shown in the report
CATEGORY_META: dict[str, tuple[str, str]] = {
    "repeatable-workflow":    ("🔁", "Repeated workflow"),
    "boilerplate-request":    ("📋", "Boilerplate/scaffolding"),
    "context-re-explanation": ("🔄", "Context re-explained"),
    "one-off-task":           ("✨", "One-off task"),
}

# ---------------------------------------------------------------------------
# Few-shot exemplars for local embedding classifier
# ---------------------------------------------------------------------------

_EXEMPLARS: dict[str, list[str]] = {
    "boilerplate-request": [
        "generate a fastapi project with docker setup",
        "create a new react component with tests",
        "scaffold a python package with pyproject.toml and ci",
        "write a dockerfile for my node application",
        "set up a django app with user authentication",
        "create a typescript interface for this json schema",
        "bootstrap a new express api with error handling middleware",
        "generate a github actions workflow for testing and deploying",
    ],
    "repeatable-workflow": [
        "run lint then run tests then commit",
        "pull latest changes, rebase onto main, and push",
        "build the project and deploy to staging",
        "run the database migration and restart the server",
        "format the code, fix lint errors, then open a pr",
        "run tests, generate coverage report, and update badge",
        "tag the release and update the changelog",
        "sync the fork with upstream and resolve conflicts",
    ],
    "context-re-explanation": [
        "this is a python 3.11 project using fastapi and postgres",
        "our stack is react frontend with a django rest api",
        "we use pytest for testing, black for formatting, and ruff for linting",
        "we deploy on aws using terraform and github actions",
        "the codebase uses typescript strict mode and eslint",
        "our database is postgres with sqlalchemy orm",
        "this service runs on kubernetes with helm charts",
        "we follow trunk-based development with feature flags",
    ],
    "one-off-task": [
        "explain what this function does",
        "what does this error message mean",
        "help me understand why this test is failing",
        "what is the difference between these two approaches",
        "can you review this pull request",
        "debug this unexpected behaviour",
        "what are the tradeoffs here",
        "is this the right approach for my use case",
    ],
}

# Minimum cosine similarity to assign a confident category.
# Below this, we leave the category as-is (keeps "one-off-task" or None).
_MIN_CONFIDENCE: float = 0.25


@lru_cache(maxsize=1)
def _category_centroids() -> dict[str, np.ndarray]:
    """Embed exemplars once and return a centroid vector per category.

    Cached for the process lifetime — embeddings are L2-normalised so
    cosine similarity == dot product.
    """
    from ai_habits.utils.embeddings import embed

    centroids: dict[str, np.ndarray] = {}
    for category, exemplars in _EXEMPLARS.items():
        vecs = embed(exemplars)          # shape (N, 384), already normalised
        centroid = vecs.mean(axis=0)
        # Re-normalise the centroid so dot product is still cosine similarity
        norm = np.linalg.norm(centroid)
        centroids[category] = centroid / norm if norm > 0 else centroid
    return centroids


def _classify_locally(text: str) -> str:
    """Return the best-matching category for *text* using embedding similarity.

    Falls back to ``"one-off-task"`` when no category exceeds MIN_CONFIDENCE.
    """
    from ai_habits.utils.embeddings import embed

    vec = embed([text])[0]                       # shape (384,), normalised
    centroids = _category_centroids()

    best_cat, best_sim = "one-off-task", 0.0
    for category, centroid in centroids.items():
        sim = float(np.dot(vec, centroid))
        if sim > best_sim:
            best_sim, best_cat = sim, category

    if best_sim < _MIN_CONFIDENCE:
        return "one-off-task"

    logger.debug("Local classify: '%s...' → %s (sim=%.3f)", text[:40], best_cat, best_sim)
    return best_cat


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify(patterns: list[Pattern]) -> list[Pattern]:
    """Add category + label to each pattern in *patterns*.

    Modifies patterns in-place and returns the list with one-off tasks removed.

    Classification strategy:
    - Always runs the local embedding classifier (no API key required).
    - If ANTHROPIC_API_KEY is set, the LLM pass runs *after* and can
      override/refine the local result for better accuracy.
    """
    from ai_habits.utils import llm

    use_llm = _check_api()

    for pat in patterns:
        text = pat.representative_text or (pat.sample_texts[0] if pat.sample_texts else "")
        if text:
            pat.category = _classify_locally(text)
        else:
            pat.category = "one-off-task"
        pat.label = _infer_label(pat)

    if use_llm:
        for pat in patterns:
            llm_category = llm.classify_cluster(pat.sample_texts)
            if llm_category:
                pat.category = llm_category
                pat.label = _infer_label(pat)
        logger.info("LLM classification pass complete.")
    else:
        logger.info("Using local embedding classifier (set ANTHROPIC_API_KEY for higher accuracy).")

    # Filter out one-off tasks — not actionable
    filtered = [p for p in patterns if p.category != "one-off-task"]
    removed = len(patterns) - len(filtered)
    if removed:
        logger.info("Filtered %d one-off-task clusters.", removed)
    return filtered


def _infer_label(pat: Pattern) -> str:
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
