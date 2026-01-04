"""
Tests for Utilities Module
===========================
Tests for logging, checkpointing, metrics, and profiling.
"""

import pytest
import json
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


class TestSTARKLogger:
    """Tests for STARKLogger class."""
    
    def test_setup_logging(self):
        """Test logging setup."""
        from utils.logger import setup_logging, STARKLogger
        
        # Reset for test
        STARKLogger._initialized = False
        
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(
                log_level="DEBUG",
                log_dir=Path(tmpdir),
                log_to_file=True,
            )
            
            assert STARKLogger._initialized is True
    
    def test_get_logger(self):
        """Test getting a logger."""
        from utils.logger import get_logger
        
        logger = get_logger("test_module")
        
        assert logger is not None
        assert logger.name == "test_module"
    
    def test_log_levels(self):
        """Test different log levels work."""
        from utils.logger import get_logger
        import logging
        
        logger = get_logger("test")
        
        # These should not raise exceptions
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")


class TestCheckpointManager:
    """Tests for CheckpointManager class."""
    
    @pytest.fixture
    def checkpoint_manager(self, tmp_path):
        """Create CheckpointManager with temp directory."""
        from utils.checkpoint import CheckpointManager
        return CheckpointManager(checkpoint_dir=tmp_path, max_checkpoints=3)
    
    def test_save_checkpoint(self, checkpoint_manager):
        """Test saving a checkpoint."""
        state = {"adapters": {"task1": [1, 2, 3]}, "step": 100}
        
        path = checkpoint_manager.save(state, name="test_ckpt")
        
        assert path.exists()
        assert path.name == "test_ckpt.json"
    
    def test_atomic_save(self, checkpoint_manager, tmp_path):
        """Test atomic save (no temp files left)."""
        state = {"data": "test"}
        
        checkpoint_manager.save(state, name="atomic_test")
        
        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0
    
    def test_load_checkpoint(self, checkpoint_manager):
        """Test loading a checkpoint."""
        original = {"key": "value", "number": 42}
        checkpoint_manager.save(original, name="load_test")
        
        loaded = checkpoint_manager.load(name="load_test")
        
        assert loaded["key"] == "value"
        assert loaded["number"] == 42
    
    def test_load_latest(self, checkpoint_manager):
        """Test loading latest checkpoint."""
        checkpoint_manager.save({"version": 1})
        time.sleep(0.01)
        checkpoint_manager.save({"version": 2})
        
        latest = checkpoint_manager.load_latest()
        
        assert latest["version"] == 2
    
    def test_checkpoint_pruning(self, checkpoint_manager):
        """Test old checkpoints are pruned."""
        # Save more than max_checkpoints
        for i in range(5):
            checkpoint_manager.save({"step": i}, name=f"ckpt_{i}")
            time.sleep(0.01)
        
        checkpoints = checkpoint_manager.list_checkpoints()
        
        # Should only keep max_checkpoints (3)
        assert len(checkpoints) <= 3
    
    def test_checkpoint_metadata(self, checkpoint_manager):
        """Test checkpoint includes metadata."""
        checkpoint_manager.save({"data": "test"}, name="meta_test")
        
        loaded = checkpoint_manager.load(name="meta_test")
        
        assert "_metadata" in loaded
        assert "timestamp" in loaded["_metadata"]
        assert "version" in loaded["_metadata"]
    
    def test_list_checkpoints(self, checkpoint_manager):
        """Test listing checkpoints."""
        checkpoint_manager.save({"v": 1})
        checkpoint_manager.save({"v": 2})
        
        checkpoints = checkpoint_manager.list_checkpoints()
        
        assert len(checkpoints) >= 2
        assert all("name" in c for c in checkpoints)
        assert all("size_kb" in c for c in checkpoints)


class TestMetricsLogger:
    """Tests for MetricsLogger class."""
    
    @pytest.fixture
    def metrics_logger(self, tmp_path):
        """Create MetricsLogger with temp directory."""
        from utils.metrics import MetricsLogger
        return MetricsLogger(log_dir=tmp_path, run_name="test_run")
    
    def test_log_memory_stats(self, metrics_logger):
        """Test logging memory stats."""
        stats = {
            "total_nodes": 1000,
            "alive_nodes": 950,
            "total_connections": 5000,
            "stores": 500,
            "recalls": 200,
        }
        
        # Should not raise
        metrics_logger.log_memory_stats(stats)
    
    def test_log_learning_stats(self, metrics_logger):
        """Test logging learning stats."""
        stats = {
            "total_samples": 100,
            "total_batches": 10,
            "avg_feedback_score": 0.75,
            "pending_feedback": 5,
        }
        
        metrics_logger.log_learning_stats(stats)
    
    def test_log_detection_stats(self, metrics_logger):
        """Test logging detection stats."""
        stats = {
            "total_detections": 500,
            "emergent_count": 25,
            "task_counts": {"error_debugging": 100, "code_explanation": 80},
        }
        
        metrics_logger.log_detection_stats(stats)
    
    def test_log_inference(self, metrics_logger):
        """Test logging inference metrics."""
        metrics_logger.log_inference(
            latency_ms=45.5,
            task="error_debugging",
            confidence=0.85,
            is_emergent=False,
        )
        
        # Step should increment
        assert metrics_logger.current_step > 0
    
    def test_step_increment(self, metrics_logger):
        """Test step counter."""
        initial = metrics_logger.current_step
        
        metrics_logger.step()
        metrics_logger.step()
        
        assert metrics_logger.current_step == initial + 2


class TestProfiler:
    """Tests for Profiler class."""
    
    @pytest.fixture
    def profiler(self):
        """Create Profiler instance."""
        from utils.profiler import Profiler
        return Profiler()
    
    def test_measure_context_manager(self, profiler):
        """Test timing with context manager."""
        with profiler.measure("test_operation"):
            time.sleep(0.01)
        
        stats = profiler.get_stats()
        assert "test_operation" in stats["timings"]
        assert stats["timings"]["test_operation"]["count"] == 1
        assert stats["timings"]["test_operation"]["avg_ms"] > 0
    
    def test_measure_decorator(self, profiler):
        """Test timing with decorator."""
        @profiler.profile
        def slow_function():
            time.sleep(0.01)
            return "done"
        
        result = slow_function()
        
        assert result == "done"
        stats = profiler.get_stats()
        assert "slow_function" in stats["timings"]
    
    def test_start_stop_timer(self, profiler):
        """Test manual timer start/stop."""
        profiler.start("manual_timer")
        time.sleep(0.01)
        duration = profiler.stop("manual_timer")
        
        assert duration > 0
        stats = profiler.get_stats()
        assert "manual_timer" in stats["timings"]
    
    def test_get_bottlenecks(self, profiler):
        """Test bottleneck identification."""
        # Create operations with different durations
        with profiler.measure("fast_op"):
            time.sleep(0.001)
        
        with profiler.measure("slow_op"):
            time.sleep(0.02)
        
        with profiler.measure("medium_op"):
            time.sleep(0.01)
        
        bottlenecks = profiler.get_bottlenecks(top_k=2)
        
        assert len(bottlenecks) == 2
        # Slowest should be first
        assert bottlenecks[0]["name"] == "slow_op"
    
    def test_get_memory_stats(self, profiler):
        """Test memory stats retrieval."""
        stats = profiler.get_memory_stats()
        
        assert "vram_available" in stats
        assert "vram_used_gb" in stats
    
    def test_reset(self, profiler):
        """Test resetting profiler."""
        with profiler.measure("op1"):
            pass
        
        profiler.reset()
        
        stats = profiler.get_stats()
        assert len(stats["timings"]) == 0


class TestSingletons:
    """Tests for singleton access functions."""
    
    def test_get_metrics_singleton(self):
        from utils.metrics import get_metrics
        
        m1 = get_metrics()
        m2 = get_metrics()
        
        assert m1 is m2
    
    def test_get_profiler_singleton(self):
        from utils.profiler import get_profiler
        
        p1 = get_profiler()
        p2 = get_profiler()
        
        assert p1 is p2
    
    def test_get_checkpoint_manager_singleton(self):
        from utils.checkpoint import get_checkpoint_manager
        
        c1 = get_checkpoint_manager()
        c2 = get_checkpoint_manager()
        
        assert c1 is c2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
