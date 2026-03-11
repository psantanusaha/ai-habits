# ai-habits

Every token you send to Claude costs money. A lot of yours are being wasted.

---

## You're paying to re-explain the same context, over and over

Claude has no memory between sessions. So every few conversations, you end up typing some version of:

> *"This is a FastAPI project, we use Postgres, deployed on GCP, auth is JWT-based..."*

That's ~80 tokens. You've sent it **12 times in the last month**. That's 960 tokens Claude processed, understood, and then forgot. Multiply that by every project, every month.

If that context lived in your `CLAUDE.md`, Claude would load it once per session — structured, consistent, free after the first turn. Instead you're paying for it every time, and getting a worse result because Claude is reading it off a casual message instead of a curated file.

---

## You're paying for the same boilerplate, over and over

That Docker + FastAPI scaffold you keep asking for? You've requested it **7 times** since January.

A typical scaffold response runs ~800 output tokens. At Sonnet pricing, you've spent roughly **$0.08 just on that one pattern** — and gotten slightly different output each time, because Claude doesn't remember how you want it done.

A skill generates it identically in one invocation, with zero re-explanation tokens. You don't have any skills.

---

## You're burning tokens correcting Claude on things it should already know

Every time Claude gets your conventions wrong and you correct it — *"no, we use pytest not unittest", "no, we don't use `any` in TypeScript"* — that's a correction turn. Input tokens for your message. Output tokens for Claude's response. Input tokens again when Claude finally does it right.

Instructions that belong in `CLAUDE.md` get processed once. Instructions you type mid-conversation get processed once, forgotten, and typed again next time.

---

## You have a workflow you type out step by step, every time

> *"lint, then run tests, then commit"*

9 times last month. Each time: your tokens to describe it, Claude's tokens to respond, back and forth until it's done. That's a shell script or a slash command. It takes 2 minutes to set up and costs nothing to run forever.

---

## Your CLAUDE.md is stale — so Claude is operating on bad context

Most developers either don't have a `CLAUDE.md`, or wrote one months ago and never touched it again. Meanwhile the stack evolved, the conventions changed, and Claude is consuming tokens acting on outdated instructions — and occasionally getting it wrong, costing more tokens to correct.

---

## `ai-habits` shows you exactly where the tokens are going

```
$ ai-habits scan

📊 Scanned 47 conversations (last 30 days)

🔁 REPEATED PATTERNS

  1. "Set up FastAPI with auth + Docker" — 7 occurrences
     │ Type: boilerplate-request
     │ Dates: Jan 3, Jan 8, Jan 14, Jan 20, Feb 1, Feb 9, Feb 15
     │ Est. wasted: ~5,600 output tokens (same scaffold generated 7×)
     └─ 💡 Skill candidate → ai-habits generate skill --id pat-001

  2. Tech stack re-explained — 12 out of 47 conversations
     │ Type: context-re-explanation
     │ You keep telling Claude: Python 3.11, FastAPI, Postgres, Redis, GCP
     │ Est. wasted: ~960 input tokens (80 tokens × 12 sessions)
     └─ 💡 Add to CLAUDE.md → ai-habits generate patch --id pat-002

  3. "lint then test then commit" — 9 occurrences
     │ Type: repeatable-workflow
     │ Est. wasted: ~1,800 tokens (back-and-forth × 9 runs)
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

## The token math

A few common patterns, priced at Claude Sonnet rates ($3/MTok input, $15/MTok output):

| Pattern | Without ai-habits | With ai-habits |
|---|---|---|
| Stack context re-explained 12×/month | ~960 input tokens/month, repeated forever | 0 — loaded once from CLAUDE.md |
| Same boilerplate requested 7× | ~5,600 output tokens, inconsistent results | 1 skill invocation, consistent output |
| Correction loops ("no, use pytest") | 2–4 turns per correction, every session | 0 — instruction lives in CLAUDE.md |
| "lint → test → commit" typed 9× | ~1,800 tokens of back-and-forth | 1 shell script, runs in 1 command |

None of these are large numbers individually. Combined, across projects, over months — it adds up. More importantly: every one of these patterns means Claude is working with less context than it could have, producing worse output than it should.

The fix for each takes minutes. ai-habits finds them.

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
