import json
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.constants import PROJECT_ROOT

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    session_id: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    emotion_vector: List[float] = field(default_factory=list)
    active_tool_schemas: List[str] = field(default_factory=list)
    retrieved_memory_ids: List[str] = field(default_factory=list)
    episode_boundaries: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    ended: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "emotion_vector": self.emotion_vector,
            "active_tool_schemas": self.active_tool_schemas,
            "retrieved_memory_ids": self.retrieved_memory_ids,
            "episode_boundaries": self.episode_boundaries,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "ended": self.ended,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        return cls(
            session_id=data["session_id"],
            messages=data.get("messages", []),
            emotion_vector=data.get("emotion_vector", []),
            active_tool_schemas=data.get("active_tool_schemas", []),
            retrieved_memory_ids=data.get("retrieved_memory_ids", []),
            episode_boundaries=data.get("episode_boundaries", []),
            started_at=data.get("started_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            ended=data.get("ended", False),
        )


class ThreadStateManager:
    def __init__(
        self, sessions_dir: Optional[Path] = None, max_state_size_mb: int = 10
    ):
        self.sessions_dir = sessions_dir or (PROJECT_ROOT / ".stark" / "sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.max_state_size_bytes = max_state_size_mb * 1024 * 1024
        self._lock = threading.RLock()
        self._sessions: Dict[str, SessionState] = {}
        self._last_message_at: Dict[str, float] = {}

    def new_session(self) -> SessionState:
        session_id = str(uuid.uuid4())
        state = SessionState(session_id=session_id)
        with self._lock:
            self._sessions[session_id] = state
            self._last_message_at[session_id] = time.time()
        self._checkpoint_state(state)
        return state

    def load_session(self, session_id: str) -> SessionState:
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]

        session_path = self._session_path(session_id)
        if not session_path.exists():
            logger.warning(
                "Session file missing for %s; starting fresh session", session_id
            )
            new_state = SessionState(session_id=session_id)
            with self._lock:
                self._sessions[session_id] = new_state
                self._last_message_at[session_id] = time.time()
            self._checkpoint_state(new_state)
            return new_state

        try:
            with open(session_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            state = SessionState.from_dict(data)
        except Exception as exc:
            logger.warning(
                "Session load failed for %s (%s); starting fresh", session_id, exc
            )
            state = SessionState(session_id=session_id)

        with self._lock:
            self._sessions[session_id] = state
            self._last_message_at[session_id] = state.updated_at
        return state

    def update(
        self,
        session_id: str,
        query: str,
        response: str,
        emotion_vector: Optional[List[float]] = None,
        active_tool_schemas: Optional[List[str]] = None,
        retrieved_memory_ids: Optional[List[str]] = None,
        episode_boundary: Optional[str] = None,
    ) -> SessionState:
        state = self.load_session(session_id)
        now = time.time()

        with self._lock:
            state.messages.append({"role": "user", "content": query})
            state.messages.append({"role": "assistant", "content": response})

            if emotion_vector is not None:
                state.emotion_vector = emotion_vector
            if active_tool_schemas is not None:
                state.active_tool_schemas = active_tool_schemas
            if retrieved_memory_ids is not None:
                state.retrieved_memory_ids = retrieved_memory_ids
            if episode_boundary is not None:
                state.episode_boundaries.append(episode_boundary)

            state.updated_at = now
            state.ended = False
            self._last_message_at[session_id] = now

        self._compress_if_needed(state)
        self._checkpoint_state(state)
        return state

    def get_or_create_session(self, session_id: Optional[str] = None) -> SessionState:
        if session_id is None:
            return self.new_session()
        return self.load_session(session_id)

    def is_conversation_ended(self, session_id: str, idle_seconds: int = 300) -> bool:
        with self._lock:
            last_seen = self._last_message_at.get(session_id)
            if last_seen is None:
                return True
            ended = (time.time() - last_seen) > idle_seconds
            if ended and session_id in self._sessions:
                self._sessions[session_id].ended = True
            return ended

    def checkpoint_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
        for state in sessions:
            self._checkpoint_state(state)

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def _checkpoint_state(self, state: SessionState) -> None:
        session_path = self._session_path(state.session_id)
        lock_path = session_path.with_suffix(".lock")
        temp_path = session_path.with_suffix(".tmp")

        try:
            with sqlite3.connect(lock_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS checkpoint_lock (id INTEGER PRIMARY KEY)"
                )
                conn.execute("BEGIN IMMEDIATE")
                with open(temp_path, "w", encoding="utf-8") as handle:
                    json.dump(state.to_dict(), handle)
                temp_path.replace(session_path)
                conn.commit()
        except Exception as exc:
            logger.warning("Checkpoint failed for %s: %s", state.session_id, exc)

    def _compress_if_needed(self, state: SessionState) -> None:
        encoded = json.dumps(state.to_dict(), separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) <= self.max_state_size_bytes:
            return

        message_count = len(state.messages)
        if message_count <= 4:
            return

        cut = max(2, message_count // 2)
        archived = state.messages[:cut]
        summary_text = self._summarize_messages(archived)
        state.messages = [{"role": "system", "content": summary_text}] + state.messages[
            cut:
        ]
        state.updated_at = time.time()

    def _summarize_messages(self, messages: List[Dict[str, str]]) -> str:
        max_preview = 8
        fragments: List[str] = []
        for msg in messages[:max_preview]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "").strip().replace("\n", " ")
            if len(content) > 120:
                content = content[:117] + "..."
            fragments.append(f"{role}: {content}")
        hidden = len(messages) - len(fragments)
        if hidden > 0:
            fragments.append(f"... {hidden} more messages archived")
        return "Archived conversation summary | " + " | ".join(fragments)


_thread_state_manager: Optional[ThreadStateManager] = None


def get_thread_state_manager() -> ThreadStateManager:
    global _thread_state_manager
    if _thread_state_manager is None:
        _thread_state_manager = ThreadStateManager()
    return _thread_state_manager
