import sqlite3

from memory.episodic_schema import ensure_episodic_schema


def test_ensure_episodic_schema_adds_v2_columns(tmp_path):
    db_path = tmp_path / "episodic.db"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE episodes (
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
        conn.execute(
            "INSERT INTO episodes (id, content, timestamp, metadata, strength, access_count, last_accessed) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("e-1", "content", 123.0, "{}", 1.0, 0, 123.0),
        )
        conn.commit()

    ensure_episodic_schema(db_path)

    with sqlite3.connect(db_path) as conn:
        cols = {
            row[1] for row in conn.execute("PRAGMA table_info(episodes)").fetchall()
        }
        row = conn.execute("SELECT id FROM episodes WHERE id = 'e-1'").fetchone()

    expected = {
        "session_id",
        "emotion_vector",
        "episode_ids",
        "tool_schemas_used",
        "insights",
        "tags",
        "neutral_embedding",
        "contextual_embedding",
    }
    assert expected.issubset(cols)
    assert row is not None


def test_ensure_episodic_schema_is_idempotent(tmp_path):
    db_path = tmp_path / "episodic.db"

    ensure_episodic_schema(db_path)
    ensure_episodic_schema(db_path)

    with sqlite3.connect(db_path) as conn:
        cols = [
            row[1] for row in conn.execute("PRAGMA table_info(episodes)").fetchall()
        ]

    assert len(cols) == len(set(cols))
