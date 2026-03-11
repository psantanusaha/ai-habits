# Contributing to ai-habits

## Setup

```bash
git clone https://github.com/psantanusaha/ai-habits
cd ai-habits
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest tests/ -v
```

Tests don't require an Anthropic API key or sentence-transformers model — scanner tests use fixture data and clustering tests use pre-computed embeddings.

## Project structure

```
src/ai_habits/
├── cli.py              # Click CLI — add new commands here
├── scanners/           # Conversation log parsers (one per AI tool)
├── patterns/           # Clustering + classification engine
├── auditors/           # Config auditing (v0.2)
├── generators/         # Output generators (skills, patches, scripts)
└── utils/              # Embeddings + LLM wrappers
```

## Adding a new scanner (e.g. Cursor)

1. Create `src/ai_habits/scanners/cursor.py`
2. Subclass `BaseScanner` from `scanners/base.py`
3. Implement `iter_sessions()` — yield `Session` objects
4. Document the log format at the top of the file (see `claude_code.py` as reference)
5. Add tests in `tests/test_scanner_cursor.py` using fixture JSONL files

## Adding anti-patterns

Edit `patterns/anti_patterns.py` — add a tuple to `_RULES`:

```python
(
    "name",
    "Description of the problem",
    "Suggestion for fixing it",
    r"(?i)regex that matches the pattern",
),
```

## Pull requests

- Keep PRs focused — one feature or fix per PR
- Add tests for new scanner adapters
- Don't add dependencies without discussion — the install footprint is already heavy (PyTorch via sentence-transformers)
- Generated files (`*.draft`, `*.patch`) should never be committed

## Roadmap

See build milestones in [CLAUDE.md](CLAUDE.md).
