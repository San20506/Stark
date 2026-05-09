"""
Channel Index — Thread Continuity
===================================
Bidirectional map: Hermes conversation_id ↔ STARK thread_id ↔ user_persona.
Persisted in SQLite (same DB as thread_state) so context survives restarts.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.constants import DATA_DIR

logger = logging.getLogger(__name__)

_DB_PATH = DATA_DIR / "memory" / "channel_index.db"

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS channel_map (
    conversation_id TEXT NOT NULL,
    platform        TEXT NOT NULL DEFAULT 'unknown',
    thread_id       TEXT NOT NULL,
    user_persona    TEXT NOT NULL DEFAULT '',
    created_at      REAL NOT NULL,
    last_seen       REAL NOT NULL,
    PRIMARY KEY (conversation_id)
);
CREATE TABLE IF NOT EXISTS persona_aliases (
    user_persona    TEXT NOT NULL,
    platform        TEXT NOT NULL,
    platform_user_id TEXT NOT NULL,
    PRIMARY KEY (user_persona, platform, platform_user_id)
);
"""


@dataclass
class ChannelEntry:
    conversation_id: str
    platform: str
    thread_id: str
    user_persona: str
    created_at: float
    last_seen: float


class ChannelIndex:
    """
    Maps Hermes conversation_ids to STARK thread_ids.

    Thread continuity:
    - Same conversation_id always resolves to the same thread_id.
    - Trusted users on different platforms can be merged under one persona.
    - New conversation_ids get a fresh thread_id on first contact.
    """

    def __init__(self, db_path: Path = _DB_PATH) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._init_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_create_thread(
        self, conversation_id: str, platform: str = "unknown", user_id: str = ""
    ) -> str:
        """
        Return the STARK thread_id for this Hermes conversation.
        Creates a new mapping on first call.
        """
        existing = self._fetch(conversation_id)
        if existing:
            self._touch(conversation_id)
            return existing.thread_id

        thread_id = f"hermes:{platform}:{conversation_id}"
        persona = self._resolve_persona(platform, user_id)
        now = time.time()
        self._insert(
            ChannelEntry(
                conversation_id=conversation_id,
                platform=platform,
                thread_id=thread_id,
                user_persona=persona,
                created_at=now,
                last_seen=now,
            )
        )
        logger.debug("New channel mapping: %s → %s", conversation_id, thread_id)
        return thread_id

    def get_thread(self, conversation_id: str) -> Optional[str]:
        """Return existing thread_id or None."""
        entry = self._fetch(conversation_id)
        return entry.thread_id if entry else None

    def register_persona_alias(
        self, user_persona: str, platform: str, platform_user_id: str
    ) -> None:
        """Link a platform user_id to a named persona (for cross-platform merging)."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO persona_aliases VALUES (?, ?, ?)",
                (user_persona, platform, platform_user_id),
            )

    def get_persona(self, conversation_id: str) -> str:
        entry = self._fetch(conversation_id)
        return entry.user_persona if entry else ""

    def all_entries(self) -> list[ChannelEntry]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM channel_map ORDER BY last_seen DESC").fetchall()
        return [self._row_to_entry(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_CREATE_SQL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _fetch(self, conversation_id: str) -> Optional[ChannelEntry]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM channel_map WHERE conversation_id = ?", (conversation_id,)
            ).fetchone()
        return self._row_to_entry(row) if row else None

    def _insert(self, entry: ChannelEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO channel_map VALUES (?, ?, ?, ?, ?, ?)",
                (
                    entry.conversation_id,
                    entry.platform,
                    entry.thread_id,
                    entry.user_persona,
                    entry.created_at,
                    entry.last_seen,
                ),
            )

    def _touch(self, conversation_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE channel_map SET last_seen = ? WHERE conversation_id = ?",
                (time.time(), conversation_id),
            )

    def _resolve_persona(self, platform: str, platform_user_id: str) -> str:
        if not platform_user_id:
            return ""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_persona FROM persona_aliases WHERE platform = ? AND platform_user_id = ?",
                (platform, platform_user_id),
            ).fetchone()
        return row["user_persona"] if row else platform_user_id

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> ChannelEntry:
        return ChannelEntry(
            conversation_id=row["conversation_id"],
            platform=row["platform"],
            thread_id=row["thread_id"],
            user_persona=row["user_persona"],
            created_at=row["created_at"],
            last_seen=row["last_seen"],
        )
