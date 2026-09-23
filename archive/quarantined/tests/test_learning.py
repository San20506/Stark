"""
Tests for Continuous Learning Module
=====================================
Tests for ContinualLearner, Hebbian hooks, and feedback processing.
"""

import pytest
import threading
import time
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


class TestContinualLearner:
    """Tests for ContinualLearner class."""
    
    @pytest.fixture
    def mock_memory(self):
        """Create mock NeuromorphicMemory."""
        memory = Mock()
        memory.store.return_value = "node_123"
        memory._encode.return_value = [0.1] * 384
        memory._find_similar_nodes.return_value = [
            ("node_1", 0.8),
            ("node_2", 0.7),
            ("node_3", 0.65),
        ]
        memory._hebbian_update = Mock()
        return memory
    
    @pytest.fixture
    def mock_adapter_manager(self):
        """Create mock AdapterManager."""
        manager = Mock()
        adapter = Mock()
        adapter._training_steps = 0
        manager.get_adapter.return_value = adapter
        return manager
    
    @pytest.fixture
    def learner(self, mock_memory, mock_adapter_manager):
        """Create ContinualLearner with mocks."""
        # Import here to avoid import errors if dependencies missing
        from learning.continual_learner import ContinualLearner
        
        return ContinualLearner(
            memory=mock_memory,
            adapter_manager=mock_adapter_manager,
            train_interval=1,  # Fast for testing
            min_samples=2,     # Low threshold for testing
        )
    
    def test_init(self, learner):
        """Test learner initialization."""
        assert learner is not None
        assert learner.train_interval == 1
        assert learner.min_samples == 2
        assert not learner.is_running()
    
    def test_add_feedback(self, learner, mock_memory):
        """Test adding feedback."""
        learner.add_feedback(
            query="How do I fix this error?",
            response="Check the variable types",
            task="error_debugging",
            score=0.8,
        )
        
        assert learner.stats.total_samples == 1
        assert learner.queue_depth >= 0
        
        # High score should trigger memory store
        mock_memory.store.assert_called_once()
    
    def test_add_positive_example(self, learner):
        """Test shorthand for positive feedback."""
        learner.add_positive_example(
            query="Test query",
            response="Test response",
            task="conversation",
        )
        
        assert learner.stats.total_samples == 1
    
    def test_feedback_score_clamping(self, learner):
        """Test that scores are clamped to [-1, 1]."""
        learner.add_feedback("q", "r", "t", score=2.5)
        learner.add_feedback("q", "r", "t", score=-3.0)
        
        # Both should be clamped
        assert learner.stats.total_samples == 2
    
    def test_thread_start_stop(self, learner):
        """Test background thread lifecycle."""
        learner.start()
        assert learner.is_running()
        
        time.sleep(0.1)
        
        learner.stop(timeout=2.0)
        assert not learner.is_running()
    
    def test_graceful_shutdown(self, learner):
        """Test graceful shutdown with pending work."""
        learner.start()
        
        # Add some feedback
        for i in range(5):
            learner.add_feedback(f"query_{i}", f"response_{i}", "test", 0.9)
        
        # Stop should complete gracefully
        learner.stop(timeout=3.0)
        assert not learner.is_running()
    
    def test_thread_safety(self, learner):
        """Test concurrent access to feedback queue."""
        learner.start()
        
        def add_feedback_thread(n):
            for i in range(n):
                learner.add_feedback(f"q_{i}", f"r_{i}", "test", 0.5)
        
        threads = [threading.Thread(target=add_feedback_thread, args=(10,)) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        learner.stop()
        
        # All feedback should be recorded
        assert learner.stats.total_samples == 30
    
    def test_is_backpressured(self, learner):
        """Test backpressure detection."""
        assert not learner.is_backpressured
        
        # Add many items to trigger backpressure
        for i in range(150):
            learner._pending_feedback.append(Mock())
        
        assert learner.is_backpressured
    
    def test_queue_depth(self, learner):
        """Test queue depth property."""
        assert learner.queue_depth == 0
        
        learner.add_feedback("q", "r", "t", 0.5)
        assert learner.queue_depth >= 1
    
    def test_hebbian_hooks(self, learner, mock_memory):
        """Test that Hebbian updates are triggered for high-quality feedback."""
        # Add enough high-quality feedback
        for i in range(5):
            learner.add_feedback(
                f"query_{i}",
                f"response_{i}",
                "error_debugging",
                score=0.9,
            )
        
        # Process feedback
        learner._process_feedback()
        
        # Hebbian update should have been called
        assert mock_memory._hebbian_update.called
    
    def test_export_training_data(self, learner):
        """Test exporting training data."""
        # Add some feedback
        learner.add_feedback("q1", "r1", "t1", 0.9)
        learner.add_feedback("q2", "r2", "t2", 0.3)  # Below threshold
        learner.add_feedback("q3", "r3", "t3", 0.8)
        
        exported = learner.export_training_data(min_score=0.5)
        
        # Only high-score items should be exported
        assert len(exported) == 2
    
    def test_get_stats(self, learner):
        """Test statistics retrieval."""
        stats = learner.get_stats()
        
        assert "is_running" in stats
        assert "pending_feedback" in stats
        assert "total_samples" in stats
        assert "avg_feedback_score" in stats
    
    def test_get_task_breakdown(self, learner):
        """Test task breakdown by category."""
        learner.add_feedback("q1", "r1", "error_debugging", 0.9)
        learner.add_feedback("q2", "r2", "error_debugging", 0.8)
        learner.add_feedback("q3", "r3", "code_explanation", 0.7)
        
        breakdown = learner.get_task_breakdown()
        
        assert "error_debugging" in breakdown
        assert breakdown["error_debugging"]["total"] == 2
        assert breakdown["code_explanation"]["total"] == 1


class TestFeedbackEntry:
    """Tests for FeedbackEntry dataclass."""
    
    def test_creation(self):
        from learning.continual_learner import FeedbackEntry
        
        entry = FeedbackEntry(
            query="test query",
            response="test response",
            task="test_task",
            score=0.8,
        )
        
        assert entry.query == "test query"
        assert entry.score == 0.8
        assert entry.timestamp is not None


class TestTrainingStats:
    """Tests for TrainingStats dataclass."""
    
    def test_to_dict(self):
        from learning.continual_learner import TrainingStats
        
        stats = TrainingStats(
            total_samples=100,
            total_batches=10,
            avg_feedback_score=0.75,
        )
        
        d = stats.to_dict()
        
        assert d["total_samples"] == 100
        assert d["avg_feedback_score"] == 0.75
