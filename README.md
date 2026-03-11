# ai-habits

**Stop the token bleed.**

Every project that lacks the Claude Code essentials — a `CLAUDE.md`, skills, MCP servers — leaks tokens on every conversation. You re-explain context Claude should already know. You ask for the same boilerplate Claude already generated last week. You copy-paste things into the chat that a tool could fetch automatically.

This is token bleed. It's quiet, it compounds, and most developers don't know it's happening.

`ai-habits` scans your conversation history, finds where you're bleeding, and generates the fixes — without you having to read the docs, take an Anthropic course, or figure out what "setting up an effective Claude Code environment" even means.

---

## The essentials you're probably missing

Claude Code has three features that eliminate token bleed almost entirely. Most developers don't use any of them.

### `CLAUDE.md` — persistent context, loaded every session

Without it, Claude starts every conversation knowing nothing about your project. So you explain it. Every time.

> *"This is a FastAPI project, Python 3.11, Postgres on GCP, JWT auth..."*

That's ~80 tokens per session. Across 12 sessions last month, that's 960 tokens of context Claude processed and forgot. With a `CLAUDE.md`, that context loads once, structured, at the start of every session. Zero re-explanation tokens.

`CLAUDE.md` also carries your conventions — "use pytest not unittest", "no `any` in TypeScript", "always use `pathlib.Path`". Without it, Claude gets these wrong and you correct it. Every correction is a round-trip: your tokens, Claude's tokens, back and forth, every session.

### Skills — reusable prompts, one command

Without skills, repeated tasks cost full tokens every time.

That Docker + FastAPI scaffold you keep asking for? Each generation runs ~800 output tokens. Asked 7 times this month: ~5,600 tokens, slightly different output each time because Claude doesn't remember your conventions.

A skill generates it identically in one invocation. No re-explanation. No variation. No cost beyond the first time you set it up.

### MCP servers — tools that fetch context so you don't have to

Without them, you copy-paste. GitHub issues into the chat. Database query results. Documentation snippets. Every paste is tokens — input tokens Claude uses to read what a tool could have fetched directly and more efficiently.

The GitHub MCP server, for example, lets Claude read issues, PRs, and comments directly. No paste. No truncation. No tokens wasted on formatting.

---

## What ai-habits does

It reads your Claude Code conversation history, finds your specific gaps, and tells you exactly what to fix.

```
$ ai-habits scan

┌─────────────────────────────────────────────┐
│ ai-habits scan  last 30 days                │
└─────────────────────────────────────────────┘
Scanned 47 conversations, 531 user messages

🔁 REPEATED PATTERNS

  1. "Set up FastAPI with auth + Docker" — 7 occurrences
     │ Type: 📋 boilerplate-request
     │ Dates: Jan 3, Jan 9, Jan 14, Jan 21, Feb 1, Feb 8 +1 more
     │ Est. token waste: ~4,900 input + ~5,600 output tokens
     └─ 💡 Skill candidate → ai-habits generate skill --id pat-001

  2. "This is a Python 3.11 FastAPI project on GCP..." — 12 occurrences
     │ Type: 🔄 context-re-explanation
     │ Dates: Dec 28, Jan 2, Jan 6, Jan 11, Jan 15, Jan 19 +6 more
     │ Est. token waste: ~960 input tokens
     └─ 💡 Add to CLAUDE.md → ai-habits generate patch --id pat-002

  3. "run lint then tests then commit" — 9 occurrences
     │ Type: 🔁 repeatable-workflow
     │ Est. token waste: ~630 input + ~3,600 output tokens
     └─ 💡 Skill candidate → ai-habits generate skill --id pat-003

⚠️  ANTI-PATTERNS
  auth-setup-repeat (16 occurrences)
  You repeatedly describe your authentication setup to Claude.
  💡 Your auth architecture should be in CLAUDE.md, not your chat history.
```

> Pattern types (`boilerplate-request`, `context-re-explanation`, etc.) are detected locally using the same embedding model used for clustering — no API key required. Setting `ANTHROPIC_API_KEY` runs an additional LLM pass for higher accuracy.

```
$ ai-habits discover

┌──────────────────────────────┐
│ ai-habits discover           │
└──────────────────────────────┘
Project: /path/to/my-project

✗ CLAUDE.md
  Without CLAUDE.md, Claude has no persistent context about your project.
  You'll keep re-explaining the same things every session.
  → Run `claude /init` to generate a starter CLAUDE.md, then use `ai-habits audit` to improve it.

✗ Skills
  You have 5 repeated patterns that would work as skills (pat-001, pat-002, pat-003 +2 more).
  Skills let you invoke complex recurring tasks in one command.
  → Run `ai-habits generate skill --id pat-001` to create a draft from your top pattern.

✗ MCP Servers
  Based on your conversation history, you're manually providing context that MCP servers
  could fetch automatically — saving tokens every session.
    • You reference GitHub content repeatedly — GitHub MCP lets Claude read issues/PRs directly
  → Add the relevant servers to ~/.claude/settings.json under 'mcpServers'.
  Browse available servers: https://github.com/modelcontextprotocol/servers
```

Then it generates the fixes:

```bash
# Create a skill from a repeated pattern
ai-habits generate skill --id pat-001
# → .claude/skills/fastapi-scaffold/SKILL.md (draft, commented)

# Patch your CLAUDE.md with missing context
ai-habits generate patch --id pat-002
# → CLAUDE.md.patch (append to your existing file — never replaces it)

# Turn a workflow into a script
ai-habits generate script --id pat-003
# → scripts/lint-test-commit.sh
```

Everything generated is a **draft with inline comments** explaining what evidence triggered it. Nothing is auto-applied.

---

## No courses required

Setting up an effective Claude Code environment is documented — in Anthropic's docs, in blog posts, in YouTube videos. Most developers never get to it because it feels like a project, not a quick fix.

`ai-habits` skips the learning curve. It reads *your* conversations, finds *your* specific gaps, and generates *your* specific fixes. You don't need to know what a skill is before you make one. You don't need to understand the CLAUDE.md format before you patch yours. The generated files are explained line by line.

---

## Install

```bash
pip install ai-habits        # works immediately, uses TF-IDF clustering
pip install 'ai-habits[ml]'  # adds neural embeddings for better accuracy (~500MB)
```

**Requirements:** Python 3.11+, Claude Code with existing conversation history (`~/.claude/projects/`)

> The base install uses TF-IDF (scikit-learn) for clustering — no PyTorch, no large downloads. The `[ml]` extra adds `sentence-transformers` with the `all-MiniLM-L6-v2` model for better semantic clustering. All processing stays on your machine.

---

## Quick start

```bash
# Find your token bleed
ai-habits scan

# Scope to one project
ai-habits scan --project /path/to/my-project

# See which essentials are missing
ai-habits discover

# Check if your CLAUDE.md matches how you actually work
ai-habits audit
```

---

## Commands

### `ai-habits scan`
```bash
ai-habits scan [--last 30d] [--min-occurrences 3] [--project PATH] [--no-llm]
```
Parses `~/.claude/projects/` logs, clusters similar messages, classifies patterns. Results saved to `~/.ai-habits/last_scan.json`.

| Flag | Default | Description |
|---|---|---|
| `--last` | `30d` | Lookback window |
| `--min-occurrences` | `3` | Min messages to form a pattern |
| `--project` | all projects | Filter to one project |
| `--no-llm` | off | Skip Anthropic classification, show all clusters |

### `ai-habits discover`
```bash
ai-habits discover [PROJECT_DIR]
```
Checks for missing Claude Code essentials (CLAUDE.md, skills, MCP servers) and cross-references your last scan to make it concrete: *"You have 5 patterns that would work as skills."*

### `ai-habits audit`
```bash
ai-habits audit [PROJECT_DIR]
```
Compares your CLAUDE.md against actual conversation behavior. Flags stale entries (contradicted by recent conversations) and missing entries (context you keep re-explaining). Requires CLAUDE.md — run `claude /init` first.

### `ai-habits generate`
```bash
ai-habits generate skill --id pat-001    # → .claude/skills/<name>/SKILL.md
ai-habits generate patch [--id pat-002]  # → CLAUDE.md.patch
ai-habits generate script --id pat-003  # → scripts/<name>.sh
```
Generates draft artifacts from your detected patterns. Every file includes inline comments explaining what evidence triggered the suggestion.

### `ai-habits explain`
```bash
ai-habits explain --id pat-001
```
Shows the conversations where a pattern appeared and what would have been different with the fix in place.

---

## LLM classification (optional)

Pattern classification works out of the box using the same local embedding model (`all-MiniLM-L6-v2`) already used for clustering. No API key, no internet, no extra downloads.

Setting `ANTHROPIC_API_KEY` runs an additional Claude Haiku pass after the local classifier for higher accuracy and better noise filtering:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
ai-habits scan
```

A 30-day scan costs a few cents. Uses `claude-haiku` only.

---

## How it works

1. **Scan** — reads `~/.claude/projects/*/` JSONL files (Claude Code's local log format)
2. **Embed** — encodes each user message with `all-MiniLM-L6-v2`, locally and offline
3. **Cluster** — groups similar messages with DBSCAN
4. **Classify** — optional LLM pass labels each cluster: `repeatable-workflow`, `boilerplate-request`, `context-re-explanation`, or `one-off-task`
5. **Report** — ranks by frequency, surfaces anti-patterns, links to the right fix

---

## Privacy

- All conversation data stays on your machine
- Embeddings computed locally — no API call for this step
- The only outbound request is the optional Anthropic classification pass
- Scan results stored in `~/.ai-habits/last_scan.json`

No telemetry. No tracking. This tool reads your most sensitive work data — that trust is taken seriously.

---

## Supported platforms

| Platform | Status |
|---|---|
| Claude Code | ✅ Supported |
| Cursor | Planned |
| Aider | Planned |
| GitHub Copilot | Planned |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
