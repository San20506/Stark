import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.constants import EPISODE_SURPRISE_THRESHOLD
from memory.diary_store import DiaryEntry, get_diary_store
from memory.thread_state import SessionState

logger = logging.getLogger(__name__)


@dataclass
class Episode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    emotion_vector: List[float] = field(default_factory=list)
    tool_schemas_used: List[str] = field(default_factory=list)
    insights: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EpisodeManager:
    def __init__(self, surprise_threshold: float = EPISODE_SURPRISE_THRESHOLD):
        self.surprise_threshold = surprise_threshold
        self._last_surprise = 0.0

    def should_segment(self, confidence: float, context_drift: float = 0.0) -> bool:
        surprise = 1.0 - confidence
        self._last_surprise = surprise

        # Trigger if surprise exceeds threshold or significant context drift
        return surprise >= self.surprise_threshold or context_drift > 0.8

    def create_episode_from_session(
        self, session: SessionState, insights: str = ""
    ) -> Episode:
        # Concatenate session messages into a single block
        content_parts = []
        for msg in session.messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            content_parts.append(f"{role.upper()}: {text}")

        content = "\n".join(content_parts)

        # Extract tags from content (basic keyword extraction)
        tags = self._extract_tags(content)

        episode = Episode(
            content=content,
            session_id=session.session_id,
            emotion_vector=session.emotion_vector,
            tool_schemas_used=session.active_tool_schemas,
            insights=insights,
            tags=tags,
            metadata={
                "message_count": len(session.messages),
                "duration_sec": time.time() - session.started_at,
            },
        )

        logger.info(f"Created episode {episode.id} from session {session.session_id}")
        return episode

    def commit_episode(self, episode: Episode) -> str:
        store = get_diary_store()
        entry = DiaryEntry(
            content=episode.content,
            timestamp=episode.timestamp,
            session_id=episode.session_id,
            emotion_vector=episode.emotion_vector,
            tool_schemas_used=episode.tool_schemas_used,
            insights=episode.insights,
            tags=episode.tags,
            metadata=episode.metadata,
        )
        return store.write(entry)

    def _extract_tags(self, text: str) -> List[str]:
        # Placeholder for more complex NLP tag extraction
        # For now, just a simple word-frequency/regex logic
        import re

        words = re.findall(r"\b[a-zA-Z]{5,}\b", text.lower())
        # Filter for common tech terms if needed or just return top frequent
        from collections import Counter

        common = Counter(words).most_common(5)
        return [w for w, c in common]
