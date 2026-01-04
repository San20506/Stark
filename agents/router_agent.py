"""
Router Agent
=============
High-level routing agent that decides query handling strategy.

Routes queries to either:
- Fast Path: For simple Q&A, low-latency responses
- Deep Path: For complex analysis, planning, code generation
- Both Paths: For comprehensive coverage with arbiter selection
"""

import logging
import json
from typing import Dict, Any, Optional
from enum import Enum

from agents.base_agent import BaseAgent, AgentResult, AgentType

logger = logging.getLogger(__name__)


class RoutePath(Enum):
    """Available routing paths."""
    FAST = "fast"
    DEEP = "deep"
    BOTH = "both"


class RouterAgent(BaseAgent):
    """
    Router agent that decides query handling strategy.
    
    Uses AdaptiveRouter for intelligent routing decisions.
    """
    
    def __init__(self, name: str = "RouterAgent"):
        """Initialize Router Agent."""
        super().__init__(
            name=name,
            agent_type=AgentType.GENERAL,
            description="Routes queries to appropriate processing paths",
        )
        
        self._adaptive_router = None
        self._task_detector = None
    
    def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Route the query to appropriate path.
        
        Args:
            task: User query
            context: Optional context
            
        Returns:
            AgentResult with routing decision
        """
        context = context or {}
        steps = []
        
        try:
            # Lazy load dependencies
            if self._adaptive_router is None:
                from core.adaptive_router import get_router
                from core.task_detector import TaskDetector
                
                self._adaptive_router = get_router()
                self._task_detector = TaskDetector()
            
            steps.append("Analyzing query")
            
            # Step 1: Get initial task detection
            detection = self._task_detector.detect(task)
            initial_task = detection.task
            confidence = detection.confidence
            
            steps.append(f"TaskDetector: {initial_task} ({confidence:.2f})")
            
            # Step 2: Use adaptive router for detailed analysis
            routing = self._adaptive_router.route(task, initial_task, confidence)
            
            steps.append(f"Router decision: {routing.task}")
            
            # Step 3: Determine path
            path = self._determine_path(task, routing, context)
            
            steps.append(f"Selected path: {path.value}")
            
            # Build result
            output_data = {
                "path": path.value,
                "task": routing.task,
                "model": routing.model,
                "confidence": routing.confidence,
                "reasoning": routing.reasoning,
                "needs_clarification": routing.needs_clarification,
                "clarification_prompt": routing.clarification_prompt,
            }
            
            return AgentResult(
                success=True,
                output=json.dumps(output_data),
                steps_taken=steps,
            )
            
        except Exception as e:
            logger.error(f"RouterAgent error: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                steps_taken=steps,
            )
    
    def _determine_path(
        self,
        query: str,
        routing,
        context: Dict[str, Any]
    ) -> RoutePath:
        """
        Determine which path to use.
        
        Logic:
        - Fast: Simple Q&A, greetings, factual queries
        - Deep: Code generation, planning, analysis, simulation
        - Both: When speed matters but accuracy is critical
        """
        task = routing.task
        query_lower = query.lower()
        
        # Deep path triggers
        deep_keywords = [
            "plan", "design", "create", "build", "write code",
            "implement", "analyze", "simulate", "explain how",
            "why does", "debug", "fix", "optimize"
        ]
        
        # Fast path triggers
        fast_keywords = [
            "hello", "hi", "hey", "what is", "who is",
            "when", "where", "quick question"
        ]
        
        # Check for deep path triggers
        if any(kw in query_lower for kw in deep_keywords):
            return RoutePath.DEEP
        
        # Check for fast path triggers
        if any(kw in query_lower for kw in fast_keywords):
            return RoutePath.FAST
        
        # Check task category
        if task in ["code_generation", "code_review", "error_debugging"]:
            return RoutePath.DEEP
        elif task in ["conversation", "greeting", "general"]:
            return RoutePath.FAST
        
        # Check confidence
        if routing.confidence >= 0.8:
            return RoutePath.FAST  # High confidence = fast path
        elif routing.confidence < 0.5:
            return RoutePath.DEEP  # Low confidence = needs analysis
        
        # Default: use both paths for comprehensive coverage
        return RoutePath.BOTH
