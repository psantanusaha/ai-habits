"""Sentence-transformer wrapper for local, offline embedding.

Model: all-MiniLM-L6-v2 (22M params, 384-dim, fast and good for clustering).
We never call an external API for embeddings.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _load_model() -> "SentenceTransformer":
    """Load model once and cache it for the process lifetime."""
    try:
        import contextlib
        import io
        import transformers
        from sentence_transformers import SentenceTransformer

        transformers.logging.set_verbosity_error()  # suppress BertModel LOAD REPORT
        logger.debug("Loading sentence-transformer model: %s", MODEL_NAME)

        # safetensors prints a "Loading weights" progress bar to stderr — suppress it
        with contextlib.redirect_stderr(io.StringIO()):
            return SentenceTransformer(MODEL_NAME)
    except ImportError as e:
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Run: pip install sentence-transformers"
        ) from e


def embed(texts: list[str], batch_size: int = 64) -> np.ndarray:
    """Embed a list of strings into a 2D float32 array of shape (N, 384).

    Args:
        texts: List of strings to embed.
        batch_size: Number of sentences to embed in one forward pass.

    Returns:
        numpy array of shape (len(texts), 384).
    """
    if not texts:
        return np.empty((0, 384), dtype=np.float32)

    model = _load_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 200,
        convert_to_numpy=True,
        normalize_embeddings=True,  # cosine similarity = dot product
    )
    return embeddings.astype(np.float32)
