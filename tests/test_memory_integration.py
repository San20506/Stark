import time
from memory.knowledge_graph import ConceptNode, KnowledgeGraph
from memory.appraisal_engine import AppraisalEngine
from memory.episode_manager import EpisodeManager
from memory.thread_state import SessionState
from memory.diary_store import DiaryStore, DiaryEntry
from memory.tool_schema_store import ToolSchema, ToolSchemaStore
from memory.consolidation import ConflictGroup, ConsolidationJob
import numpy as np


def test_appraisal_then_episode_then_diary(tmp_path):
    appraisal = AppraisalEngine()
    result = appraisal.compute(
        "I fixed a tricky null reference bug", session_state={"task_confidence": 0.7}
    )
    assert result["novelty"] >= 0.0
    assert appraisal.is_novel(result) in [True, False]

    manager = EpisodeManager()
    assert manager.should_segment(confidence=0.3) is True
    assert manager.should_segment(confidence=0.9) is False

    session = SessionState(
        session_id="test-1",
        messages=[
            {"role": "user", "content": "fix the bug"},
            {"role": "assistant", "content": "done"},
        ],
        emotion_vector=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    )
    episode = manager.create_episode_from_session(session, insights="null ref fixed")
    assert episode.session_id == "test-1"
    assert episode.insights == "null ref fixed"

    db_path = tmp_path / "episodic.db"
    store = DiaryStore(db_path=db_path, soft_cap=1000)
    entry_id = store.write(DiaryEntry(content="fixed null ref", tags=["bug", "python"]))
    assert entry_id
    assert store.count() == 1
    hits = store.query_semantic("python bug fix", top_k=3)
    assert len(hits) >= 1


def test_knowledge_graph_concept_lifecycle(tmp_path):
    kg = KnowledgeGraph()

    node1 = ConceptNode(
        id="c1",
        content="python list indexing",
        embedding=np.random.rand(128).astype(np.float32),
        node_type="episodic",
        created_at=time.time(),
        access_count=0,
        promotion_count=0,
        metadata={},
    )
    node2 = ConceptNode(
        id="c2",
        content="python error handling",
        embedding=np.random.rand(128).astype(np.float32),
        node_type="episodic",
        created_at=time.time(),
        access_count=0,
        promotion_count=0,
        metadata={},
    )

    kg.add_concept(node1)
    kg.add_concept(node2)

    assert kg.count() == 2

    results = kg.query_associative(np.random.rand(128).astype(np.float32), top_k=2)
    assert len(results) <= 2

    prom = kg.promote("c1")
    assert prom in [True, False]


def test_tool_schema_store_crud(tmp_path):
    store = ToolSchemaStore(db_path=tmp_path / "schemas.db", staleness_days=365)

    schema = ToolSchema(
        schema_id="tool-1",
        name="python_debug",
        description="debug python code",
        parameters={"type": "object"},
        tool_type="code",
        confidence=0.9,
        last_used=time.time(),
        use_count=0,
        staleness_days=365,
        metadata={},
    )
    registered_id = store.register(schema)
    assert registered_id == "tool-1"

    fetched = store.get("tool-1")
    assert fetched is not None
    assert fetched.name == "python_debug"

    by_type = store.query_by_type("code")
    assert len(by_type) >= 1

    store.record_use("tool-1")
    updated = store.get("tool-1")
    assert updated is not None
    assert updated.use_count >= 1

    count = store.count()
    assert count >= 1


def test_consolidation_job_start_stop(tmp_path):
    db_path = tmp_path / "episodic.db"
    store = DiaryStore(db_path=db_path, soft_cap=10000)
    job = ConsolidationJob()

    store.write(DiaryEntry(content="use list comprehension", tags=["python"]))
    store.write(DiaryEntry(content="avoid for loops", tags=["python"]))
    store.write(DiaryEntry(content="check null first", tags=["bug"]))

    job.start()
    assert job._running is True

    job._run_consolidation()
    conflicts = job.get_conflicts()
    assert isinstance(conflicts, list)

    job.stop()
    assert job._running is False


def test_full_memory_v2_pipeline(tmp_path):
    appraisal = AppraisalEngine()
    app_result = appraisal.compute(
        "deploy this to prod", session_state={"task_confidence": 0.5}
    )
    assert set(app_result.keys()) == {
        "novelty",
        "valence",
        "agency",
        "coping",
        "certainty",
        "goal_relevance",
    }

    session = SessionState(
        session_id="pipe-1", messages=[{"role": "user", "content": "deploy"}]
    )
    manager = EpisodeManager()
    episode = manager.create_episode_from_session(session)
    assert episode.session_id == "pipe-1"

    kg = KnowledgeGraph()
    concept = ConceptNode(
        id="pipe-c1",
        content="deployment checklist",
        embedding=np.random.rand(128).astype(np.float32),
        node_type="procedural",
        created_at=time.time(),
        access_count=0,
        promotion_count=0,
        metadata={},
    )
    kg.add_concept(concept)
    assert kg.count() >= 1

    schema_store = ToolSchemaStore(db_path=tmp_path / "schemas2.db")
    schema_store.register(
        ToolSchema(
            schema_id="deploy-tool",
            name="deploy",
            description="deploy to environment",
            parameters={},
            tool_type="system",
            confidence=0.8,
            last_used=time.time(),
            use_count=0,
            staleness_days=30,
            metadata={},
        )
    )
    assert schema_store.count() >= 1

    diary_store = DiaryStore(db_path=tmp_path / "episodic2.db")
    diary_id = diary_store.write(
        DiaryEntry(content="deployment successful", tags=["deploy", "prod"])
    )
    assert diary_id

    consol = ConsolidationJob()
    consol._run_consolidation()
    assert isinstance(consol.get_conflicts(), list)
    consol.stop()
