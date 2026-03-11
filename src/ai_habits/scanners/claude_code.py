"""Scanner adapter for Claude Code local conversation logs.

## Claude Code Log Format (reverse-engineered, as of Claude Code v2.1.x)

### Storage location
    ~/.claude/projects/<encoded-path>/<session-uuid>.jsonl

### Path encoding
    Absolute path with '/' replaced by '-', no leading slash dropped.
    Example: /Users/foo/my-project → ~/.claude/projects/-Users-foo-my-project/

    To reverse: encoded.replace('-', '/') → but hyphens in dir names are ambiguous.
    Safer approach: iterate all project dirs and match by CWD field in records.

### Per-session file
    One .jsonl file per conversation session.
    Each line is a JSON object with a mandatory "type" field.

### Record types

    type = "user"
        A user turn in the conversation.
        Fields:
            uuid          str       unique message ID
            parentUuid    str|null  ID of the preceding message (null = start)
            timestamp     str       ISO 8601 UTC  (e.g. "2026-02-27T21:08:42.639Z")
            sessionId     str       matches the filename stem
            cwd           str       working directory when message was sent
            isSidechain   bool      True for subagent/background conversations — SKIP these
            userType      str       "external" = real user input
            permissionMode str      "default" | "acceptEdits" | etc.
            message       object
                role      "user"
                content   str | list[ContentBlock]

            ContentBlock:
                { "type": "text", "text": "..." }          — user text
                { "type": "tool_result", ... }             — tool output fed back in
                { "type": "thinking", ... }                — model thinking (skip)

        To extract text: if content is str, use it. If list, join all items
        where item["type"] == "text".

    type = "assistant"
        Claude's response. Skip for user message extraction.

    type = "system"
        Session lifecycle event (init/exit). Fields: subtype, durationMs.

    type = "progress"
        Tool use in progress. Fields: toolUseID, parentToolUseID, slug, data.

    type = "queue-operation"
        Session init queue. Fields: operation ("enqueue"|"dequeue"), content.

    type = "file-history-snapshot"
        File state snapshot for context. Fields: messageId, snapshot.

### Filtering rules
    - Keep: type == "user" AND isSidechain == false
    - Skip: messages where content is only tool_result blocks (no user text)
    - Skip: messages where extracted text is empty or whitespace only

### Known risks
    - Format is undocumented — may change between Claude Code versions
    - Path encoding is lossy (hyphens in dir names)
    - Subagent JSONL files live in <session-uuid>/subagents/ — skip these
    - Large files (1000+ lines) for long sessions with many tool calls
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from ai_habits.scanners.base import BaseScanner, Message, Session

logger = logging.getLogger(__name__)

CLAUDE_DIR = Path.home() / ".claude" / "projects"


class ClaudeCodeScanner(BaseScanner):
    """Reads Claude Code JSONL logs from ~/.claude/projects/."""

    def __init__(self, claude_dir: Path = CLAUDE_DIR) -> None:
        self._claude_dir = claude_dir

    def iter_sessions(
        self,
        project_path: Path | None = None,
        since: datetime | None = None,
    ) -> Iterator[Session]:
        """Yield sessions from Claude Code logs.

        Args:
            project_path: If given, only sessions whose CWD starts with this path.
            since: If given, only sessions with at least one message after this time.
        """
        if not self._claude_dir.exists():
            logger.warning(
                "Claude Code log directory not found: %s\n"
                "Make sure Claude Code is installed and has been used.",
                self._claude_dir,
            )
            return

        for project_dir in sorted(self._claude_dir.iterdir()):
            if not project_dir.is_dir():
                continue
            for jsonl_path in sorted(project_dir.glob("*.jsonl")):
                session = self._parse_session(jsonl_path, project_path, since)
                if session is not None and session.messages:
                    yield session

    def list_projects(self) -> list[Path]:
        """Return the set of unique project CWD paths found in logs."""
        seen: set[str] = set()
        projects: list[Path] = []
        for session in self.iter_sessions():
            p = str(session.project_path)
            if p not in seen:
                seen.add(p)
                projects.append(session.project_path)
        return projects

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_session(
        self,
        path: Path,
        project_path: Path | None,
        since: datetime | None,
    ) -> Session | None:
        """Parse one JSONL file into a Session. Returns None on failure."""
        session_id = path.stem
        messages: list[Message] = []
        session_cwd: Path = Path(".")

        try:
            for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    record = json.loads(raw_line)
                except json.JSONDecodeError:
                    logger.debug("Skipping malformed line in %s", path)
                    continue

                if record.get("type") != "user":
                    continue
                if record.get("isSidechain", False):
                    continue

                text = _extract_text(record.get("message", {}).get("content", ""))
                if not text:
                    continue

                cwd = Path(record.get("cwd", "."))
                session_cwd = cwd  # use last seen cwd as session cwd

                if project_path and not _path_matches(cwd, project_path):
                    continue

                ts = _parse_timestamp(record.get("timestamp", ""))
                if since and ts and ts < since:
                    continue

                messages.append(
                    Message(
                        uuid=record.get("uuid", ""),
                        session_id=session_id,
                        project_path=cwd,
                        timestamp=ts or datetime.now(tz=timezone.utc),
                        text=text,
                        parent_uuid=record.get("parentUuid"),
                    )
                )
        except OSError as e:
            logger.warning("Could not read %s: %s", path, e)
            return None

        if not messages:
            return None

        return Session(
            session_id=session_id,
            project_path=session_cwd,
            messages=messages,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_text(content: str | list | object) -> str:
    """Extract plain text from a message content field."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                t = block.get("text", "").strip()
                if t:
                    parts.append(t)
            # Skip tool_result, thinking, image blocks
        return " ".join(parts).strip()
    return ""


def _parse_timestamp(ts: str) -> datetime | None:
    """Parse an ISO 8601 timestamp string to a timezone-aware datetime."""
    if not ts:
        return None
    try:
        # Python 3.11+ handles 'Z' suffix; handle older versions too
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _path_matches(cwd: Path, project_path: Path) -> bool:
    """Return True if cwd is equal to or inside project_path."""
    try:
        cwd.relative_to(project_path)
        return True
    except ValueError:
        return False
