"""
Tests for Neuromorphic Memory
"""

import pytest
import numpy as np
import time
from memory.memory_node import MemoryNode
from memory.neuromorphic_memory import NeuromorphicMemory


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
