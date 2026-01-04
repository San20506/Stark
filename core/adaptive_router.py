"""
STARK Adaptive Router
=======================
Intelligent routing layer that uses LLM for ambiguous/unknown queries.

When TaskDetector confidence is low, this module:
1. Asks a fast LLM to analyze the query intent
2. Decides optimal routing (model, task, clarification needed)
3. Handles edge cases (multi-intent, ambiguity, safety)
"""

import logging
import json
import re
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
import requests

from core.constants import (
    OLLAMA_BASE_URL,
    TASK_MODELS,
    OLLAMA_DEFAULT_MODEL,
    TASK_CATEGORIES,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RoutingDecision:
    """Result of adaptive routing analysis."""
    
    # Primary routing
    task: str                      # Final task category
    model: str                     # Model to use
    confidence: float              # Router's confidence in this decision
    
    # Metadata
    reasoning: str = ""            # Why this decision was made
    is_multi_intent: bool = False  # Query contains multiple intents
    sub_intents: List[str] = None  # List of detected sub-intents
    
    # Edge cases
    needs_clarification: bool = False  # Should ask user for clarity
    clarification_prompt: str = ""      # Question to ask user
    is_safe: bool = True               # Passed safety check
    safety_reason: str = ""            # Why it's marked unsafe
    
    def __post_init__(self):
        if self.sub_intents is None:
            self.sub_intents = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "model": self.model,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "is_multi_intent": self.is_multi_intent,
            "sub_intents": self.sub_intents,
            "needs_clarification": self.needs_clarification,
            "clarification_prompt": self.clarification_prompt,
            "is_safe": self.is_safe,
            "safety_reason": self.safety_reason,
        }


# =============================================================================
# ROUTER PROMPTS
# =============================================================================

ROUTER_SYSTEM_PROMPT = """You are a routing agent for STARK AI. Analyze the user query and decide how to handle it.

Available task categories: {categories}

IMPORTANT: Only set needs_clarification=true if the query is TRULY ambiguous (like "open" with no context).
For normal greetings and clear questions, route confidently.

Respond with a JSON object:
{{
    "task": "the best matching task category",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "is_complex": true/false (needs deep reasoning?),
    "is_multi_intent": false,
    "sub_intents": null,
    "needs_clarification": false,
    "clarification_prompt": null,
    "is_safe": true
}}

Be concise. Output ONLY valid JSON."""

ROUTER_USER_PROMPT = """Query: "{query}"

Context:
- Initial task guess: {initial_task}
- Initial confidence: {initial_confidence:.2f}

Analyze and route this query."""


# =============================================================================
# ADAPTIVE ROUTER
# =============================================================================

class AdaptiveRouter:
    """
    Intelligent routing layer using LLM for ambiguous queries.
    
    Architecture:
        TaskDetector (fast) -> [if low confidence] -> AdaptiveRouter (LLM)
                                                           |
                                                           v
                                              RoutingDecision (task, model, etc)
    """
    
    def __init__(
        self,
        router_model: str = "llama3.2:3b",
        confidence_threshold: float = 0.6,
        timeout: float = 30.0,  # Increased for model warmup
    ):
        """
        Initialize adaptive router.
        
        Args:
            router_model: Small, fast model for routing decisions
            confidence_threshold: Below this, we use full LLM routing
            timeout: HTTP timeout for router calls
        """
        self.router_model = router_model
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout
        
        # Stats
        self._routes_analyzed = 0
        self._llm_routes = 0
        self._clarifications_requested = 0
        
        logger.info(f"AdaptiveRouter initialized (model={router_model}, threshold={confidence_threshold})")
    
    def route(
        self,
        query: str,
        initial_task: str,
        initial_confidence: float,
    ) -> RoutingDecision:
        """
        Analyze query and decide optimal routing.
        
        Args:
            query: User's query
            initial_task: TaskDetector's guess
            initial_confidence: TaskDetector's confidence
            
        Returns:
            RoutingDecision with routing information
        """
        self._routes_analyzed += 1
        
        # Fast path: high confidence, use initial detection
        if initial_confidence >= self.confidence_threshold:
            model = TASK_MODELS.get(initial_task, TASK_MODELS.get("default", OLLAMA_DEFAULT_MODEL))
            return RoutingDecision(
                task=initial_task,
                model=model,
                confidence=initial_confidence,
                reasoning="High confidence from TaskDetector",
            )
        
        # Slow path: use LLM to analyze
        self._llm_routes += 1
        logger.info(f"Low confidence ({initial_confidence:.2f}), using LLM router")
        
        try:
            decision = self._llm_route(query, initial_task, initial_confidence)
            
            if decision.needs_clarification:
                self._clarifications_requested += 1
            
            return decision
            
        except Exception as e:
            logger.error(f"LLM routing failed: {e}")
            # Fallback: use thinking model for safety
            return RoutingDecision(
                task=initial_task,
                model=TASK_MODELS.get("error_debugging", "qwen3:4b"),  # Safe fallback
                confidence=initial_confidence,
                reasoning=f"Router fallback due to error: {e}",
            )
    
    def _llm_route(
        self,
        query: str,
        initial_task: str,
        initial_confidence: float,
    ) -> RoutingDecision:
        """Use LLM to make routing decision."""
        
        # Build prompts
        categories_str = ", ".join(TASK_CATEGORIES)
        system_prompt = ROUTER_SYSTEM_PROMPT.format(categories=categories_str)
        user_prompt = ROUTER_USER_PROMPT.format(
            query=query[:500],  # Truncate long queries
            initial_task=initial_task,
            initial_confidence=initial_confidence,
        )
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Call router model
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.router_model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"num_predict": 300},  # Limit output
                },
                timeout=self.timeout,
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama returned {response.status_code}")
            
            result_text = response.json().get("response", "")
            return self._parse_router_response(result_text, initial_task, initial_confidence)
            
        except requests.Timeout:
            logger.warning("Router timed out, using fallback")
            raise
        except Exception as e:
            logger.error(f"Router call failed: {e}")
            raise
    
    def _parse_router_response(
        self,
        response_text: str,
        fallback_task: str,
        fallback_confidence: float,
    ) -> RoutingDecision:
        """Parse JSON response from router LLM."""
        
        # Try to extract JSON from response
        try:
            # Remove markdown code blocks
            cleaned = re.sub(r'```json\s*', '', response_text)
            cleaned = re.sub(r'```\s*', '', cleaned)
            
            # Find JSON - try multiple patterns
            # Pattern 1: Complete JSON object
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
            
            if not json_match:
                # Pattern 2: Look for any curly braces
                json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            
            if not json_match:
                raise ValueError(f"No JSON found in response: {response_text[:200]}")
            
            json_str = json_match.group()
            data = json.loads(json_str)
            
            # Extract fields with defaults
            task = data.get("task", fallback_task)
            
            # Validate task
            if task not in TASK_CATEGORIES:
                task = fallback_task
            
            confidence = float(data.get("confidence", fallback_confidence))
            is_complex = data.get("is_complex", False)
            
            # Select model based on complexity
            if is_complex:
                model = TASK_MODELS.get("error_debugging", "qwen3:4b")  # Thinking model
            else:
                model = TASK_MODELS.get(task, TASK_MODELS.get("default", "llama3.2:3b"))
            
            return RoutingDecision(
                task=task,
                model=model,
                confidence=confidence,
                reasoning=data.get("reasoning", ""),
                is_multi_intent=data.get("is_multi_intent", False),
                sub_intents=data.get("sub_intents") or [],
                needs_clarification=data.get("needs_clarification", False),
                clarification_prompt=data.get("clarification_prompt", ""),
                is_safe=data.get("is_safe", True),
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse router response: {e}")
            # Return safe fallback
            return RoutingDecision(
                task=fallback_task,
                model=TASK_MODELS.get("error_debugging", "qwen3:4b"),
                confidence=fallback_confidence,
                reasoning=f"Parse error, using safe fallback: {e}",
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            "total_routes": self._routes_analyzed,
            "llm_routes": self._llm_routes,
            "clarifications_requested": self._clarifications_requested,
            "router_model": self.router_model,
            "threshold": self.confidence_threshold,
        }
    
    def __repr__(self) -> str:
        return f"AdaptiveRouter(model={self.router_model}, analyzed={self._routes_analyzed})"


# =============================================================================
# SINGLETON
# =============================================================================

_router_instance: Optional[AdaptiveRouter] = None


def get_router() -> AdaptiveRouter:
    """Get or create the global adaptive router."""
    global _router_instance
    
    if _router_instance is None:
        _router_instance = AdaptiveRouter()
    
    return _router_instance


def reset_router() -> None:
    """Reset router singleton (for testing)."""
    global _router_instance
    _router_instance = None
