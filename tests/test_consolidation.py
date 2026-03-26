"""Tests for memory/consolidation.py — ConsolidationJob."""
import time
import uuid
from unittest.mock import MagicMock, patch

import pytest

from memory.consolidation import ConflictGroup, ConsolidationJob
from memory.diary_store import DiaryRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(
    *,
    content: str = "test content",
    tags: list = None,
    record_id: str = None,
) -> DiaryRecord:
    return DiaryRecord(
        id=record_id or str(uuid.uuid4()),
        content=content,
        timestamp=time.time(),
        session_id=None,
        emotion_vector=[],
        episode_ids=[],
        tool_schemas_used=[],
        insights="",
        tags=tags or [],
        metadata={},
        score=1.0,
    )


def _make_job(**kwargs) -> ConsolidationJob:
    """Create a ConsolidationJob with a mocked DiaryStore so no real DB is created."""
    with patch("memory.consolidation.DiaryStore") as MockDiaryStore:
        MockDiaryStore.return_value = MagicMock()
        job = ConsolidationJob(**kwargs)
    return job


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

def test_init_default_values():
    from core.constants import CONSOLIDATION_CONFLICT_THRESH, CONSOLIDATION_SCHEDULE
    job = _make_job()
    assert job.conflict_thresh == CONSOLIDATION_CONFLICT_THRESH
    assert job.schedule == CONSOLIDATION_SCHEDULE


def test_init_custom_values():
    job = _make_job(conflict_thresh=20, schedule="04:00")
    assert job.conflict_thresh == 20
    assert job.schedule == "04:00"


# ---------------------------------------------------------------------------
# start / stop
# ---------------------------------------------------------------------------

def test_start_stop():
    job = _make_job()
    job.start()
    assert job._running is True
    assert job._thread is not None
    assert job._thread.is_alive()

    job.stop(timeout=2.0)
    assert job._running is False
    assert job._thread is None


def test_start_idempotent():
    """Calling start() twice must not raise or create a second thread."""
    job = _make_job()
    job.start()
    thread_before = job._thread
    job.start()  # second call — should be a no-op
    assert job._thread is thread_before
    job.stop(timeout=2.0)


# ---------------------------------------------------------------------------
# _detect_conflicts
# ---------------------------------------------------------------------------

def test_detect_conflicts_empty():
    job = _make_job()
    result = job._detect_conflicts([])
    assert result == []


def test_detect_conflicts_finds_repeated_keywords():
    """
    12 entries that share a common tag and a common keyword in content → at least
    one ConflictGroup whose conflict_count >= conflict_thresh (10).
    """
    job = _make_job(conflict_thresh=10)
    # Keyword "error" appears in all 12 entries; they all share tag "system"
    records = [
        _make_record(content=f"error occurred case {i}", tags=["system"])
        for i in range(12)
    ]
    conflicts = job._detect_conflicts(records)
    assert len(conflicts) >= 1
    assert any(c.conflict_count >= 10 for c in conflicts)


def test_detect_conflicts_below_thresh():
    """5 entries with same keyword/tag but thresh=10 → no conflicts."""
    job = _make_job(conflict_thresh=10)
    records = [
        _make_record(content=f"error case {i}", tags=["system"])
        for i in range(5)
    ]
    conflicts = job._detect_conflicts(records)
    assert conflicts == []


def test_detect_conflicts_no_shared_tags():
    """Entries with different tags are never grouped regardless of content."""
    job = _make_job(conflict_thresh=2)
    records = [
        _make_record(content="same keyword text", tags=[f"unique_tag_{i}"])
        for i in range(5)
    ]
    # Because each entry has a unique tag, no tag group will have >= 2 entries
    conflicts = job._detect_conflicts(records)
    assert conflicts == []


# ---------------------------------------------------------------------------
# _resolve_conflict
# ---------------------------------------------------------------------------

def test_resolve_conflict_single_id():
    job = _make_job()
    group = ConflictGroup(concept_ids=["only-one"], conflict_count=1)
    assert job._resolve_conflict(group) == "keep_newest"


def test_resolve_conflict_multiple_ids():
    job = _make_job()
    group = ConflictGroup(concept_ids=["a", "b", "c"], conflict_count=3)
    assert job._resolve_conflict(group) == "merge"


def test_resolve_conflict_empty_ids():
    job = _make_job()
    group = ConflictGroup(concept_ids=[], conflict_count=0)
    assert job._resolve_conflict(group) == "discard"


# ---------------------------------------------------------------------------
# get_conflicts / resolve_conflict
# ---------------------------------------------------------------------------

def test_get_conflicts_excludes_resolved():
    """After resolve_conflict(), the resolved group no longer appears in get_conflicts()."""
    job = _make_job(conflict_thresh=1)

    # Inject two conflict groups directly
    group_a = ConflictGroup(concept_ids=["id-aaa", "id-bbb"], conflict_count=2)
    group_b = ConflictGroup(concept_ids=["id-ccc"], conflict_count=1)
    job._conflicts = [group_a, group_b]

    # Resolve group_a via its first concept_id
    resolved = job.resolve_conflict("id-aaa")
    assert resolved is True

    remaining = job.get_conflicts()
    ids_in_remaining = [g.concept_ids[0] for g in remaining if g.concept_ids]
    assert "id-aaa" not in ids_in_remaining
    assert "id-ccc" in ids_in_remaining


def test_resolve_conflict_unknown_id_returns_false():
    job = _make_job()
    job._conflicts = []
    assert job.resolve_conflict("nonexistent-id") is False
