"""
Tests for Neuromorphic Memory
"""

import pytest
import numpy as np
import time
from memory.memory_node import MemoryNode
from memory.neuromorphic_memory import NeuromorphicMemory
import memory.neuromorphic_memory as nm_mod


class TestMemoryNode:
    """Tests for MemoryNode dataclass."""
    
    def test_create_node(self):
        """Test basic node creation."""
        embedding = np.random.rand(384)
        node = MemoryNode(
            query="test query",
            response="test response",
            task="error_debugging",
            embedding=embedding
        )
        
        assert node.query == "test query"
        assert node.task == "error_debugging"
        assert node.activation == 1.0
        assert len(node.node_id) == 8
    
    def test_activate(self):
        """Test activation increases."""
        node = MemoryNode(
            query="q", response="r", task="t",
            embedding=np.random.rand(384)
        )
        node.activation = 0.5
        
        new_activation = node.activate(amount=0.3)
        
        assert new_activation == 0.8
        assert node.access_count == 1
    
    def test_decay(self):
        """Test activation decay."""
        node = MemoryNode(
            query="q", response="r", task="t",
            embedding=np.random.rand(384)
        )
        node.decay_rate = 0.1
        
        new_activation = node.decay(hours_elapsed=2.0)
        
        assert new_activation == 0.8  # 1.0 - (0.1 * 2)
    
    def test_connections(self):
        """Test adding connections."""
        node = MemoryNode(
            query="q", response="r", task="t",
            embedding=np.random.rand(384)
        )
        
        node.add_connection("node_2", 0.8)
        
        assert "node_2" in node.connections
        assert node.connections["node_2"] == 0.8
    
    def test_similarity(self):
        """Test cosine similarity."""
        emb1 = np.array([1, 0, 0])
        emb2 = np.array([1, 0, 0])
        emb3 = np.array([0, 1, 0])
        
        node = MemoryNode(
            query="q", response="r", task="t",
            embedding=emb1
        )
        
        assert node.similarity(emb2) == pytest.approx(1.0)
        assert node.similarity(emb3) == pytest.approx(0.0)
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        node = MemoryNode(
            query="test", response="resp", task="task",
            embedding=np.array([1.0, 2.0, 3.0])
        )
        node.add_connection("other", 0.5)
        
        data = node.to_dict()
        restored = MemoryNode.from_dict(data)
        
        assert restored.query == node.query
        assert restored.task == node.task
        assert "other" in restored.connections


class TestNeuromorphicMemory:
    """Tests for NeuromorphicMemory class."""
    
    @pytest.fixture
    def memory(self):
        """Create fresh memory instance."""
        return NeuromorphicMemory(lazy_load=False)
    
    def test_store_and_recall(self, memory):
        """Test basic store and recall."""
        # Store a memory
        node_id = memory.store(
            query="How to fix IndexError?",
            response="Check list bounds before accessing",
            task="error_debugging"
        )
        
        assert node_id is not None
        assert len(memory) == 2  # 1 node + 1 task hub
        
        # Recall it
        results = memory.recall("index out of bounds error", top_k=5)
        
        assert len(results) > 0
        assert results[0][0].query == "How to fix IndexError?"
    
    def test_task_indexing(self, memory):
        """Test task-based retrieval."""
        memory.store("q1", "r1", "error_debugging")
        memory.store("q2", "r2", "task_planning")
        memory.store("q3", "r3", "error_debugging")
        
        debug_memories = memory.recall_by_task("error_debugging")
        
        assert len(debug_memories) == 2
    
    def test_connection_formation(self, memory):
        """Test that similar memories form connections."""
        memory.store("Python null pointer", "Check for None", "error_debugging")
        memory.store("Python None error", "Handle null values", "error_debugging")
        
        # Get nodes (excluding hub)
        nodes = [n for n in memory.nodes.values() if n.decay_rate > 0]
        
        # Should have connections between similar memories
        has_connection = any(len(n.connections) > 0 for n in nodes)
        assert has_connection
    
    def test_stats(self, memory):
        """Test statistics tracking."""
        memory.store("q1", "r1", "error_debugging")
        memory.recall("test query")
        
        stats = memory.get_stats()
        
        assert stats["stores"] == 1
        assert stats["recalls"] == 1
        assert stats["total_nodes"] > 0


def _unit_vec(idx):
    """Return a 384-dim unit vector (matches hub embedding dims)."""
    vec = np.zeros(384)
    vec[idx] = 1.0
    return vec


def _make_memory(vectors=None):
    """Build a memory with stubbed encoder and diary (no network calls)."""
    mem = NeuromorphicMemory()
    if vectors is None:
        mem._encode = lambda text: _unit_vec(0)
    else:
        it = iter(vectors)
        mem._encode = lambda text: next(it)
    mem.diary_store.write = lambda entry: "fake-diary-id"
    return mem


def _make_node(query="q", task="t", activation=1.0, decay_rate=0.05, vec=None):
    """Build a standalone MemoryNode without touching the encoder."""
    return MemoryNode(
        query=query,
        response="r",
        task=task,
        embedding=vec if vec is not None else np.array([1.0, 0.0, 0.0]),
        activation=activation,
        decay_rate=decay_rate,
    )


class TestStoreClustering:
    """Cover store() task clustering, hub reuse, and diary failure paths."""

    def test_store_reuses_task_hub(self):
        mem = _make_memory()
        mem.store("q1", "r1", "clustering_task")
        hub_id = mem.task_hubs["clustering_task"]
        mem.store("q2", "r2", "clustering_task")
        assert mem.task_hubs["clustering_task"] == hub_id
        assert len(mem.task_hubs) == 1

    def test_store_second_task_creates_second_hub(self):
        mem = _make_memory()
        mem.store("q1", "r1", "task_a")
        mem.store("q2", "r2", "task_b")
        assert len(mem.task_hubs) == 2
        assert mem.task_hubs["task_a"] != mem.task_hubs["task_b"]

    def test_store_diary_failure_still_returns_id(self):
        mem = _make_memory()

        def _boom(entry):
            raise RuntimeError("diary down")

        mem.diary_store.write = _boom
        node_id = mem.store("q", "r", "diary_task")
        assert node_id is not None
        assert node_id in mem.nodes

    def test_store_with_metadata(self):
        mem = _make_memory()
        node_id = mem.store("q", "r", "meta_task", metadata={"source": "test"})
        assert mem.nodes[node_id].metadata["source"] == "test"


class TestRecallEdgeCases:
    """Cover recall()/recall_v2() ranking, empty-store and no-match paths."""

    def test_recall_empty_store_returns_empty(self):
        assert _make_memory().recall("anything") == []

    def test_recall_v2_empty_store_returns_empty(self):
        assert _make_memory().recall_v2("anything") == []

    def test_recall_v2_unknown_task_returns_empty(self):
        mem = _make_memory()
        mem.store("q", "r", "some_task")
        assert mem.recall_v2("q", task="missing_task") == []

    def test_recall_v2_all_dead_returns_empty(self):
        mem = _make_memory()
        mem.store("q", "r", "some_task")
        for node in mem.nodes.values():
            node.activation = 0.0
        assert mem.recall_v2("q") == []

    def test_recall_v2_ranking_orders_by_similarity(self):
        mem = _make_memory(vectors=[_unit_vec(0), _unit_vec(1), _unit_vec(0)])
        mem.store("alpha query", "ra", "rank_task")
        mem.store("beta query", "rb", "rank_task")
        mem.scorer.s = 0  # disable ACT-R noise for deterministic ranking
        results = mem.recall_v2("alpha query")
        assert len(results) == 3  # 2 nodes + 1 task hub
        assert results[0][0].query == "alpha query"

    def test_recall_v2_recreates_missing_scorer(self):
        mem = _make_memory()
        mem.store("q", "r", "scorer_task")
        del mem.scorer
        results = mem.recall_v2("q")
        assert len(results) > 0
        assert mem.scorer is not None

    def test_recall_v2_respects_top_k(self):
        mem = _make_memory()
        mem.store("q1", "r1", "topk_task")
        mem.store("q2", "r2", "topk_task")
        assert len(mem.recall_v2("q1", top_k=1)) == 1

    def test_recall_delegates_to_v2_when_flag_enabled(self, monkeypatch):
        mem = _make_memory()
        mem.store("q", "r", "flag_task")
        monkeypatch.setattr(nm_mod, "MEMORY_V2_ENABLED", True)
        results = mem.recall("q", top_k=1)
        assert len(results) == 1


class TestDecayAndGC:
    """Cover activation decay, GC triggers, and node removal paths."""

    def test_apply_decay_reduces_activation_over_time(self):
        mem = _make_memory()
        node = _make_node()
        node.activation = 1.0
        node.decay_rate = 0.1
        hub = _make_node(query="[TASK_HUB:t]", decay_rate=0.0)
        mem.nodes = {node.node_id: node, hub.node_id: hub}
        mem._last_decay = time.time() - 3600
        mem._apply_decay()
        assert node.activation == pytest.approx(0.9, abs=0.01)
        assert hub.activation == 1.0

    def test_apply_decay_skips_when_recent(self):
        mem = _make_memory()
        node = _make_node()
        mem.nodes = {node.node_id: node}
        mem._apply_decay()
        assert node.activation == 1.0

    def test_maybe_gc_skips_when_recent(self):
        mem = _make_memory()
        mem.store("q", "r", "gc_task")
        mem._maybe_gc()
        assert mem.get_stats()["gc_runs"] == 0

    def test_maybe_gc_skips_when_under_capacity(self, monkeypatch):
        mem = _make_memory()
        mem.store("q", "r", "gc_task")
        monkeypatch.setattr(nm_mod, "GC_INTERVAL_SECONDS", 0)
        mem._last_gc = time.time() - 10000
        mem._maybe_gc()
        assert mem.get_stats()["gc_runs"] == 0

    def test_maybe_gc_runs_when_over_capacity(self, monkeypatch):
        mem = _make_memory()
        mem.store("q", "r", "gc_task")
        monkeypatch.setattr(nm_mod, "GC_INTERVAL_SECONDS", 0)
        monkeypatch.setattr(nm_mod, "MEMORY_MAX_NODES", 1)
        mem._last_gc = time.time() - 10000
        mem._maybe_gc()
        assert mem.get_stats()["gc_runs"] == 1

    def test_run_gc_removes_dead_nodes(self):
        mem = _make_memory()
        dead1 = _make_node(query="d1", activation=0.0)
        dead2 = _make_node(query="d2", activation=0.0)
        alive = _make_node(query="a1", activation=0.9)
        hub = _make_node(query="[TASK_HUB:t]", decay_rate=0.0)
        mem.nodes = {n.node_id: n for n in (dead1, dead2, alive, hub)}
        mem._task_index = {"t": [dead1.node_id, dead2.node_id, alive.node_id]}
        alive.add_connection(dead1.node_id, 0.8)
        mem._run_gc()
        assert dead1.node_id not in mem.nodes
        assert dead2.node_id not in mem.nodes
        assert alive.node_id in mem.nodes and hub.node_id in mem.nodes
        assert dead1.node_id not in mem._task_index["t"]
        assert dead1.node_id not in alive.connections
        assert mem.get_stats()["pruned_nodes"] == 2

    def test_run_gc_respects_batch_size(self, monkeypatch):
        monkeypatch.setattr(nm_mod, "GC_BATCH_SIZE", 1)
        mem = _make_memory()
        dead = [_make_node(query=f"d{i}", activation=0.0) for i in range(3)]
        mem.nodes = {n.node_id: n for n in dead}
        mem._task_index = {"t": [n.node_id for n in dead]}
        mem._run_gc()
        assert mem.get_stats()["pruned_nodes"] == 1
        assert len(mem.nodes) == 2

    def test_remove_node_missing_is_noop(self):
        _make_memory()._remove_node("ghost-id")  # must not raise

    def test_remove_node_handles_stale_task_index(self):
        mem = _make_memory()
        node = _make_node(task="stale_task")
        mem.nodes = {node.node_id: node}
        mem._task_index = {"stale_task": []}  # stale index triggers ValueError path
        mem._remove_node(node.node_id)
        assert node.node_id not in mem.nodes


class TestHebbianAndSpread:
    """Cover Hebbian strengthening and activation spreading branches."""

    def test_hebbian_strengthens_coactivated_connection(self):
        mem = _make_memory()
        node_a = _make_node(query="a")
        node_b = _make_node(query="b", vec=np.array([0.0, 1.0, 0.0]))
        node_a.add_connection(node_b.node_id, 0.5)
        mem.nodes = {node_a.node_id: node_a, node_b.node_id: node_b}
        before = node_a.connections[node_b.node_id]
        mem._hebbian_update([node_a.node_id, node_b.node_id])
        assert node_a.connections[node_b.node_id] == pytest.approx(before + 0.1)

    def test_hebbian_ignores_missing_nodes(self):
        mem = _make_memory()
        node = _make_node()
        mem.nodes = {node.node_id: node}
        mem._hebbian_update(["ghost-id", node.node_id])  # must not raise

    def test_hebbian_leaves_unconnected_pairs_alone(self):
        mem = _make_memory()
        node_a = _make_node(query="a")
        node_b = _make_node(query="b")
        mem.nodes = {node_a.node_id: node_a, node_b.node_id: node_b}
        mem._hebbian_update([node_a.node_id, node_b.node_id])
        assert node_b.node_id not in node_a.connections

    def test_spread_skips_dangling_connection_targets(self):
        mem = _make_memory()
        node = _make_node()
        node.add_connection("ghost-id", 0.9)
        mem.nodes = {node.node_id: node}
        query_vec = np.array([1.0, 0.0, 0.0])
        activated = mem._activate_and_spread([(node.node_id, 0.9)], query_vec)
        assert "ghost-id" not in activated
        assert activated[node.node_id] == pytest.approx(0.9)

    def test_spread_reaches_connected_neighbors(self):
        mem = _make_memory()
        vec_a = np.array([1.0, 0.0, 0.0])
        node_a = _make_node(query="a", vec=vec_a)
        node_b = _make_node(query="b", vec=vec_a)
        node_a.add_connection(node_b.node_id, 0.8)
        mem.nodes = {node_a.node_id: node_a, node_b.node_id: node_b}
        activated = mem._activate_and_spread([(node_a.node_id, 0.9)], vec_a)
        assert node_b.node_id in activated
        assert node_b.access_count >= 1


class TestPersistence:
    """Cover save/load roundtrip, missing/corrupt files, and singleton."""

    def test_save_load_roundtrip(self, tmp_path):
        mem = _make_memory()
        mem.store("q1", "r1", "persist_task")
        mem.store("q2", "r2", "persist_task")
        save_path = tmp_path / "memory.json"
        mem.save(save_path)
        assert save_path.exists()
        restored = NeuromorphicMemory()
        assert restored.load(save_path) is True
        assert len(restored.nodes) == len(mem.nodes)
        assert restored.task_hubs == mem.task_hubs
        for nid in mem._task_index["persist_task"]:
            assert nid in restored._task_index["persist_task"]

    def test_load_missing_file_returns_false(self, tmp_path):
        assert _make_memory().load(tmp_path / "nope.json") is False

    def test_load_corrupt_file_returns_false(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not valid json {{{")
        assert _make_memory().load(bad) is False

    def test_repr(self):
        assert "NeuromorphicMemory" in repr(_make_memory())

    def test_get_memory_singleton(self, monkeypatch):
        monkeypatch.setattr(NeuromorphicMemory, "load", lambda self, path=None: True)
        nm_mod._memory_instance = None
        try:
            first = nm_mod.get_memory()
            assert nm_mod.get_memory() is first
        finally:
            nm_mod._memory_instance = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
