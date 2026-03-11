# AI-HABITS

CLI tool that analyzes how you use AI coding assistants and tells you what you're doing wrong. Scans conversation history, audits your existing config, and generates actionable fixes — skills, CLAUDE.md improvements, workflow scripts.

Think ESLint but for your AI assistant usage.

## Project Philosophy

- **Conversation analysis is the core.** The differentiator is understanding how someone *actually* uses their AI assistant and surfacing gaps. Claude Code's `/init` already generates CLAUDE.md from project structure. We don't duplicate that. We analyze *behavior*.
- **Never auto-apply.** All generated configs are drafts for review. Always explain what each suggestion does and why.
- **One platform deep before going wide.** Claude Code is the primary target. Adapter pattern exists in code but do NOT build other adapters yet.
- **Discovery over optimization.** Frame suggestions as "unlock features you didn't know existed" not "you wasted X minutes."
- **Show don't tell.** Every suggestion includes concrete evidence from their own conversations. "You re-explained your auth setup 8 times — here are the dates" hits differently than "consider adding context to your CLAUDE.md."

## Tech Stack

- Python 3.11+
- Click (CLI framework)
- sentence-transformers (local embedding for prompt clustering, `all-MiniLM-L6-v2`)
- Anthropic SDK (for LLM-powered classification and generation passes)
- Rich (terminal output formatting)
- PyPI distribution via `pyproject.toml`

## Project Structure

```
ai-habits/
├── pyproject.toml
├── README.md
├── src/
│   └── ai_habits/
│       ├── __init__.py
│       ├── cli.py                  # Click CLI entry point
│       ├── config.py               # User config, thresholds, defaults
│       │
│       ├── scanners/               # Conversation history parsing
│       │   ├── __init__.py
│       │   ├── base.py             # Abstract adapter interface
│       │   └── claude_code.py      # Parse Claude Code local logs (~/.claude/)
│       │
│       ├── auditors/               # Audit existing config against actual usage
│       │   ├── __init__.py
│       │   ├── claude_md_auditor.py  # Is CLAUDE.md stale? Missing key context that keeps getting re-explained?
│       │   ├── feature_auditor.py    # What features exist that the user never touches?
│       │   └── skill_auditor.py      # Are there skills that should exist based on usage?
│       │
│       ├── patterns/               # Pattern detection engine
│       │   ├── __init__.py
│       │   ├── clustering.py       # Embed + cluster user messages
│       │   ├── classifier.py       # LLM pass: repeatable workflow vs one-off task
│       │   └── anti_patterns.py    # Pre-built common anti-pattern catalog
│       │
│       ├── generators/             # Output generators
│       │   ├── __init__.py
│       │   ├── claude_md_patch.py  # Generate additions/edits to existing CLAUDE.md
│       │   ├── skill_generator.py  # Generate SKILL.md files from repeated patterns
│       │   ├── script_generator.py # Generate shell scripts for repeated workflows
│       │   └── report.py           # Terminal report with suggestions
│       │
│       └── utils/
│           ├── __init__.py
│           ├── embeddings.py       # Sentence-transformer wrapper
│           └── llm.py              # Anthropic API wrapper for classification/generation
│
└── tests/
    ├── test_scanner.py
    ├── test_clustering.py
    ├── test_auditor.py
    └── fixtures/                   # Sample conversation logs and project dirs
```

## CLI Commands

### `ai-habits scan` (core command)

Parses Claude Code conversation history. Finds patterns.

```bash
ai-habits scan [--last 30d] [--min-occurrences 3] [--project ./my-project]

📊 Scanned 47 conversations (last 30 days)

🔁 REPEATED PATTERNS (3 found)
  1. "Set up FastAPI with auth + Docker" — 7 occurrences
     │ Type: boilerplate/scaffolding
     │ Dates: Jan 3, Jan 8, Jan 14, Jan 20, Feb 1, Feb 9, Feb 15
     └─ 💡 This is a skill candidate → ai-habits generate skill --id pat-001

  2. Tech stack re-explained — 12 out of 47 conversations
     │ Type: context re-explanation
     │ You keep telling Claude: Python 3.11, FastAPI, Postgres, Redis, deployed on GCP
     └─ 💡 Add to CLAUDE.md → ai-habits generate patch --id pat-002

  3. "lint then test then commit" — 9 occurrences
     │ Type: sequential workflow
     └─ 💡 Shell script or slash command → ai-habits generate script --id pat-003
```

### `ai-habits audit`

Compares your existing CLAUDE.md against your actual conversation behavior.

```bash
ai-habits audit [--project ./my-project]

📋 CLAUDE.md Audit for ./my-project

⚠️  STALE: CLAUDE.md says "Python 3.10" but recent conversations reference 3.12
⚠️  MISSING: You explain your testing approach in 60% of conversations — not in CLAUDE.md
⚠️  MISSING: You mention "use pytest not unittest" repeatedly — not in CLAUDE.md
✅ COVERED: Project structure is well documented
✅ COVERED: API conventions are documented

💡 Run `ai-habits generate patch` to create a CLAUDE.md update
```

If no CLAUDE.md exists:

```bash
⛔ No CLAUDE.md found. Run `claude /init` to create one, then use `ai-habits audit` to improve it.
```

### `ai-habits discover`

Shows Claude Code features the user isn't leveraging, based on their usage patterns.

```bash
ai-habits discover

🔍 Based on your usage patterns:

📂 SKILLS — You don't have any custom skills
   You have 3 repeated patterns that would work as skills.
   Learn more: https://docs.anthropic.com/...

⚡ SLASH COMMANDS — You've never used custom slash commands
   Your "lint → test → commit" workflow is a perfect candidate.

📝 CLAUDE.md — Exists but hasn't been updated in 45 days
   Your stack has evolved. Run `ai-habits audit` to see gaps.

🔧 MCP SERVERS — You're not using any
   Based on your conversations, you frequently reference GitHub issues.
   The GitHub MCP server could save you context-switching.
```

### `ai-habits generate`

Creates draft artifacts from detected patterns.

```bash
# Patch existing CLAUDE.md with missing context
ai-habits generate patch [--id pat-002]
# Output: CLAUDE.md.patch with additions + comments explaining each

# Create a skill from a repeated pattern
ai-habits generate skill --id pat-001
# Output: ./skills/fastapi-scaffold/SKILL.md (draft)

# Create a shell script from a workflow pattern
ai-habits generate script --id pat-003
# Output: ./scripts/lint-test-commit.sh (draft)
```

### `ai-habits explain`

Dry-run: shows how a generated artifact would have helped in past conversations.

```bash
ai-habits explain --id pat-001

🔍 Pattern: "Set up FastAPI with auth + Docker" (7 occurrences)

If this skill existed, here's what would have changed:
  • Jan 3: You spent ~12 messages describing the setup. Skill would have done it in 1.
  • Jan 14: You forgot to include Redis this time. Skill includes it every time.
  • Feb 9: You asked Claude to "do it the same way as last time" — Claude didn't remember. Skill solves this.
```

## Build Milestones

### v0.1 — Scan + Report (SHIP THIS FIRST)
Priority: Get conversation data flowing and show useful output.

- **Research Claude Code log format.** This is step zero. Run `find ~/.claude -type f`, understand the schema. If it's undocumented, reverse-engineer it. If it's inaccessible, pivot to manual import (`ai-habits import conversation.json`).
- `claude_code.py` scanner: parse conversation logs, extract user messages with timestamps and project context
- `clustering.py`: embed user messages with sentence-transformers, cluster with DBSCAN
- `classifier.py`: LLM pass on each cluster — classify as: repeatable-workflow | boilerplate-request | context-re-explanation | one-off-task. One-off-tasks are filtered out.
- `report.py`: Rich-formatted terminal output ranking top patterns
- `ai-habits scan` command working end to end
- Ship to PyPI as `ai-habits`

### v0.2 — Audit + Discover
- `claude_md_auditor.py`: parse existing CLAUDE.md, compare statements against conversation content, flag stale/missing entries
- `feature_auditor.py`: check for skills directory, custom slash commands, MCP config, CLAUDE.md presence
- `anti_patterns.py`: catalog of common mistakes (no CLAUDE.md, no skills, overly verbose prompts, re-explaining context)
- `ai-habits audit` and `ai-habits discover` commands

### v0.3 — Generators
- `claude_md_patch.py`: generate additions to existing CLAUDE.md from conversation analysis
- `skill_generator.py`: take a repeatable-workflow cluster, use LLM to synthesize into a SKILL.md draft
- `script_generator.py`: take a sequential-workflow cluster, generate shell script
- `ai-habits generate` command (patch, skill, script subcommands)
- `ai-habits explain` dry-run command

### v0.4+ — Expansion (only after validation)
- Cursor adapter (parse conversation logs → audit .cursorrules)
- Aider adapter (parse .aider.chat.history.md)
- Cross-platform view: "across your AI tools, here's the full picture"
- Community anti-pattern library (public repo, community-contributed)
- VS Code extension wrapper
- Team mode: aggregate patterns across a dev team's usage

## Key Design Decisions

1. **We do NOT generate CLAUDE.md from scratch.** Claude's `/init` does that. We audit, patch, and improve existing ones. If no CLAUDE.md exists, we tell the user to run `/init` first, then come back to us.

2. **Embedding model runs locally.** Do not call an API for embeddings. Use sentence-transformers so the tool works offline and doesn't cost money per scan. The LLM classification pass (Anthropic API) is the only network call and it's optional — without an API key, skip classification and show raw clusters with a note that results would be better with an API key.

3. **Conversation log parsing must fail gracefully.** If log format changes or logs don't exist, say so clearly and suggest manual import. Never crash on missing/malformed logs.

4. **Generated files always include comments.** Every section of a generated patch or SKILL.md should have a comment explaining why it was suggested and what evidence triggered it. The user should learn from the draft.

5. **Thresholds are configurable.** Min occurrences for pattern detection (default: 3), similarity threshold for clustering (default: 0.75), lookback window (default: 30d). Sensible defaults but tunable via `~/.ai-habits/config.yaml`.

6. **No telemetry, no data leaves the machine** (except optional Anthropic API calls for classification). This is a local-first tool. Users are trusting it with their conversation history. Make this a prominent selling point.

7. **Pattern IDs are stable.** When a scan produces patterns (pat-001, pat-002...), those IDs should be deterministic for the same input so that `generate` and `explain` commands work reliably after a scan without re-running it. Store scan results in `~/.ai-habits/last_scan.json`.

## Claude Code Log Location (MUST RESEARCH FIRST)

This is the highest-risk unknown. Before writing any scanner code:

1. Run `find ~/.claude -type f` and `ls -laR ~/.claude/` to map the file structure
2. Check for JSONL, SQLite, JSON files containing conversation data
3. Look for per-project vs global conversation storage
4. Check Claude Code docs and GitHub issues for any documented format
5. Check if conversations are stored per-project in `.claude/` within project directories

If conversation logs are not locally accessible or are encrypted:
- Pivot to manual import: user exports conversations and feeds them in
- Or build as a Claude Code extension/plugin that has proper API access
- Document this as a known limitation honestly

## Testing Approach

- Unit tests for scanner: use fixture conversation logs (mock the Claude Code format)
- Unit tests for clustering: use pre-computed embeddings, don't run sentence-transformers model in CI
- Unit tests for auditor: fixture CLAUDE.md files + conversation logs, verify correct stale/missing detection
- Integration test: run full `ai-habits scan` on fixture data, verify report output
- Keep fixtures small and committed to repo
- No tests that require Anthropic API key (mock the LLM calls)

## Code Style

- Type hints everywhere
- Docstrings on public functions
- Use `pathlib.Path` not string paths
- Errors are logged clearly with suggestions for the user, never raw tracebacks
- Keep dependencies minimal — don't add a dep unless it saves 100+ lines
- Use `logging` module, not print statements (except for CLI output via Rich)