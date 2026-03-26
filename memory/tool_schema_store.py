import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.constants import (
    PROJECT_ROOT,
    TOOL_SCHEMA_CONFIDENCE_DECAY,
    TOOL_SCHEMA_STALENESS_DAYS,
)


@dataclass(frozen=True)
class ToolSchema:
    schema_id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    tool_type: str
    confidence: float
    last_used: float
    use_count: int
    staleness_days: int
    metadata: Dict[str, Any]


class ToolSchemaStore:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        staleness_days: int = TOOL_SCHEMA_STALENESS_DAYS,
        confidence_decay: float = TOOL_SCHEMA_CONFIDENCE_DECAY,
    ):
        self.db_path = db_path or (PROJECT_ROOT / ".stark" / "tool_schemas.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.staleness_days = staleness_days
        self.confidence_decay = confidence_decay
        self._lock = threading.RLock()
        self._init_schema()

    def register(self, schema: ToolSchema) -> str:
        schema_id = schema.schema_id or str(uuid.uuid4())
        now = time.time()

        with self._lock, sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT schema_id, use_count FROM tool_schemas WHERE schema_id = ?",
                (schema_id,),
            ).fetchone()

            if existing:
                new_use_count = existing[1] + 1
                conn.execute(
                    """
                    UPDATE tool_schemas SET
                        name = ?, description = ?, parameters = ?, tool_type = ?,
                        confidence = ?, last_used = ?, use_count = ?,
                        staleness_days = ?, metadata = ?
                    WHERE schema_id = ?
                    """,
                    (
                        schema.name,
                        schema.description,
                        json.dumps(schema.parameters),
                        schema.tool_type,
                        schema.confidence,
                        now,
                        new_use_count,
                        schema.staleness_days,
                        json.dumps(schema.metadata),
                        schema_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO tool_schemas (
                        schema_id, name, description, parameters, tool_type,
                        confidence, last_used, use_count, staleness_days, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        schema_id,
                        schema.name,
                        schema.description,
                        json.dumps(schema.parameters),
                        schema.tool_type,
                        schema.confidence,
                        now,
                        1,
                        schema.staleness_days,
                        json.dumps(schema.metadata),
                    ),
                )
            conn.commit()

        return schema_id

    def get(self, schema_id: str) -> Optional[ToolSchema]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tool_schemas WHERE schema_id = ?", (schema_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_schema(row)

    def query_by_name(self, name: str) -> List[ToolSchema]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM tool_schemas WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{name}%",),
            ).fetchall()
        return [self._row_to_schema(row) for row in rows]

    def query_by_type(self, tool_type: str) -> List[ToolSchema]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM tool_schemas WHERE tool_type = ?", (tool_type,)
            ).fetchall()
        return [self._row_to_schema(row) for row in rows]

    def query_weighted(self, query_text: str, top_k: int = 5) -> List[ToolSchema]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM tool_schemas").fetchall()

        scored = []
        query_lower = query_text.lower()
        for row in rows:
            schema = self._row_to_schema(row)
            name_match = (
                query_lower in schema.name.lower()
                or query_lower in schema.description.lower()
            )
            if not name_match:
                continue
            days_stale = (time.time() - schema.last_used) / 86400.0
            recency_factor = 1.0 / (1.0 + days_stale * self.confidence_decay)
            score = schema.confidence * recency_factor
            scored.append((schema, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored[:top_k]]

    def record_use(self, schema_id: str) -> None:
        now = time.time()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tool_schemas SET last_used = ?, use_count = use_count + 1 WHERE schema_id = ?",
                (now, schema_id),
            )
            conn.commit()

    def evict_stale(self) -> int:
        cutoff = time.time() - (self.staleness_days * 86400.0)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "DELETE FROM tool_schemas WHERE last_used < ?", (cutoff,)
            )
            conn.commit()
            return result.rowcount

    def count(self) -> int:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            (cnt,) = conn.execute("SELECT COUNT(*) FROM tool_schemas").fetchone()
        return int(cnt)

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_schemas (
                    schema_id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    parameters TEXT,
                    tool_type TEXT,
                    confidence REAL,
                    last_used REAL,
                    use_count INTEGER,
                    staleness_days INTEGER,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tool_type ON tool_schemas(tool_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_last_used ON tool_schemas(last_used)"
            )

    def _row_to_schema(self, row: tuple) -> ToolSchema:
        return ToolSchema(
            schema_id=row[0],
            name=row[1],
            description=row[2],
            parameters=json.loads(row[3]) if row[3] else {},
            tool_type=row[4],
            confidence=float(row[5]),
            last_used=float(row[6]),
            use_count=int(row[7]),
            staleness_days=int(row[8]),
            metadata=json.loads(row[9]) if row[9] else {},
        )
