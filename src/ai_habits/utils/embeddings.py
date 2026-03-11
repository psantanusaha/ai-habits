"""Embedding backends for clustering.

Two backends, selected automatically:

  Neural (default when sentence-transformers is installed)
    Model: all-MiniLM-L6-v2 — 22M params, 384-dim, accurate semantic similarity.
    Install: pip install 'ai-habits[ml]'

  TF-IDF (fallback, zero extra deps beyond sklearn)
    Uses sklearn TfidfVectorizer.  Less accurate on paraphrases but works well
    for clustering messages that share keywords/phrases.
    Vocabulary is built from the corpus being embedded — callers must pass all
    texts in one call so the vectorizer can build a consistent vocabulary.

Public API:
  neural_available() -> bool
  embed(texts)        -> np.ndarray  (neural or TF-IDF depending on availability)
  embed_tfidf(texts)  -> np.ndarray  (always TF-IDF, for callers that need it explicitly)
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
def neural_available() -> bool:
    """Return True if sentence-transformers is installed and loadable."""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _load_model() -> "SentenceTransformer":
    """Load the neural model once and cache it for the process lifetime."""
    import contextlib
    import io
    import transformers
    from sentence_transformers import SentenceTransformer

    transformers.logging.set_verbosity_error()  # suppress BertModel LOAD REPORT
    logger.debug("Loading sentence-transformer model: %s", MODEL_NAME)

    # safetensors prints a "Loading weights" progress bar to stderr — suppress it
    with contextlib.redirect_stderr(io.StringIO()):
        return SentenceTransformer(MODEL_NAME)


def embed(texts: list[str], batch_size: int = 64) -> np.ndarray:
    """Embed texts using the best available backend.

    Returns an L2-normalised float32 array of shape (N, D) where D is 384
    for neural and up to 512 for TF-IDF.  Cosine similarity = dot product.
    """
    if not texts:
        return np.empty((0, 384), dtype=np.float32)

    if neural_available():
        return _embed_neural(texts, batch_size)
    return embed_tfidf(texts)


def _embed_neural(texts: list[str], batch_size: int = 64) -> np.ndarray:
    model = _load_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 200,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.astype(np.float32)


def embed_tfidf(texts: list[str]) -> np.ndarray:
    """Embed texts using TF-IDF + L2 normalisation.

    The vectorizer is fit on *texts* itself — all texts to be compared must
    be passed in a single call so they share the same vocabulary.

    Returns float32 array of shape (N, min(512, vocab_size)).
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    if not texts:
        return np.empty((0, 512), dtype=np.float32)

    vec = TfidfVectorizer(max_features=512, ngram_range=(1, 2), sublinear_tf=True)
    matrix = vec.fit_transform(texts).toarray().astype(np.float32)
    return normalize(matrix, norm="l2")
