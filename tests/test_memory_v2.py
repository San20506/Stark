import time
import numpy as np
from memory.appraisal_engine import AppraisalEngine
from memory.episode_manager import EpisodeManager
from memory.activation_scorer import ActivationScorer
from memory.knowledge_graph import ConceptNode, KnowledgeGraph
from memory.diary_store import DiaryEntry, DiaryStore
from memory.reflection_loop import ReflectionLoop, ReflectionResult
from memory.consolidation import ConflictGroup, ConsolidationJob
from memory.tool_schema_store import ToolSchema, ToolSchemaStore
from memory.thread_state import SessionState, ThreadStateManager


class TestAppraisalEngine:
    def test_returns_six_dimensions(self):
        engine = AppraisalEngine()
        result = engine.compute("deploy to production server")
        assert set(result.keys()) == {
            "novelty",
            "valence",
            "agency",
            "coping",
            "certainty",
            "goal_relevance",
        }
        assert all(0.0 <= v <= 1.0 for v in result.values())

    def test_smoothing_stabilises(self):
        engine = AppraisalEngine(smoothing_window=3)
        first = engine.compute("error error failed")
        second = engine.compute("great success fixed")
        third = engine.compute("great success fixed")
        assert third["valence"] >= first["valence"]

    def test_session_state_signals(self):
        engine = AppraisalEngine()
        result = engine.compute(
            "help me debug",
            session_state={
                "task_complexity": 0.9,
                "rolling_success_rate": 0.4,
                "task_scores": {"error_debugging": 0.8, "conversation": 0.2},
            },
        )
        assert result["coping"] <= 0.2
        assert result["certainty"] > 0.0

    def test_novel_detection(self):
        engine = AppraisalEngine()
        result = engine.compute("alpha beta gamma delta epsilon zeta")
        assert isinstance(engine.is_novel(result), bool)


class TestEpisodeManager:
    def test_surprise_segmentation(self):
        manager = EpisodeManager(surprise_threshold=0.5)
        assert manager.should_segment(confidence=0.1) is True
        assert manager.should_segment(confidence=0.9) is False

    def test_session_to_episode(self):
        manager = EpisodeManager()
        session = SessionState(
            session_id="s1",
            messages=[
                {"role": "user", "content": "how to sort a list"},
                {"role": "assistant", "content": "use sorted()"},
            ],
            active_tool_schemas=["python_repl"],
        )
        ep = manager.create_episode_from_session(
            session, insights="sorted() is the answer"
        )
        assert ep.session_id == "s1"
        assert ep.insights == "sorted() is the answer"


class TestActivationScorer:
    def test_decay_over_time(self):
        scorer = ActivationScorer(decay_rate=0.5)
        early = scorer.compute_base_level([1000.0, 2000.0], current_time=2001.0)
        late = scorer.compute_base_level([1000.0, 2000.0], current_time=2010.0)
        assert late < early

    def test_frequency_boosts_activation(self):
        scorer = ActivationScorer(decay_rate=0.5)
        now = 1201.0
        low = scorer.compute_base_level([1200.0], current_time=now)
        high = scorer.compute_base_level([1100.0, 1150.0, 1200.0], current_time=now)
        assert high > low

    def test_retrieval_score_determinism(self):
        scorer = ActivationScorer(noise_std=0.0)
        s1 = scorer.compute_retrieval_score(
            base_activation=2.0, semantic_similarity=0.1
        )
        s2 = scorer.compute_retrieval_score(
            base_activation=0.1, semantic_similarity=0.9
        )
        assert s1 != s2

    def test_memory_ranking(self):
        scorer = ActivationScorer(noise_std=0.0)
        query = np.array([1.0, 0.0, 0.0, 0.0] * 32)
        candidates = [
            {
                "id": "high",
                "access_times": [1000.0],
                "embedding": np.array([1.0, 0.0, 0.0, 0.0] * 32),
            },
            {
                "id": "low",
                "access_times": [1000.0],
                "embedding": np.array([0.0, 1.0, 0.0, 0.0] * 32),
            },
        ]
        ranked = scorer.rank_memories(candidates, query, current_time=1100.0)
        assert ranked[0][0] == "high"


class TestKnowledgeGraph:
    def test_concept_add_and_retrieve(self):
        kg = KnowledgeGraph()
        node = ConceptNode(
            id="c1",
            content="python decorators",
            embedding=np.random.rand(128).astype(np.float32),
            node_type="episodic",
            created_at=time.time(),
            access_count=0,
            promotion_count=0,
            metadata={},
        )
        kg.add_concept(node)
        assert kg.count() == 1

    def test_similarity_links_created(self):
        kg = KnowledgeGraph()
        embed = np.random.rand(128).astype(np.float32)
        n1 = ConceptNode(
            "n1", "python list", embed.copy(), "episodic", time.time(), 0, 0, {}
        )
        n2 = ConceptNode(
            "n2", "python dict", embed.copy(), "episodic", time.time(), 0, 0, {}
        )
        kg.add_concept(n1)
        kg.add_concept(n2)
        assert kg.count() == 2

    def test_promotion_criteria(self):
        kg = KnowledgeGraph()
        embed = np.random.rand(128).astype(np.float32)
        node = ConceptNode(
            "p1", "debug", embed.copy(), "episodic", time.time(), 5, 3, {}
        )
        kg.add_concept(node)
        result = kg.promote("p1")
        assert isinstance(result, bool)

    def test_query_associative(self):
        kg = KnowledgeGraph()
        embed = np.random.rand(128).astype(np.float32)
        for i in range(3):
            node = ConceptNode(
                f"q{i}", f"content {i}", embed.copy(), "episodic", time.time(), 0, 0, {}
            )
            kg.add_concept(node)
        results = kg.query_associative(embed, top_k=3)
        assert len(results) <= 3


class TestDiaryStore:
    def test_write_and_semantic_query(self, tmp_path):
        db = tmp_path / "d.db"
        store = DiaryStore(db_path=db, soft_cap=1000)
        store.write(
            DiaryEntry(content="fix null pointer error", tags=["bug", "python"])
        )
        store.write(DiaryEntry(content="weekly planning", tags=["planning"]))
        hits = store.query_semantic("python null fix", top_k=2)
        assert len(hits) >= 1

    def test_timerange_query(self, tmp_path):
        db = tmp_path / "t.db"
        store = DiaryStore(db_path=db, soft_cap=1000)
        id1 = store.write(DiaryEntry(content="e1", timestamp=1000.0, tags=["a"]))
        id2 = store.write(DiaryEntry(content="e2", timestamp=2000.0, tags=["b"]))
        hits = store.query_timerange(900.0, 1500.0)
        assert len(hits) == 1
        assert hits[0].id == id1

    def test_tag_query(self, tmp_path):
        db = tmp_path / "g.db"
        store = DiaryStore(db_path=db, soft_cap=1000)
        id1 = store.write(DiaryEntry(content="e1", tags=["x"]))
        id2 = store.write(DiaryEntry(content="e2", tags=["y"]))
        hits = store.query_tags(["y"])
        assert len(hits) == 1
        assert hits[0].id == id2

    def test_emotion_query(self, tmp_path):
        db = tmp_path / "em.db"
        store = DiaryStore(db_path=db, soft_cap=1000)
        store.write(DiaryEntry(content="e1", emotion_vector=[0.1, 0.2]))
        store.write(DiaryEntry(content="e2", emotion_vector=[0.9, 0.9]))
        hits = store.query_emotion({0: (0.85, 1.0), 1: (0.85, 1.0)})
        assert len(hits) == 1

    def test_soft_cap_archives(self, tmp_path):
        db = tmp_path / "cap.db"
        arc = tmp_path / "arc.jsonl"
        store = DiaryStore(db_path=db, soft_cap=2, archive_path=arc)
        for i in range(4):
            store.write(DiaryEntry(content=f"e{i}", timestamp=float(1000 + i)))
        assert store.count() == 2
        assert arc.exists()


class TestReflectionLoop:
    def test_result_dataclass_fields(self):
        result = ReflectionResult(
            insights=["insight1"], summary="summary", triggered_at=time.time()
        )
        assert result.insights == ["insight1"]
        assert result.summary == "summary"

    def test_trigger_returns_none_without_ollama(self, tmp_path):
        loop = ReflectionLoop()
        session = SessionState(
            session_id="s1", messages=[{"role": "user", "content": "test"}]
        )
        result = loop.trigger(session)
        assert result is None


class TestConsolidationJob:
    def test_start_stop(self, tmp_path):
        db = tmp_path / "con.db"
        DiaryStore(db_path=db, soft_cap=10000)
        job = ConsolidationJob()
        job.start()
        assert job._running is True
        job.stop()
        assert job._running is False

    def test_detect_conflicts_returns_list(self, tmp_path):
        db = tmp_path / "dc.db"
        store = DiaryStore(db_path=db, soft_cap=10000)
        store.write(DiaryEntry(content="use list comprehension", tags=["python"]))
        store.write(DiaryEntry(content="avoid for loops", tags=["python"]))
        store.write(DiaryEntry(content="check null first", tags=["bug"]))
        job = ConsolidationJob()
        conflicts = job.get_conflicts()
        assert isinstance(conflicts, list)


class TestToolSchemaStore:
    def test_register_and_retrieve(self, tmp_path):
        db = tmp_path / "sc.db"
        store = ToolSchemaStore(db_path=db, staleness_days=365)
        schema = ToolSchema(
            schema_id="s1",
            name="python_debug",
            description="debug python",
            parameters={},
            tool_type="code",
            confidence=0.9,
            last_used=time.time(),
            use_count=0,
            staleness_days=365,
            metadata={},
        )
        store.register(schema)
        fetched = store.get("s1")
        assert fetched is not None
        assert fetched.name == "python_debug"

    def test_query_by_type(self, tmp_path):
        db = tmp_path / "qt.db"
        store = ToolSchemaStore(db_path=db, staleness_days=365)
        store.register(
            ToolSchema("t1", "debug", "", {}, "code", 0.8, time.time(), 0, 365, {})
        )
        store.register(
            ToolSchema("t2", "plan", "", {}, "planning", 0.7, time.time(), 0, 365, {})
        )
        results = store.query_by_type("code")
        assert len(results) >= 1

    def test_record_use_increments(self, tmp_path):
        db = tmp_path / "ru.db"
        store = ToolSchemaStore(db_path=db, staleness_days=365)
        store.register(
            ToolSchema("r1", "test", "", {}, "test", 0.8, time.time(), 0, 365, {})
        )
        store.record_use("r1")
        updated = store.get("r1")
        assert updated.use_count >= 1

    def test_weighted_query(self, tmp_path):
        db = tmp_path / "wq.db"
        store = ToolSchemaStore(db_path=db, staleness_days=365)
        store.register(
            ToolSchema(
                "w1", "python debugging", "", {}, "code", 0.9, time.time(), 1, 30, {}
            )
        )
        store.register(
            ToolSchema(
                "w2", "task planning", "", {}, "planning", 0.6, time.time(), 0, 30, {}
            )
        )
        results = store.query_weighted("python debugging", top_k=2)
        assert len(results) >= 1

    def test_count(self, tmp_path):
        db = tmp_path / "ct.db"
        store = ToolSchemaStore(db_path=db, staleness_days=365)
        store.register(ToolSchema("c1", "a", "", {}, "t", 0.5, time.time(), 0, 365, {}))
        store.register(ToolSchema("c2", "b", "", {}, "t", 0.5, time.time(), 0, 365, {}))
        assert store.count() >= 2


class TestThreadStateManager:
    def test_new_and_reload(self, tmp_path):
        mgr = ThreadStateManager(sessions_dir=tmp_path)
        state = mgr.new_session()
        mgr.update(state.session_id, "q1", "r1")
        reloaded = mgr.load_session(state.session_id)
        assert reloaded.session_id == state.session_id
        assert len(reloaded.messages) == 2

    def test_missing_session_starts_fresh(self, tmp_path):
        mgr = ThreadStateManager(sessions_dir=tmp_path)
        state = mgr.load_session("does-not-exist")
        assert state.session_id == "does-not-exist"
        assert state.messages == []

    def test_idle_end_detection(self, tmp_path):
        mgr = ThreadStateManager(sessions_dir=tmp_path)
        state = mgr.new_session()
        assert mgr.is_conversation_ended(state.session_id, idle_seconds=300) is False
        assert mgr.is_conversation_ended(state.session_id, idle_seconds=0) is True


class TestMemoryV2Integration:
    def test_full_pipeline(self, tmp_path):
        engine = AppraisalEngine()
        result = engine.compute(
            "deploy to prod", session_state={"task_confidence": 0.6}
        )
        assert set(result.keys()) == {
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
        ep = manager.create_episode_from_session(session)
        assert ep.session_id == "pipe-1"

        kg = KnowledgeGraph()
        concept = ConceptNode(
            "pc1",
            "deployment checklist",
            np.random.rand(128).astype(np.float32),
            "procedural",
            time.time(),
            0,
            0,
            {},
        )
        kg.add_concept(concept)
        assert kg.count() >= 1

        schemas = ToolSchemaStore(db_path=tmp_path / "sc2.db")
        schemas.register(
            ToolSchema(
                "deploy",
                "deploy",
                "deploy to env",
                {},
                "system",
                0.8,
                time.time(),
                0,
                30,
                {},
            )
        )
        assert schemas.count() >= 1

        diary = DiaryStore(db_path=tmp_path / "d2.db")
        diary.write(DiaryEntry(content="deployment successful", tags=["deploy"]))
        assert diary.count() >= 1

        consol = ConsolidationJob()
        consol._run_consolidation()
        assert isinstance(consol.get_conflicts(), list)
        consol.stop()
