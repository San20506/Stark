"""
Tests for STARK Orchestration Module
"""

import pytest
from unittest.mock import MagicMock, patch

# Reset singleton before each test
@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset STARK singleton before each test."""
    from core.main import reset_stark
    reset_stark()
    yield
    reset_stark()


class TestSTARKInit:
    """Tests for STARK initialization."""
    
    def test_create_stark_lazy(self):
        """Test lazy initialization."""
        from core.main import STARK
        stark = STARK(lazy_load=True)
        
        assert stark._task_detector is None
        assert stark._memory is None
        assert stark._running is False
    
    def test_singleton_pattern(self):
        """Test get_stark returns same instance."""
        from core.main import get_stark
        
        s1 = get_stark()
        s2 = get_stark()
        
        assert s1 is s2


class TestSTARKLifecycle:
    """Tests for STARK lifecycle methods."""
    
    def test_start_stop(self):
        """Test start and stop cycle."""
        from core.main import STARK
        stark = STARK(lazy_load=True)
        
        # Start
        stark.start()
        assert stark._running is True
        assert stark._start_time is not None
        
        # Stop
        stark.stop()
        assert stark._running is False
    
    def test_double_start(self):
        """Test calling start twice doesn't error."""
        from core.main import STARK
        stark = STARK(lazy_load=True)
        
        stark.start()
        stark.start()  # Should just log warning
        assert stark._running is True
        stark.stop()
    
    def test_double_stop(self):
        """Test calling stop twice doesn't error."""
        from core.main import STARK
        stark = STARK(lazy_load=True)
        
        stark.start()
        stark.stop()
        stark.stop()  # Should just log warning
        assert stark._running is False


class TestSTARKPrediction:
    """Tests for STARK prediction methods."""
    
    def test_predict_returns_result(self):
        """Test predict returns PredictionResult."""
        from core.main import STARK, PredictionResult
        stark = STARK(lazy_load=True)
        
        result = stark.predict("fix this error in my code")
        
        assert isinstance(result, PredictionResult)
        assert result.task is not None
        assert result.confidence >= 0.0
        assert result.latency_ms > 0
    
    def test_predict_detects_task(self):
        """Test task detection works."""
        from core.main import STARK
        stark = STARK(lazy_load=True)
        
        result = stark.predict("What does this function do?")
        # Should detect as code_explanation or similar
        assert result.task in [
            "error_debugging", "code_explanation", "task_planning",
            "research", "health_monitoring", "system_control",
            "conversation", "math_reasoning", "unknown"
        ]
    
    def test_predict_handles_error(self):
        """Test predict handles errors gracefully."""
        from core.main import STARK
        stark = STARK(lazy_load=True)
        
        # Mock task detector to raise error
        stark._task_detector = MagicMock()
        stark._task_detector.detect.side_effect = Exception("Test error")
        
        result = stark.predict("test query")
        
        assert result.error is not None
        assert result.task == "error"


class TestSTARKStatus:
    """Tests for STARK status methods."""
    
    def test_status_when_stopped(self):
        """Test status when not running."""
        from core.main import STARK
        stark = STARK(lazy_load=True)
        
        status = stark.status()
        
        assert status.running is False
        assert status.uptime_seconds == 0.0
        assert status.queries_processed == 0
    
    def test_status_when_running(self):
        """Test status when running."""
        from core.main import STARK
        stark = STARK(lazy_load=True)
        stark.start()
        
        # Make a prediction
        stark.predict("test")
        
        status = stark.status()
        
        assert status.running is True
        assert status.uptime_seconds > 0
        assert status.queries_processed == 1
        
        stark.stop()
    
    def test_health_check(self):
        """Test health check returns dict."""
        from core.main import STARK
        stark = STARK(lazy_load=True)
        
        health = stark.health_check()
        
        assert isinstance(health, dict)
        assert "config" in health
        assert "task_detector" in health
        assert "memory" in health
        assert "ollama" in health


class TestPredictionResult:
    """Tests for PredictionResult dataclass."""
    
    def test_to_dict(self):
        """Test to_dict conversion."""
        from core.main import PredictionResult
        
        result = PredictionResult(
            response="Test response",
            task="error_debugging",
            confidence=0.95,
            latency_ms=50.0,
        )
        
        d = result.to_dict()
        
        assert d["response"] == "Test response"
        assert d["task"] == "error_debugging"
        assert d["confidence"] == 0.95
        assert d["latency_ms"] == 50.0


class TestSystemStatus:
    """Tests for SystemStatus dataclass."""
    
    def test_to_dict(self):
        """Test to_dict conversion."""
        from core.main import SystemStatus
        from datetime import datetime
        
        now = datetime.now()
        status = SystemStatus(
            running=True,
            uptime_seconds=100.5,
            queries_processed=10,
            memories_stored=50,
            active_adapter="error_debugging",
            learning_active=True,
            vram_usage_gb=4.5,
            last_query_time=now,
        )
        
        d = status.to_dict()
        
        assert d["running"] is True
        assert d["uptime_seconds"] == 100.5
        assert d["queries_processed"] == 10
        assert d["last_query_time"] == now.isoformat()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
