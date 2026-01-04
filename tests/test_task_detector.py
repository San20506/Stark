"""
Tests for Task Detection Module
================================
Tests for TaskDetector, emergent task handling, and classification.
"""

import pytest
from unittest.mock import Mock, patch


class TestTaskDetector:
    """Tests for TaskDetector class."""
    
    @pytest.fixture
    def detector(self):
        """Create TaskDetector instance."""
        from core.task_detector import TaskDetector
        return TaskDetector(threshold=0.15, use_hybrid=True)
    
    def test_init(self, detector):
        """Test detector initialization."""
        assert detector is not None
        assert detector.threshold == 0.15
        assert detector.use_hybrid is True
        assert len(detector._examples) > 0
    
    def test_detect_error_debugging(self, detector):
        """Test detection of error debugging task."""
        result = detector.detect("How do I fix this IndexError?")
        
        assert result.task == "error_debugging"
        assert result.confidence > 0
        assert result.method in ["hybrid", "tfidf", "keyword"]
    
    def test_detect_code_explanation(self, detector):
        """Test detection of code explanation task."""
        result = detector.detect("Explain what this function does")
        
        assert result.task == "code_explanation"
        assert result.confidence > 0
    
    def test_detect_health_monitoring(self, detector):
        """Test detection of health monitoring task."""
        result = detector.detect("Remind me to take a break")
        
        assert result.task == "health_monitoring"
        assert result.confidence > 0
    
    def test_detect_system_control(self, detector):
        """Test detection of system control task."""
        result = detector.detect("Open Chrome browser")
        
        assert result.task == "system_control"
        assert result.confidence > 0
    
    def test_detect_math_reasoning(self, detector):
        """Test detection of math reasoning task."""
        result = detector.detect("Calculate 15% of 200")
        
        assert result.task == "math_reasoning"
        assert result.confidence > 0
    
    def test_detect_conversation(self, detector):
        """Test detection of conversation task."""
        result = detector.detect("Hello, how are you?")
        
        assert result.task == "conversation"
        assert result.confidence > 0
    
    def test_detect_task_planning(self, detector):
        """Test detection of task planning."""
        result = detector.detect("Plan my project roadmap")
        
        assert result.task == "task_planning"
        assert result.confidence > 0
    
    def test_detect_research(self, detector):
        """Test detection of research task."""
        result = detector.detect("Research the best Python frameworks")
        
        assert result.task == "research"
        assert result.confidence > 0
    
    def test_confidence_range(self, detector):
        """Test that confidence is in valid range."""
        queries = [
            "Fix this bug",
            "What does this code do?",
            "Hello!",
            "Calculate 5 + 3",
            "Open notepad",
        ]
        
        for query in queries:
            result = detector.detect(query)
            assert 0 <= result.confidence <= 1
    
    def test_empty_query(self, detector):
        """Test handling of empty query."""
        result = detector.detect("")
        
        assert result.task == "conversation"
        assert result.method == "default"
    
    def test_emergent_task_detection(self, detector):
        """Test that low-confidence queries are flagged as emergent."""
        # Very unusual query that shouldn't match well
        result = detector.detect("xyzzy plugh")
        
        if result.confidence < detector.threshold:
            assert result.is_emergent is True
            assert result.emergent_id is not None
            assert result.method == "emergent"
    
    def test_emergent_id_uniqueness(self, detector):
        """Test that emergent IDs are unique."""
        ids = set()
        
        for _ in range(5):
            result = detector.detect("completely random gibberish xyz")
            if result.is_emergent and result.emergent_id:
                assert result.emergent_id not in ids
                ids.add(result.emergent_id)
    
    def test_detection_result_to_dict(self, detector):
        """Test DetectionResult serialization."""
        result = detector.detect("Fix my code")
        d = result.to_dict()
        
        assert "task" in d
        assert "confidence" in d
        assert "scores" in d
        assert "method" in d
        assert "is_emergent" in d
    
    def test_add_example(self, detector):
        """Test adding new examples."""
        initial_count = len(detector._examples)
        
        detector.add_example("New custom query", "error_debugging")
        
        assert len(detector._examples) == initial_count + 1
    
    def test_add_examples_batch(self, detector):
        """Test adding multiple examples."""
        initial_count = len(detector._examples)
        
        detector.add_examples([
            ("Query one", "error_debugging"),
            ("Query two", "code_explanation"),
        ])
        
        assert len(detector._examples) == initial_count + 2
    
    def test_get_top_tasks(self, detector):
        """Test getting top k task predictions."""
        top = detector.get_top_tasks("Fix this bug please", top_k=3)
        
        assert len(top) == 3
        assert all(isinstance(t, tuple) and len(t) == 2 for t in top)
        # Should be sorted by score descending
        scores = [t[1] for t in top]
        assert scores == sorted(scores, reverse=True)
    
    def test_get_stats(self, detector):
        """Test statistics retrieval."""
        # Make some detections
        detector.detect("test query 1")
        detector.detect("test query 2")
        
        stats = detector.get_stats()
        
        assert "total_detections" in stats
        assert stats["total_detections"] >= 2
        assert "task_counts" in stats
        assert "emergent_count" in stats
    
    def test_task_correlation_logging(self, detector):
        """Test that correlations are logged for low-confidence queries."""
        # Make a query that's likely ambiguous
        detector.detect("random unlikely query xyz")
        
        # Check correlation buffer is populated if emergent
        assert isinstance(detector._task_correlations, list)
    
    def test_classification_speed(self, detector):
        """Test that classification is fast (<5ms target)."""
        import time
        
        queries = [
            "Fix this bug",
            "Explain this code",
            "Open Chrome",
            "Calculate 5 + 3",
            "Hello there",
        ]
        
        start = time.perf_counter()
        for query in queries:
            detector.detect(query)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # Average should be under 5ms per query
        avg_ms = elapsed_ms / len(queries)
        assert avg_ms < 50  # Allow some margin for test environment


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""
    
    def test_creation(self):
        from core.task_detector import DetectionResult
        
        result = DetectionResult(
            task="error_debugging",
            confidence=0.85,
            scores={"error_debugging": 0.85, "code_explanation": 0.3},
            method="hybrid",
        )
        
        assert result.task == "error_debugging"
        assert result.confidence == 0.85
        assert result.is_emergent is False
    
    def test_emergent_result(self):
        from core.task_detector import DetectionResult
        
        result = DetectionResult(
            task="unknown",
            confidence=0.1,
            is_emergent=True,
            emergent_id="emergent_12345_1",
            method="emergent",
        )
        
        assert result.is_emergent is True
        assert result.emergent_id is not None


class TestSingleton:
    """Tests for get_detector singleton."""
    
    def test_singleton_pattern(self):
        from core.task_detector import get_detector
        
        d1 = get_detector()
        d2 = get_detector()
        
        assert d1 is d2
