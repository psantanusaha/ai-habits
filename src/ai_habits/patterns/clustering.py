"""Embed + cluster user messages using DBSCAN.

Produces stable pattern IDs derived from the cluster centroid so that
`ai-habits generate --id pat-001` works reliably across runs on the same data.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from ai_habits.scanners.base import Message

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """A detected cluster of similar user messages."""

    id: str                          # stable ID, e.g. "pat-001"
    messages: list[Message]
    centroid: np.ndarray             # mean embedding of the cluster
    category: str | None = None      # set by classifier pass
    label: str | None = None         # short human-readable label
    representative_text: str = ""    # message closest to centroid (best label candidate)

    @property
    def size(self) -> int:
        return len(self.messages)

    @property
    def sample_texts(self) -> list[str]:
        """Up to 5 message texts, representative one first."""
        texts: list[str] = []
        if self.representative_text:
            texts.append(self.representative_text)
        for m in self.messages:
            if m.text != self.representative_text and len(texts) < 5:
                texts.append(m.text)
        return texts

    @property
    def dates(self) -> list[datetime]:
        return sorted(m.timestamp for m in self.messages)

    @property
    def first_seen(self) -> datetime | None:
        d = self.dates
        return d[0] if d else None

    @property
    def last_seen(self) -> datetime | None:
        d = self.dates
        return d[-1] if d else None


def cluster(
    messages: list[Message],
    similarity_threshold: float = 0.75,
    min_cluster_size: int = 3,
) -> list[Pattern]:
    """Embed *messages* and return DBSCAN clusters as :class:`Pattern` objects.

    Args:
        messages: User messages to cluster.
        similarity_threshold: Cosine similarity cutoff (0–1). Higher = tighter clusters.
        min_cluster_size: Minimum messages to form a pattern. Smaller clusters are noise.

    Returns:
        List of patterns, sorted by size descending.
        Noise points (cluster label -1) are excluded.
    """
    if not messages:
        return []

    texts = [m.text for m in messages]

    # Import here so the module is importable even if sentence-transformers is absent
    from ai_habits.utils.embeddings import embed
    from sklearn.cluster import DBSCAN

    logger.info("Embedding %d messages...", len(texts))
    embeddings = embed(texts)  # shape (N, 384), L2-normalized

    # DBSCAN with cosine metric.
    # eps = 1 - similarity_threshold (since embeddings are normalized, euclidean ≈ cosine).
    # For normalized vectors: ||a - b||² = 2(1 - cos(a,b)), so dist = sqrt(2*(1-sim)).
    eps = float(np.sqrt(2 * (1.0 - similarity_threshold)))
    db = DBSCAN(eps=eps, min_samples=min_cluster_size, metric="euclidean", n_jobs=-1)
    labels = db.fit_predict(embeddings)

    unique_labels = set(labels) - {-1}
    if not unique_labels:
        logger.info("No patterns found (all messages classified as noise).")
        return []

    patterns: list[Pattern] = []
    for label_id in sorted(unique_labels):
        mask = labels == label_id
        cluster_msgs = [m for m, keep in zip(messages, mask) if keep]
        cluster_embeddings = embeddings[mask]
        centroid = cluster_embeddings.mean(axis=0)
        representative = _pick_representative(cluster_msgs, cluster_embeddings, centroid)
        pat_id = _stable_id(centroid, len(patterns) + 1)
        patterns.append(
            Pattern(
                id=pat_id,
                messages=cluster_msgs,
                centroid=centroid,
                representative_text=representative,
            )
        )

    # Sort by frequency descending
    patterns.sort(key=lambda p: p.size, reverse=True)

    # Re-assign sequential IDs after sorting so pat-001 is always the biggest
    for i, pat in enumerate(patterns):
        pat.id = f"pat-{i + 1:03d}"

    logger.info("Found %d patterns.", len(patterns))
    return patterns


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick_representative(
    msgs: list[Message],
    embeddings: np.ndarray,
    centroid: np.ndarray,
) -> str:
    """Return the text of the message closest to *centroid* that is also
    meaningful (long enough, not a system artifact).

    Falls back to the closest message regardless if none pass the quality bar.
    """
    _NOISE_PREFIXES = (
        "[request interrupted", "<local-command", "<task-notification",
        "this session is being continued", "conversation so far:",
        "base directory for this skill",
    )
    _MIN_LEN = 12  # skip very short messages like "yes", "done", "hi"

    # Cosine distance to centroid (embeddings are already L2-normalized)
    dists = np.linalg.norm(embeddings - centroid, axis=1)
    order = np.argsort(dists)  # closest first

    # Try to find a meaningful message
    for idx in order:
        text = msgs[idx].text.strip()
        if len(text) < _MIN_LEN:
            continue
        if any(text.lower().startswith(p) for p in _NOISE_PREFIXES):
            continue
        # Truncate at first newline
        return text.split("\n")[0][:100].strip()

    # Fallback: just take the closest regardless
    closest = msgs[order[0]].text.strip()
    return closest.split("\n")[0][:100].strip()


def _stable_id(centroid: np.ndarray, fallback_index: int) -> str:
    """Generate a short stable ID from the centroid vector."""
    digest = hashlib.md5(centroid.tobytes()).hexdigest()[:8]
    return f"pat-{fallback_index:03d}-{digest}"
