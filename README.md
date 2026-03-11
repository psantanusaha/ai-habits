# ai-habits

**ESLint for your AI assistant usage.**

`ai-habits` scans your Claude Code conversation history, finds patterns in how you use AI, and tells you what to fix — generate skills, patch your CLAUDE.md, or create workflow scripts.

```
📊 Scanned 47 conversations (last 30 days)

🔁 REPEATED PATTERNS

  1. "Set up FastAPI with auth + Docker" — 7 occurrences
     │ Type: boilerplate-request
     │ Dates: Jan 3, Jan 8, Jan 14, Jan 20, Feb 1, Feb 9, Feb 15
     └─ 💡 Skill candidate → ai-habits generate skill --id pat-001

  2. Tech stack re-explained — 12 out of 47 conversations
     │ Type: context-re-explanation
     └─ 💡 Add to CLAUDE.md → ai-habits generate patch --id pat-002

  3. "lint then test then commit" — 9 occurrences
     │ Type: repeatable-workflow
     └─ 💡 Shell script → ai-habits generate script --id pat-003

⚠️  ANTI-PATTERNS
  You frequently describe your auth setup to Claude. (16 occurrences)
  💡 Document your auth architecture in CLAUDE.md
```

## Why

Claude Code's `/init` generates a CLAUDE.md from your project files. That's a good start. But it doesn't know how you *actually* use Claude day-to-day:

- The context you re-explain in 60% of conversations
- The boilerplate you've asked for 8 times this month
- The workflow you keep typing out step by step

`ai-habits` reads your conversation history, surfaces these patterns, and generates the fixes — skills, CLAUDE.md additions, shell scripts.

## Installation

```bash
pip install ai-habits
```

> **Note:** `ai-habits` uses [sentence-transformers](https://www.sbert.net/) for local embedding, which pulls in PyTorch (~500MB on first run). Everything runs locally — no data leaves your machine except optional Anthropic API calls for classification.

## Quick start

```bash
# Scan your last 30 days of Claude Code conversations
ai-habits scan

# Scan a specific project
ai-habits scan --project /path/to/my-project

# See what Claude Code features you're not using
ai-habits discover

# Check if your CLAUDE.md matches how you actually work
ai-habits audit
```

## Commands

### `ai-habits scan`

Parses Claude Code logs, clusters similar messages, classifies patterns.

```bash
ai-habits scan [--last 30d] [--min-occurrences 3] [--project PATH] [--no-llm]
```

Options:
- `--last` — lookback window (default: `30d`)
- `--min-occurrences` — minimum messages to form a pattern (default: `3`)
- `--project` — filter to a specific project path
- `--no-llm` — skip Anthropic API classification (faster, shows more noise)

Results are saved to `~/.ai-habits/last_scan.json` for use by `generate` and `explain`.

---

### `ai-habits discover`

Shows Claude Code features you're not using, cross-referenced with your scan results.

```bash
ai-habits discover [PROJECT_DIR]
```

Example output:
```
✓ CLAUDE.md
✗ Skills
  You have 5 repeated patterns that would work as skills (pat-002, pat-004, pat-005).
  → Run `ai-habits generate skill --id pat-002` to create a draft.
✗ MCP Servers
  Based on your conversations, you frequently reference GitHub issues.
  → Add the GitHub MCP server to save context-switching.
```

---

### `ai-habits audit`

Compares your existing CLAUDE.md against actual conversation behavior.

```bash
ai-habits audit [PROJECT_DIR]
```

Requires CLAUDE.md to exist — run `claude /init` first if needed.

---

### `ai-habits generate`

Creates draft artifacts from detected patterns.

```bash
ai-habits generate skill --id pat-001    # → .claude/skills/<name>/SKILL.md
ai-habits generate patch [--id pat-002]  # → CLAUDE.md.patch
ai-habits generate script --id pat-003  # → scripts/<name>.sh
```

All generated files are **drafts** — never auto-applied. Every section includes a comment explaining what evidence triggered it.

---

### `ai-habits explain`

Dry-run: shows how a generated artifact would have helped in past conversations.

```bash
ai-habits explain --id pat-001
```

---

## How it works

1. **Scan** — reads `~/.claude/projects/*/` JSONL files (Claude Code's local log format)
2. **Embed** — encodes each user message using `all-MiniLM-L6-v2` (runs locally, offline)
3. **Cluster** — groups similar messages with DBSCAN
4. **Classify** — optional LLM pass (Anthropic API) labels each cluster: `repeatable-workflow`, `boilerplate-request`, `context-re-explanation`, or `one-off-task`
5. **Report** — ranks patterns by frequency, surfaces anti-patterns, suggests actions

Without an API key, classification is skipped and all clusters are shown. With a key, one-off tasks are filtered and clusters get meaningful labels.

## LLM classification (optional)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
ai-habits scan   # now classifies and filters clusters
```

Uses `claude-haiku` — cheap, fast. A 30-day scan costs a few cents.

## Privacy

- All conversation data stays on your machine
- Embeddings are computed locally using sentence-transformers
- The only outbound call is the optional Anthropic classification pass
- Scan results are stored in `~/.ai-habits/last_scan.json`

## Supported platforms

Currently supports **Claude Code** (`~/.claude/projects/`).

Planned: Cursor, Aider, GitHub Copilot.

## Configuration

Thresholds can be tuned via `~/.ai-habits/config.yaml` (coming in v0.2):

```yaml
min_cluster_size: 3       # min messages to form a pattern
similarity_threshold: 0.75 # cosine similarity for clustering
default_lookback_days: 30
```

## Requirements

- Python 3.11+
- Claude Code installed and used (logs exist at `~/.claude/projects/`)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
