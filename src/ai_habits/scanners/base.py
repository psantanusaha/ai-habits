"""Abstract adapter interface for conversation history scanners."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator


@dataclass
class Message:
    """A single user message from a conversation."""

    uuid: str
    session_id: str
    project_path: Path  # cwd at the time of the message
    timestamp: datetime
    text: str
    parent_uuid: str | None = None


@dataclass
class Session:
    """A single conversation session."""

    session_id: str
    project_path: Path
    messages: list[Message] = field(default_factory=list)

    @property
    def start_time(self) -> datetime | None:
        return self.messages[0].timestamp if self.messages else None

    @property
    def end_time(self) -> datetime | None:
        return self.messages[-1].timestamp if self.messages else None


class BaseScanner(ABC):
    """Abstract base class for conversation history adapters."""

    @abstractmethod
    def iter_sessions(
        self,
        project_path: Path | None = None,
        since: datetime | None = None,
    ) -> Iterator[Session]:
        """Yield :class:`Session` objects from the conversation store.

        Args:
            project_path: If given, only yield sessions for this project.
            since: If given, only yield sessions after this datetime.
        """

    def all_messages(
        self,
        project_path: Path | None = None,
        since: datetime | None = None,
    ) -> list[Message]:
        """Convenience: return a flat list of all user messages."""
        messages: list[Message] = []
        for session in self.iter_sessions(project_path=project_path, since=since):
            messages.extend(session.messages)
        return messages
