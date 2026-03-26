import logging
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

from core.constants import CONSOLIDATION_CONFLICT_THRESH, CONSOLIDATION_SCHEDULE
from memory.diary_store import DiaryStore, DiaryRecord

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConflictGroup:
    concept_ids: List[str] = field(default_factory=list)
    conflict_count: int = 0
    resolution: str = ""
    resolved_at: float = 0.0


class ConsolidationJob:
    def __init__(
        self,
        conflict_thresh: int = CONSOLIDATION_CONFLICT_THRESH,
        schedule: str = CONSOLIDATION_SCHEDULE,
    ):
        self.conflict_thresh = conflict_thresh
        self.schedule = schedule
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._conflicts: List[ConflictGroup] = []
        self._diary_store = DiaryStore()
        logger.info(
            f"ConsolidationJob initialized: thresh={conflict_thresh}, schedule={schedule}"
        )

    def start(self) -> None:
        if self._running:
            logger.warning("ConsolidationJob already running")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._consolidation_loop,
            name="ConsolidationJob",
            daemon=True,
        )
        self._thread.start()
        logger.info("ConsolidationJob started")

    def stop(self, timeout: float = 5.0) -> None:
        if not self._running:
            return
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("ConsolidationJob thread did not stop cleanly")
        self._thread = None
        logger.info("ConsolidationJob stopped")

    def _consolidation_loop(self) -> None:
        logger.info("Consolidation loop started")
        while self._running:
            try:
                time.sleep(3600)
                if not self._running:
                    break
                self._run_consolidation()
            except Exception as e:
                logger.error(f"Error in consolidation loop: {e}")
                time.sleep(60)
        logger.info("Consolidation loop stopped")

    def _run_consolidation(self) -> None:
        logger.info("Running consolidation")
        with self._lock:
            rows = self._diary_store._fetch_rows()
            entries = [self._diary_store._to_record(row, score=1.0) for row in rows]
        conflicts = self._detect_conflicts(entries)
        with self._lock:
            self._conflicts = conflicts
        logger.info(f"Consolidation complete: found {len(conflicts)} conflicts")

    def _detect_conflicts(self, entries: List[DiaryRecord]) -> List[ConflictGroup]:
        if not entries:
            return []
        tag_groups: dict = {}
        for entry in entries:
            entry_tags = set(tag.lower() for tag in entry.tags)
            for tag in entry_tags:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(entry)
        conflicts: List[ConflictGroup] = []
        for tag, tag_entries in tag_groups.items():
            if len(tag_entries) < 2:
                continue
            content_keywords: dict = {}
            for entry in tag_entries:
                keywords = set(entry.content.lower().split())
                for kw in keywords:
                    if kw not in content_keywords:
                        content_keywords[kw] = []
                    content_keywords[kw].append(entry)
            for kw, kw_entries in content_keywords.items():
                if len(kw_entries) >= self.conflict_thresh:
                    concept_ids = [e.id for e in kw_entries]
                    conflict = ConflictGroup(
                        concept_ids=concept_ids,
                        conflict_count=len(kw_entries),
                        resolution="",
                        resolved_at=0.0,
                    )
                    conflicts.append(conflict)
        return conflicts

    def _resolve_conflict(self, group: ConflictGroup) -> str:
        if not group.concept_ids:
            return "discard"
        if len(group.concept_ids) <= 1:
            return "keep_newest"
        return "merge"

    def get_conflicts(self) -> List[ConflictGroup]:
        with self._lock:
            return [c for c in self._conflicts if not c.resolution]

    def resolve_conflict(self, group_id: str) -> bool:
        with self._lock:
            for i, group in enumerate(self._conflicts):
                if group.concept_ids and group.concept_ids[0] == group_id:
                    resolution = self._resolve_conflict(group)
                    self._conflicts[i] = ConflictGroup(
                        concept_ids=group.concept_ids,
                        conflict_count=group.conflict_count,
                        resolution=resolution,
                        resolved_at=time.time(),
                    )
                    return True
        return False
