import sqlite3
from pathlib import Path
from typing import Iterable

from core.constants import PROJECT_ROOT


EPISODIC_COLUMNS: tuple[str, ...] = (
    "session_id TEXT",
    "emotion_vector TEXT",
    "episode_ids TEXT",
    "tool_schemas_used TEXT",
    "insights TEXT",
    "tags TEXT",
    "neutral_embedding BLOB",
    "contextual_embedding BLOB",
)


def ensure_episodic_schema(db_path: Path | None = None) -> Path:
    target = db_path or (PROJECT_ROOT / "data" / "memory" / "episodic.db")
    target.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(target) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                content TEXT,
                timestamp REAL,
                metadata TEXT,
                strength REAL,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON episodes(timestamp)")
        _ensure_columns(conn, EPISODIC_COLUMNS)

    return target


def _existing_columns(conn: sqlite3.Connection) -> set[str]:
    rows: Iterable[tuple] = conn.execute("PRAGMA table_info(episodes)").fetchall()
    return {row[1] for row in rows}


def _ensure_columns(conn: sqlite3.Connection, column_defs: tuple[str, ...]) -> None:
    existing = _existing_columns(conn)
    for definition in column_defs:
        col_name = definition.split()[0]
        if col_name not in existing:
            conn.execute(f"ALTER TABLE episodes ADD COLUMN {definition}")
