# ai-habits

You've been using Claude Code every day. Here's what's actually happening.

---

## You're re-explaining the same context over and over

Claude has no memory between sessions. So every few conversations, you end up typing some version of:

> *"This is a FastAPI project, we use Postgres, deployed on GCP, auth is JWT-based..."*

You've done this **12 times in the last month**. Claude forgot it every time. That context belongs in your `CLAUDE.md` — but nobody told you what to put there.

---

## You're asking for the same boilerplate repeatedly

That Docker + FastAPI scaffold you keep asking for? You've requested it **7 times** since January. Each time, Claude generates it slightly differently. Each time, you correct it to match your conventions. Each time, Claude forgets those corrections.

A skill would do this in one command, consistently, every time. You don't have any skills.

---

## You have a workflow you type out step by step, every time

> *"lint, then run tests, then commit"*

9 times last month. That's a shell script. Or a slash command. It takes 2 minutes to set up and saves you 9 interactions a month — forever.

---

## Your CLAUDE.md is stale (if you have one at all)

Most developers either don't have a `CLAUDE.md`, or wrote one 6 months ago and never touched it again. Meanwhile their stack evolved, their conventions changed, and Claude is still operating on outdated instructions.

---

## `ai-habits` shows you all of this

```
$ ai-habits scan

📊 Scanned 47 conversations (last 30 days)

🔁 REPEATED PATTERNS

  1. "Set up FastAPI with auth + Docker" — 7 occurrences
     │ Type: boilerplate-request
     │ Dates: Jan 3, Jan 8, Jan 14, Jan 20, Feb 1, Feb 9, Feb 15
     └─ 💡 Skill candidate → ai-habits generate skill --id pat-001

  2. Tech stack re-explained — 12 out of 47 conversations
     │ Type: context-re-explanation
     │ You keep telling Claude: Python 3.11, FastAPI, Postgres, Redis, GCP
     └─ 💡 Add to CLAUDE.md → ai-habits generate patch --id pat-002

  3. "lint then test then commit" — 9 occurrences
     │ Type: repeatable-workflow
     └─ 💡 Shell script → ai-habits generate script --id pat-003

⚠️  ANTI-PATTERNS
  You frequently describe your auth setup to Claude. (16 occurrences)
  💡 Document your auth architecture in CLAUDE.md — it's clearly a core
     system Claude needs to know about every session.
```

Then it generates the fixes:

```bash
# Turn a repeated pattern into a skill
ai-habits generate skill --id pat-001
# → .claude/skills/fastapi-scaffold/SKILL.md (draft, with comments explaining each section)

# Patch your CLAUDE.md with missing context
ai-habits generate patch --id pat-002
# → CLAUDE.md.patch (append to your existing file — never replaces it)

# Turn a workflow into a script
ai-habits generate script --id pat-003
# → scripts/lint-test-commit.sh
```

Everything is a **draft**. ai-habits never auto-applies anything.

---

## And it shows you features you didn't know existed

```
$ ai-habits discover

✗ Skills
  You have 5 repeated patterns that would work as skills.
  → ai-habits generate skill --id pat-001

✗ MCP Servers
  You frequently copy-paste GitHub issue content into Claude.
  → The GitHub MCP server would eliminate this entirely.

✓ CLAUDE.md — exists, but run `ai-habits audit` to check if it's still accurate
```

---

## Install

```bash
pip install 'ai-habits[ml]'
```

> Pulls in PyTorch via sentence-transformers (~500MB on first run) for local embedding. Everything runs on your machine — no conversation data leaves unless you opt into LLM classification.

**Requirements:** Python 3.11+, Claude Code with existing conversation history (`~/.claude/projects/`)

---

## Quick start

```bash
# See your patterns
ai-habits scan

# Scope to one project
ai-habits scan --project /path/to/my-project

# See what Claude Code features you're missing
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
| `--no-llm` | off | Skip classification, show all clusters |

### `ai-habits discover`
```bash
ai-habits discover [PROJECT_DIR]
```
Checks for missing Claude Code features (skills, MCP servers, CLAUDE.md) and cross-references your last scan to make it concrete: *"You have 5 patterns that would work as skills."*

### `ai-habits audit`
```bash
ai-habits audit [PROJECT_DIR]
```
Compares your CLAUDE.md against actual conversation behavior. Flags stale entries (contradicted by recent conversations) and missing entries (context you keep re-explaining). Requires CLAUDE.md — run `claude /init` first if you don't have one.

### `ai-habits generate`
```bash
ai-habits generate skill --id pat-001    # → .claude/skills/<name>/SKILL.md
ai-habits generate patch [--id pat-002]  # → CLAUDE.md.patch
ai-habits generate script --id pat-003  # → scripts/<name>.sh
```
Creates draft artifacts from detected patterns. Every generated file includes inline comments explaining what evidence triggered the suggestion.

### `ai-habits explain`
```bash
ai-habits explain --id pat-001
```
Dry-run: shows the conversations where the pattern appeared and what would have been different with a skill or config in place.

---

## LLM classification (optional, recommended)

Without an API key, all clusters are shown — including noise like short confirmations. With a key, Claude Haiku classifies each cluster and filters one-off tasks:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
ai-habits scan
```

A full 30-day scan costs a few cents. Uses `claude-haiku` only.

---

## How it works

1. **Scan** — reads `~/.claude/projects/*/` JSONL files (Claude Code's local log format)
2. **Embed** — encodes each user message with `all-MiniLM-L6-v2`, runs locally and offline
3. **Cluster** — groups similar messages with DBSCAN
4. **Classify** — optional LLM pass labels each cluster: `repeatable-workflow`, `boilerplate-request`, `context-re-explanation`, or `one-off-task`
5. **Report** — ranks by frequency, surfaces anti-patterns, suggests the right fix for each

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
