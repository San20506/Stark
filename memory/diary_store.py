import json
import math
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from core.constants import (
    DIARY_MAX_ENTRIES_SOFT_CAP,
    PROJECT_ROOT,
)
from memory.episodic_schema import ensure_episodic_schema


def _tokenize(text: str) -> List[str]:
    return [token for token in text.lower().split() if token]


def _hash_embedding(text: str, dim: int = 128) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    tokens = _tokenize(text)
    if not tokens:
        return vec
    for token in tokens:
        vec[hash(token) % dim] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


@dataclass(frozen=True)
class DiaryEntry:
    content: str
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    emotion_vector: Optional[List[float]] = None
    episode_ids: List[str] = field(default_factory=list)
    tool_schemas_used: List[str] = field(default_factory=list)
    insights: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    neutral_embedding: Optional[np.ndarray] = None
    contextual_embedding: Optional[np.ndarray] = None


@dataclass(frozen=True)
class DiaryRecord:
    id: str
    content: str
    timestamp: float
    session_id: Optional[str]
    emotion_vector: List[float]
    episode_ids: List[str]
    tool_schemas_used: List[str]
    insights: str
    tags: List[str]
    metadata: Dict[str, Any]
    score: float


_diary_store_instance: Optional["DiaryStore"] = None


def get_diary_store(db_path: Optional[Path] = None) -> "DiaryStore":
    global _diary_store_instance
    if _diary_store_instance is None:
        _diary_store_instance = DiaryStore(db_path=db_path)
    return _diary_store_instance


class DiaryStore:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        soft_cap: int = DIARY_MAX_ENTRIES_SOFT_CAP,
        archive_path: Optional[Path] = None,
    ):
        self.db_path = ensure_episodic_schema(db_path)
        self.soft_cap = max(1, soft_cap)
        self.archive_path = archive_path or (
            PROJECT_ROOT / ".stark" / "archives" / "diary_archive.jsonl"
        )
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def write(self, entry: DiaryEntry) -> str:
        entry_id = str(uuid.uuid4())
        neutral = (
            entry.neutral_embedding
            if entry.neutral_embedding is not None
            else _hash_embedding(entry.content)
        )
        contextual = (
            entry.contextual_embedding
            if entry.contextual_embedding is not None
            else self._contextualize_embedding(neutral, entry.emotion_vector)
        )

        row = {
            "id": entry_id,
            "content": entry.content,
            "timestamp": float(entry.timestamp),
            "metadata": json.dumps(entry.metadata),
            "strength": float(entry.metadata.get("strength", 1.0)),
            "access_count": int(entry.metadata.get("access_count", 0)),
            "last_accessed": float(
                entry.metadata.get("last_accessed", entry.timestamp)
            ),
            "session_id": entry.session_id,
            "emotion_vector": json.dumps(entry.emotion_vector or []),
            "episode_ids": json.dumps(entry.episode_ids),
            "tool_schemas_used": json.dumps(entry.tool_schemas_used),
            "insights": entry.insights,
            "tags": json.dumps(entry.tags),
            "neutral_embedding": neutral.astype(np.float32).tobytes(),
            "contextual_embedding": contextual.astype(np.float32).tobytes(),
        }

        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO episodes (
                    id, content, timestamp, metadata, strength, access_count, last_accessed,
                    session_id, emotion_vector, episode_ids, tool_schemas_used, insights, tags,
                    neutral_embedding, contextual_embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["content"],
                    row["timestamp"],
                    row["metadata"],
                    row["strength"],
                    row["access_count"],
                    row["last_accessed"],
                    row["session_id"],
                    row["emotion_vector"],
                    row["episode_ids"],
                    row["tool_schemas_used"],
                    row["insights"],
                    row["tags"],
                    row["neutral_embedding"],
                    row["contextual_embedding"],
                ),
            )
            conn.commit()

        self._enforce_soft_cap()
        return entry_id

    def query_semantic(
        self,
        text: str,
        top_k: int = 5,
        query_emotion_vector: Optional[List[float]] = None,
    ) -> List[DiaryRecord]:
        query_embedding = _hash_embedding(text)
        rows = self._fetch_rows()
        scored = []
        for row in rows:
            neutral = self._blob_to_embedding(row[13])
            semantic_sim = max(0.0, (_cosine(query_embedding, neutral) + 1.0) / 2.0)
            score = self._final_score(
                semantic_sim=semantic_sim,
                timestamp=float(row[2]),
                query_emotion_vector=query_emotion_vector,
                entry_emotion_vector=self._json_list(row[8]),
            )
            scored.append(self._to_record(row, score))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[: max(1, top_k)]

    def query_timerange(self, start: float, end: float) -> List[DiaryRecord]:
        rows = self._fetch_rows("timestamp >= ? AND timestamp <= ?", (start, end))
        records = [self._to_record(row, score=1.0) for row in rows]
        records.sort(key=lambda item: item.timestamp)
        return records

    def query_emotion(
        self, emotion_range_dict: Dict[int, tuple[float, float]]
    ) -> List[DiaryRecord]:
        rows = self._fetch_rows()
        records: List[DiaryRecord] = []
        for row in rows:
            vector = self._json_list(row[8])
            if self._emotion_matches(vector, emotion_range_dict):
                records.append(self._to_record(row, score=1.0))
        return records

    def query_tags(self, tags: List[str]) -> List[DiaryRecord]:
        wanted = {tag.lower() for tag in tags}
        rows = self._fetch_rows()
        records = []
        for row in rows:
            row_tags = {tag.lower() for tag in self._json_list(row[12])}
            if wanted.intersection(row_tags):
                records.append(self._to_record(row, score=1.0))
        return records

    def count(self) -> int:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            (count,) = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()
        return int(count)

    def _fetch_rows(self, where_sql: str = "", params: tuple = ()) -> List[tuple]:
        query = "SELECT * FROM episodes"
        if where_sql:
            query += f" WHERE {where_sql}"
        with self._lock, sqlite3.connect(self.db_path) as conn:
            return conn.execute(query, params).fetchall()

    def _to_record(self, row: tuple, score: float) -> DiaryRecord:
        metadata_raw = row[3] if row[3] else "{}"
        metadata = json.loads(metadata_raw)
        return DiaryRecord(
            id=row[0],
            content=row[1],
            timestamp=float(row[2]),
            session_id=row[7],
            emotion_vector=self._json_list(row[8]),
            episode_ids=self._json_list(row[9]),
            tool_schemas_used=self._json_list(row[10]),
            insights=row[11] or "",
            tags=self._json_list(row[12]),
            metadata=metadata,
            score=float(score),
        )

    def _json_list(self, value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return []
        return []

    def _blob_to_embedding(self, blob_value: Any) -> np.ndarray:
        if blob_value is None:
            return np.zeros(128, dtype=np.float32)
        emb = np.frombuffer(blob_value, dtype=np.float32)
        if emb.size == 0:
            return np.zeros(128, dtype=np.float32)
        return emb

    def _contextualize_embedding(
        self, neutral: np.ndarray, emotion_vector: Optional[List[float]]
    ) -> np.ndarray:
        if not emotion_vector:
            return neutral
        emotion = np.array(emotion_vector, dtype=np.float32)
        if emotion.size == 0:
            return neutral
        expanded = np.zeros_like(neutral)
        limit = min(len(expanded), len(emotion))
        expanded[:limit] = emotion[:limit]
        mixed = (0.85 * neutral) + (0.15 * expanded)
        norm = np.linalg.norm(mixed)
        if norm == 0:
            return mixed
        return mixed / norm

    def _final_score(
        self,
        semantic_sim: float,
        timestamp: float,
        query_emotion_vector: Optional[List[float]],
        entry_emotion_vector: List[float],
    ) -> float:
        days_since = max(0.0, (time.time() - timestamp) / 86400.0)
        recency = 1.0 / (1.0 + math.log(days_since + 1.0))
        emotional_resonance = 0.0
        if query_emotion_vector and entry_emotion_vector:
            q = np.array(query_emotion_vector, dtype=np.float32)
            e = np.array(entry_emotion_vector, dtype=np.float32)
            emotional_resonance = max(0.0, (_cosine(q, e) + 1.0) / 2.0)
        return (0.7 * semantic_sim) + (0.2 * recency) + (0.1 * emotional_resonance)

    def _emotion_matches(
        self, vector: List[float], ranges: Dict[int, tuple[float, float]]
    ) -> bool:
        for idx, (low, high) in ranges.items():
            if idx >= len(vector):
                return False
            if not (low <= float(vector[idx]) <= high):
                return False
        return True

    def _enforce_soft_cap(self) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            (count,) = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()
            overflow = int(count) - self.soft_cap
            if overflow <= 0:
                return
            rows = conn.execute(
                "SELECT id, content, timestamp, metadata FROM episodes ORDER BY timestamp ASC LIMIT ?",
                (overflow,),
            ).fetchall()
            if not rows:
                return

            with open(self.archive_path, "a", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(
                        json.dumps(
                            {
                                "id": row[0],
                                "content": row[1],
                                "timestamp": row[2],
                                "metadata": json.loads(row[3] or "{}"),
                            }
                        )
                        + "\n"
                    )

            ids = [row[0] for row in rows]
            placeholders = ",".join(["?"] * len(ids))
            conn.execute(f"DELETE FROM episodes WHERE id IN ({placeholders})", ids)
            conn.commit()
