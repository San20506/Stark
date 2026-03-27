"""
Autonomous Orchestration
=========================
Autonomous multi-agent orchestration with Router-Arbiter architecture.

Implements hierarchical agent routing with fast and deep processing paths.
"""

import logging
import time
from typing import Dict, Any, Optional
import json

from agents.base_agent import BaseAgent, AgentResult, AgentOrchestrator
from agents.router_agent import RouterAgent, RoutePath
from agents.specialists import (
    RetrieverAgent,
    FastAnswerAgent,
    PlannerAgent,
    ArbiterAgent,
)
try:
    from agents.web_agent import WebAgent
except ImportError:
    WebAgent = None  # type: ignore[assignment,misc]
from agents.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


class AutonomousOrchestrator:
    """
    Autonomous orchestrator with Router-Arbiter architecture.
    
    Flow:
        User Query
            ↓
        RouterAgent (decide path)
            ↓
        ├─→ Fast Path (Retriever + FastAnswer)
        └─→ Deep Path (Planner + Execution)
            ↓
        ArbiterAgent (select best)
            ↓
        Final Response
    """
    
    def __init__(self):
        """Initialize autonomous orchestrator."""
        self.orchestrator = AgentOrchestrator()
        self.tool_executor = None  # Lazy init after agents registered
        
        # Register core agents
        self.router = RouterAgent()
        self.retriever = RetrieverAgent()
        self.fast_answer = FastAnswerAgent()
        self.planner = PlannerAgent()
        self.arbiter = ArbiterAgent()
        self.web_agent = WebAgent() if WebAgent is not None else None

        self.orchestrator.register_agent(self.router)
        self.orchestrator.register_agent(self.retriever)
        self.orchestrator.register_agent(self.fast_answer)
        self.orchestrator.register_agent(self.planner)
        self.orchestrator.register_agent(self.arbiter)
        if self.web_agent is not None:
            self.orchestrator.register_agent(self.web_agent)
        
        logger.info("AutonomousOrchestrator initialized")
    
    def predict(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Autonomous prediction with multi-agent routing.
        
        Args:
            query: User query
            context: Optional context
            
        Returns:
            Dict with response and metadata
        """
        start_time = time.time()
        context = context or {}
        
        try:
            # Step 1: Route the query
            routing_result = self.router.run(query, context)
            
            if not routing_result.success:
                return {
                    "response": "Routing failed",
                    "error": routing_result.error,
                    "latency_ms": (time.time() - start_time) * 1000,
                }
            
            routing_data = json.loads(routing_result.output)
            path = RoutePath(routing_data["path"])
            
            logger.info(f"Routed to {path.value} path")
            
            # Step 2: Execute path(s)
            candidates = []
            
            if path in [RoutePath.FAST, RoutePath.BOTH]:
                fast_result = self._execute_fast_path(query, context)
                if fast_result:
                    candidates.append(fast_result)
            
            if path in [RoutePath.DEEP, RoutePath.BOTH]:
                deep_result = self._execute_deep_path(query, context)
                if deep_result:
                    candidates.append(deep_result)
            
            # Step 3: Arbiter selection
            if len(candidates) == 0:
                return {
                    "response": "No response generated",
                    "error": "All paths failed",
                    "latency_ms": (time.time() - start_time) * 1000,
                }
            
            if len(candidates) == 1:
                final_answer = candidates[0]
            else:
                arbiter_result = self.arbiter.run(query, {"candidates": candidates})
                if arbiter_result.success:
                    final_data = json.loads(arbiter_result.output)
                    final_answer = final_data
                else:
                    final_answer = candidates[0]  # Fallback to first
            
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                "response": final_answer.get("answer", ""),
                "source": final_answer.get("source", "unknown"),
                "confidence": final_answer.get("confidence", 0.0),
                "latency_ms": latency_ms,
                "path": path.value,
                "routing": routing_data,
            }
            
        except Exception as e:
            logger.error(f"Autonomous prediction failed: {e}", exc_info=True)
            return {
                "response": "An error occurred",
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000,
            }
    
    def _execute_fast_path(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Execute fast path: Retriever → FastAnswer.
        
        Returns:
            Candidate answer dict or None
        """
        try:
            # Retrieve relevant documents
            retriever_result = self.retriever.run(query, {"top_k": 3})
            
            retrieved_docs = []
            if retriever_result.success:
                retrieved_docs = json.loads(retriever_result.output)
            
            # Generate fast answer
            answer_result = self.fast_answer.run(
                query,
                {"retrieved_docs": retrieved_docs}
            )
            
            if not answer_result.success:
                return None
            
            answer_data = json.loads(answer_result.output)
            
            return {
                "answer": answer_data["answer"],
                "confidence": answer_data["confidence"],
                "source": "fast",
                "metadata": {
                    "model": answer_data["model"],
                    "retrieved_docs": len(retrieved_docs),
                }
            }
            
        except Exception as e:
            logger.error(f"Fast path failed: {e}")
            return None
    
    def _execute_deep_path(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Execute deep path: Planner → (Future: Tool execution) → Reasoner.
        
        Currently simplified - just uses planner.
        Future: Will execute plan steps with tools.
        
        Returns:
            Candidate answer dict or None
        """
        try:
            # Create plan
            plan_result = self.planner.run(query, context)
            
            if not plan_result.success:
                return None
            
            plan_data = json.loads(plan_result.output)
            
            # Execute plan with tools
            if self.tool_executor is None:
                self.tool_executor = ToolExecutor(self.orchestrator)
            
            execution_result = self.tool_executor.execute_plan(query, plan_data)
            
            # Build answer from execution
            if execution_result.get("success"):
                answer = execution_result["output"]
                confidence = 0.85  # High confidence when tools execute successfully
            else:
                answer = f"Plan created but execution incomplete: {execution_result.get('output', 'No output')}"
                confidence = 0.6
            
            return {
                "answer": answer,
                "confidence": confidence,
                "source": "deep",
                "metadata": {
                    "plan": plan_data,
                    "completed_steps": execution_result.get("steps_executed", 0),
                    "total_steps": len(plan_data.get("steps", [])),
                    "execution": execution_result,
                }
            }
            
        except Exception as e:
            logger.error(f"Deep path failed: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return self.orchestrator.get_stats()


# =============================================================================
# SINGLETON
# =============================================================================

_autonomous_orchestrator: Optional[AutonomousOrchestrator] = None


def get_autonomous_orchestrator() -> AutonomousOrchestrator:
    """Get or create autonomous orchestrator."""
    global _autonomous_orchestrator
    
    if _autonomous_orchestrator is None:
        _autonomous_orchestrator = AutonomousOrchestrator()
    
    return _autonomous_orchestrator


def reset_autonomous_orchestrator() -> None:
    """Reset orchestrator (for testing)."""
    global _autonomous_orchestrator
    _autonomous_orchestrator = None
