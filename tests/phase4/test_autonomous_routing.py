"""
Test Autonomous Multi-Agent Routing
====================================
Tests for the Router-Arbiter autonomous agent system.
"""

import pytest
import json

from agents.router_agent import RouterAgent, RoutePath
from agents.specialists import (
    RetrieverAgent,
    FastAnswerAgent,
    PlannerAgent,
    ArbiterAgent,
)
from agents.autonomous_orchestrator import (
    AutonomousOrchestrator,
    get_autonomous_orchestrator,
    reset_autonomous_orchestrator,
)


class TestRouterAgent:
    """Test RouterAgent path selection."""
    
    def setup_method(self):
        """Reset before each test."""
        from core.adaptive_router import reset_router
        from core.task_detector import reset_task_detector
        reset_router()
        reset_task_detector()
    
    def test_init(self):
        """Test router initialization."""
        router = RouterAgent()
        assert router.name == "RouterAgent"
        assert router.description == "Routes queries to appropriate processing paths"
    
    def test_simple_greeting_fast_path(self):
        """Test that greetings route to fast path."""
        router = RouterAgent()
        result = router.run("hello")
        
        assert result.success
        data = json.loads(result.output)
        # Should route to fast path for simple greeting
        assert data["path"] in ["fast", "both"]
    
    def test_code_request_deep_path(self):
        """Test that code requests route to deep path."""
        router = RouterAgent()
        result = router.run("write a Python function to sort a list")
        
        assert result.success
        data = json.loads(result.output)
        # Should route to deep path for code generation
        assert data["path"] in ["deep", "both"]


class TestSpecialistAgents:
    """Test specialist agents."""
    
    def test_fast_answer_agent(self):
        """Test FastAnswerAgent."""
        agent = FastAnswerAgent()
        result = agent.run("What is Python?")
        
        assert result.success
        data = json.loads(result.output)
        assert "answer" in data
        assert "confidence" in data
        assert data["model"] == "llama3.2:3b"
    
    def test_planner_agent(self):
        """Test PlannerAgent."""
        agent = PlannerAgent()
        result = agent.run("Create a web scraper for news articles")
        
        assert result.success
        data = json.loads(result.output)
        assert "steps" in data
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) > 0
    
    def test_arbiter_agent_single_candidate(self):
        """Test ArbiterAgent with single candidate."""
        agent = ArbiterAgent()
        
        candidates = [
            {"answer": "Test answer", "confidence": 0.8, "source": "fast"}
        ]
        
        result = agent.run("test query", {"candidates": candidates})
        
        assert result.success
        data = json.loads(result.output)
        assert data["answer"] == "Test answer"
        assert data["source"] == "fast"
    
    def test_arbiter_agent_multiple_candidates(self):
        """Test ArbiterAgent selects best candidate."""
        agent = ArbiterAgent()
        
        candidates = [
            {"answer": "Fast answer", "confidence": 0.6, "source": "fast"},
            {"answer": "Deep answer", "confidence": 0.9, "source": "deep"},
        ]
        
        result = agent.run("test query", {"candidates": candidates})
        
        assert result.success
        data = json.loads(result.output)
        # Should select deep answer (higher confidence)
        assert data["source"] == "deep"
        assert data["confidence"] == 0.9


class TestAutonomousOrchestrator:
    """Test full autonomous orchestration flow."""
    
    def setup_method(self):
        """Reset orchestrator before each test."""
        reset_autonomous_orchestrator()
    
    def test_init(self):
        """Test orchestrator initialization."""
        orchestrator = AutonomousOrchestrator()
        
        assert orchestrator.router is not None
        assert orchestrator.retriever is not None
        assert orchestrator.fast_answer is not None
        assert orchestrator.planner is not None
        assert orchestrator.arbiter is not None
    
    def test_singleton(self):
        """Test singleton pattern."""
        orch1 = get_autonomous_orchestrator()
        orch2 = get_autonomous_orchestrator()
        
        assert orch1 is orch2
    
    def test_predict_fast_path(self):
        """Test prediction using fast path."""
        orchestrator = get_autonomous_orchestrator()
        result = orchestrator.predict("hello there")
        
        assert "response" in result
        assert "source" in result
        assert "latency_ms" in result
        # Fast queries should complete quickly
        assert result["latency_ms"] < 5000  # 5 seconds max
    
    def test_predict_deep_path(self):
        """Test prediction using deep path."""
        orchestrator = get_autonomous_orchestrator()
        result = orchestrator.predict("plan a project to build a web app")
        
        assert "response" in result
        assert "source" in result
        # Deep path may create plans
        if result.get("source") == "deep":
            assert len(result["response"]) > 0


class TestIntegration:
    """Integration tests for full flow."""
    
    def test_end_to_end_simple(self):
        """Test simple end-to-end flow."""
        reset_autonomous_orchestrator()
        orchestrator = get_autonomous_orchestrator()
        
        result = orchestrator.predict("What is 2+2?")
        
        assert result is not None
        assert "response" in result
        assert result.get("latency_ms", 0) > 0
    
    def test_get_stats(self):
        """Test statistics gathering."""
        orchestrator = get_autonomous_orchestrator()
        
        # Make a prediction
        orchestrator.predict("test query")
        
        # Get stats
        stats = orchestrator.get_stats()
        
        assert "total_agents" in stats
        assert stats["total_agents"] >= 5  # At least 5 core agents


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
