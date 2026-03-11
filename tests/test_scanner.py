"""Tests for the Claude Code scanner using fixture JSONL files."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_habits.scanners.claude_code import ClaudeCodeScanner, _extract_text, _parse_timestamp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"


def _write_session(tmp_path: Path, session_id: str, records: list[dict]) -> Path:
    """Write a fixture JSONL session file."""
    project_dir = tmp_path / "projects" / "-Users-test-project"
    project_dir.mkdir(parents=True, exist_ok=True)
    jsonl = project_dir / f"{session_id}.jsonl"
    jsonl.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return jsonl


def _user_record(text: str, uuid: str = "u1", ts: str = "2026-01-10T12:00:00.000Z") -> dict:
    return {
        "type": "user",
        "uuid": uuid,
        "parentUuid": None,
        "sessionId": "sess-1",
        "cwd": "/Users/test/project",
        "timestamp": ts,
        "isSidechain": False,
        "userType": "external",
        "permissionMode": "default",
        "message": {"role": "user", "content": text},
    }


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------

def test_extract_text_string():
    assert _extract_text("hello world") == "hello world"


def test_extract_text_list_single():
    content = [{"type": "text", "text": "hello"}]
    assert _extract_text(content) == "hello"


def test_extract_text_list_multi():
    content = [
        {"type": "text", "text": "hello"},
        {"type": "tool_result", "content": "ignored"},
        {"type": "text", "text": "world"},
    ]
    assert _extract_text(content) == "hello world"


def test_extract_text_empty_list():
    assert _extract_text([]) == ""


def test_extract_text_tool_result_only():
    content = [{"type": "tool_result", "content": "ignored"}]
    assert _extract_text(content) == ""


def test_parse_timestamp_valid():
    ts = _parse_timestamp("2026-01-10T12:00:00.000Z")
    assert ts is not None
    assert ts.year == 2026
    assert ts.tzinfo is not None


def test_parse_timestamp_empty():
    assert _parse_timestamp("") is None


def test_parse_timestamp_invalid():
    assert _parse_timestamp("not-a-date") is None


# ---------------------------------------------------------------------------
# Scanner integration tests (using tmp fixture dirs)
# ---------------------------------------------------------------------------

def test_scan_basic_messages(tmp_path):
    _write_session(tmp_path, "sess-1", [
        _user_record("How do I set up FastAPI?", uuid="u1"),
        _user_record("Add Docker support", uuid="u2"),
        {"type": "assistant", "uuid": "a1", "message": {"role": "assistant", "content": "Sure..."}},
    ])
    scanner = ClaudeCodeScanner(claude_dir=tmp_path / "projects")
    messages = scanner.all_messages()
    assert len(messages) == 2
    assert messages[0].text == "How do I set up FastAPI?"
    assert messages[1].text == "Add Docker support"


def test_scan_skips_sidechain(tmp_path):
    records = [
        _user_record("Real message", uuid="u1"),
        {**_user_record("Sidechain message", uuid="u2"), "isSidechain": True},
    ]
    _write_session(tmp_path, "sess-1", records)
    scanner = ClaudeCodeScanner(claude_dir=tmp_path / "projects")
    messages = scanner.all_messages()
    assert len(messages) == 1
    assert messages[0].text == "Real message"


def test_scan_skips_empty_text(tmp_path):
    records = [
        _user_record("Valid message", uuid="u1"),
        _user_record("", uuid="u2"),
        {**_user_record("ignored", uuid="u3"), "message": {"role": "user", "content": [{"type": "tool_result"}]}},
    ]
    _write_session(tmp_path, "sess-1", records)
    scanner = ClaudeCodeScanner(claude_dir=tmp_path / "projects")
    messages = scanner.all_messages()
    assert len(messages) == 1
    assert messages[0].text == "Valid message"


def test_scan_since_filter(tmp_path):
    records = [
        _user_record("Old message", uuid="u1", ts="2026-01-01T12:00:00.000Z"),
        _user_record("New message", uuid="u2", ts="2026-03-01T12:00:00.000Z"),
    ]
    _write_session(tmp_path, "sess-1", records)
    scanner = ClaudeCodeScanner(claude_dir=tmp_path / "projects")
    since = datetime(2026, 2, 1, tzinfo=timezone.utc)
    messages = scanner.all_messages(since=since)
    assert len(messages) == 1
    assert messages[0].text == "New message"


def test_scan_empty_dir(tmp_path):
    (tmp_path / "projects").mkdir()
    scanner = ClaudeCodeScanner(claude_dir=tmp_path / "projects")
    messages = scanner.all_messages()
    assert messages == []


def test_scan_missing_dir(tmp_path):
    scanner = ClaudeCodeScanner(claude_dir=tmp_path / "nonexistent")
    messages = scanner.all_messages()
    assert messages == []


def test_scan_malformed_json(tmp_path):
    project_dir = tmp_path / "projects" / "-test"
    project_dir.mkdir(parents=True)
    jsonl = project_dir / "sess-bad.jsonl"
    jsonl.write_text('{"type":"user","message":{"role":"user","content":"ok"},"isSidechain":false,"cwd":"/test","uuid":"u1","timestamp":"2026-01-10T12:00:00.000Z","sessionId":"sess-bad"}\nNOT JSON\n{"type":"user","message":{"role":"user","content":"also ok"},"isSidechain":false,"cwd":"/test","uuid":"u2","timestamp":"2026-01-10T12:00:01.000Z","sessionId":"sess-bad"}\n')
    scanner = ClaudeCodeScanner(claude_dir=tmp_path / "projects")
    messages = scanner.all_messages()
    # Should parse valid lines and skip the bad one
    assert len(messages) == 2
