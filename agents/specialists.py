"""
Specialist Agents
=================
Specialized agents for the Fast and Deep processing paths.

Agents:
- RetrieverAgent: RAG-based document retrieval
- FastAnswerAgent: Quick Q&A using small model
- PlannerAgent: Task decomposition and planning
- ArbiterAgent: Response selection and merging
"""

import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from agents.base_agent import BaseAgent, AgentResult, AgentType

logger = logging.getLogger(__name__)


# =============================================================================
# RETRIEVER AGENT (Fast Path)
# =============================================================================

class RetrieverAgent(BaseAgent):
    """
    RAG-based document retrieval agent.
    
    Retrieves relevant context from indexed documents.
    """
    
    def __init__(self, name: str = "RetrieverAgent"):
        """Initialize Retriever Agent."""
        super().__init__(
            name=name,
            agent_type=AgentType.RESEARCH,
            description="Retrieve relevant documents using RAG",
        )
        
        self._retriever = None
    
    def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Retrieve relevant documents.
        
        Args:
            task: Query for retrieval
            context: Optional context
            
        Returns:
            AgentResult with retrieved passages
        """
        context = context or {}
        steps = []
        
        try:
            # Lazy load RAG
            if self._retriever is None:
                from rag.retriever import get_retriever
                self._retriever = get_retriever()
            
            steps.append("Searching documents")
            
            # Retrieve relevant passages
            top_k = context.get('top_k', 3)
            results = self._retriever.search(task, top_k=top_k)
            
            steps.append(f"Found {len(results)} relevant passages")
            
            # Format output
            passages = []
            for result in results:
                passages.append({
                    "text": result.text,
                    "source": result.source,
                    "score": result.score,
                })
            
            return AgentResult(
                success=True,
                output=json.dumps(passages, indent=2),
                steps_taken=steps,
            )
            
        except Exception as e:
            logger.error(f"RetrieverAgent error: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="[]",
                error=str(e),
                steps_taken=steps,
            )


# =============================================================================
# FAST ANSWER AGENT (Fast Path)
# =============================================================================

class FastAnswerAgent(BaseAgent):
    """
    Fast Q&A agent using lightweight model.
    
    Generates quick responses with low latency.
    """
    
    def __init__(self, name: str = "FastAnswerAgent"):
        """Initialize Fast Answer Agent."""
        super().__init__(
            name=name,
            agent_type=AgentType.GENERAL,
            description="Quick Q&A using fast model",
            timeout=10.0,  # Fast responses only
        )
        
        self._model = "llama3.2:3b"
    
    def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Generate fast answer.
        
        Args:
            task: User query
            context: Optional context with 'retrieved_docs'
            
        Returns:
            AgentResult with quick answer
        """
        context = context or {}
        steps = []
        
        try:
            import requests
            from core.constants import OLLAMA_BASE_URL
            
            steps.append(f"Generating answer with {self._model}")
            
            # Build prompt with context
            retrieved_docs = context.get('retrieved_docs', [])
            
            if retrieved_docs:
                context_text = "\n\n".join([
                    f"Context {i+1}: {doc['text'][:300]}"
                    for i, doc in enumerate(retrieved_docs)
                ])
                prompt = f"{context_text}\n\nQuestion: {task}\n\nAnswer:"
            else:
                prompt = task
            
            # Generate response
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 200,  # Short answers
                        "temperature": 0.7,
                    },
                },
                timeout=self.timeout,
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama returned {response.status_code}")
            
            answer = response.json().get("response", "").strip()
            
            steps.append(f"Generated answer ({len(answer)} chars)")
            
            # Calculate confidence (simple heuristic)
            confidence = 0.8 if len(retrieved_docs) > 0 else 0.6
            
            return AgentResult(
                success=True,
                output=json.dumps({
                    "answer": answer,
                    "confidence": confidence,
                    "model": self._model,
                }),
                steps_taken=steps,
            )
            
        except Exception as e:
            logger.error(f"FastAnswerAgent error: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                steps_taken=steps,
            )


# =============================================================================
# PLANNER AGENT (Deep Path)
# =============================================================================

class PlannerAgent(BaseAgent):
    """
    Planning agent that decomposes tasks into steps.
    
    Uses thinking model for strategic planning.
    """
    
    def __init__(self, name: str = "PlannerAgent"):
        """Initialize Planner Agent."""
        super().__init__(
            name=name,
            agent_type=AgentType.GENERAL,
            description="Task decomposition and planning",
            timeout=30.0,
        )
        
        self._model = "qwen3:4b"  # Thinking model
    
    def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Create execution plan.
        
        Args:
            task: User query/request
            context: Optional context
            
        Returns:
            AgentResult with structured plan
        """
        context = context or {}
        steps = []
        
        try:
            import requests
            from core.constants import OLLAMA_BASE_URL
            
            steps.append(f"Planning with {self._model}")
            
            # Build planning prompt
            prompt = f"""Analyze this request and create a step-by-step plan:

Request: {task}

Create a JSON plan with these fields:
{{
    "steps": [list of specific actions],
    "requires_tools": ["file", "code", "web", etc.],
    "complexity": "simple|moderate|complex",
    "estimated_time": "time estimate"
}}

Output ONLY valid JSON."""
            
            # Generate plan
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 400},
                },
                timeout=self.timeout,
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama returned {response.status_code}")
            
            plan_text = response.json().get("response", "")
            
            # Parse JSON plan
            import re
            json_match = re.search(r'\{.*\}', plan_text, re.DOTALL)
            
            if json_match:
                plan = json.loads(json_match.group())
            else:
                # Fallback: simple plan
                plan = {
                    "steps": ["Analyze request", "Execute", "Return result"],
                    "requires_tools": [],
                    "complexity": "moderate",
                }
            
            steps.append(f"Created plan with {len(plan.get('steps', []))} steps")
            
            return AgentResult(
                success=True,
                output=json.dumps(plan, indent=2),
                steps_taken=steps,
            )
            
        except Exception as e:
            logger.error(f"PlannerAgent error: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                steps_taken=steps,
            )


# =============================================================================
# ARBITER AGENT (Final Selection)
# =============================================================================

@dataclass
class CandidateAnswer:
    """Candidate answer from a processing path."""
    answer: str
    confidence: float
    source: str  # "fast" or "deep"
    metadata: Dict[str, Any]


class ArbiterAgent(BaseAgent):
    """
    Arbiter agent that selects best answer.
    
    Chooses between fast and deep path responses.
    """
    
    def __init__(self, name: str = "ArbiterAgent"):
        """Initialize Arbiter Agent."""
        super().__init__(
            name=name,
            agent_type=AgentType.GENERAL,
            description="Select best response from candidates",
        )
    
    def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Select best answer from candidates.
        
        Args:
            task: Original query
            context: Must contain 'candidates' list
            
        Returns:
            AgentResult with selected answer
        """
        context = context or {}
        steps = []
        
        try:
            candidates = context.get('candidates', [])
            
            if not candidates:
                return AgentResult(
                    success=False,
                    output="",
                    error="No candidates provided",
                )
            
            steps.append(f"Evaluating {len(candidates)} candidates")
            
            # Simple selection strategy
            # TODO: Could use LLM for more sophisticated selection
            
            # Sort by confidence
            sorted_candidates = sorted(
                candidates,
                key=lambda c: c.get('confidence', 0.0),
                reverse=True
            )
            
            best = sorted_candidates[0]
            
            steps.append(f"Selected {best.get('source', 'unknown')} answer")
            
            # Add metadata about selection
            result = {
                "answer": best.get('answer', ''),
                "source": best.get('source', 'unknown'),
                "confidence": best.get('confidence', 0.0),
                "alternatives": len(candidates) - 1,
            }
            
            return AgentResult(
                success=True,
                output=json.dumps(result, indent=2),
                steps_taken=steps,
            )
            
        except Exception as e:
            logger.error(f"ArbiterAgent error: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                steps_taken=steps,
            )
