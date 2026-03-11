"""User-configurable thresholds and defaults."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Clustering
    min_cluster_size: int = 3          # min occurrences to flag a pattern
    similarity_threshold: float = 0.75  # cosine similarity for DBSCAN

    # LLM
    anthropic_model: str = "claude-haiku-4-5-20251001"
    llm_enabled: bool = True            # set False to skip Anthropic API calls

    # Output
    output_dir: Path = field(default_factory=Path.cwd)
    draft_suffix: str = ".draft"

    # Scanner
    claude_log_dir: Path = field(default_factory=lambda: Path.home() / ".claude" / "projects")
    ai_habits_dir: Path = field(default_factory=lambda: Path.home() / ".ai-habits")

    # Scan defaults
    default_lookback_days: int = 30


DEFAULT_CONFIG = Config()
