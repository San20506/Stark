"""
ALFRED Reasoning Engine
Tree of Thought (ToT) reasoning with tool suggestion and error recovery.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("Alfred.Reasoning")

@dataclass
class Approach:
    """Represents a possible approach to solving a problem."""
    description: str
    tools: List[str]
    confidence: float  # 0.0 to 1.0
    
@dataclass
class ReasoningResult:
    """Result of reasoning process."""
    success: bool
    approach: Optional[Approach]
    response: str
    attempts: int = 0


class ToolSuggester:
    """Suggests tools based on query analysis and learned patterns."""
    
    def __init__(self, tool_registry=None, learning_memory=None):
        self.tool_registry = tool_registry
        self.learning_memory = learning_memory
        logger.info("✅ ToolSuggester initialized")
    
    def suggest(self, query: str) -> List[str]:
        """Suggest tools based on query analysis."""
        query_lower = query.lower()
        suggestions = []
        
        # Pattern-based suggestions
        patterns = {
            "time": ["datetime"],
            "date": ["datetime"],
            "when": ["datetime"],
            "calculate": ["calc"],
            "math": ["calc"],
            "+": ["calc"],
            "-": ["calc"],
            "*": ["calc"],
            "/": ["calc"],
            "remember": ["memory"],
            "recall": ["memory"],
            "what did i": ["memory"],
            "copy": ["clipboard"],
            "paste": ["clipboard"],
            "read": ["file"],
            "write": ["file"],
            "file": ["file"],
            "list": ["file"],
            "notify": ["notify"],
            "alert": ["notify"],
            "screenshot": ["screenshot"],
            "capture": ["screenshot"],
            "open": ["browser"],
            "website": ["browser"],
        }
        
        for keyword, tools in patterns.items():
            if keyword in query_lower:
                suggestions.extend(tools)
        
        # Check learning memory for similar patterns
        if self.learning_memory:
            try:
                pattern = self.learning_memory.search_similar(f"query_type:{query[:30]}")
                if pattern and "tools_used:" in pattern:
                    tools_str = pattern.split("tools_used:")[1]
                    learned_tools = tools_str.split(",")
                    suggestions.extend(learned_tools)
            except Exception as e:
                logger.debug(f"Learning memory search failed: {e}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for tool in suggestions:
            tool = tool.strip()
            if tool and tool not in seen:
                seen.add(tool)
                unique_suggestions.append(tool)
        
        if unique_suggestions:
            logger.info(f"💡 Suggested tools: {unique_suggestions}")
        
        return unique_suggestions


class ReasoningChain:
    """Tree of Thought reasoning with multi-step problem solving."""
    
    def __init__(self, tool_suggester: ToolSuggester):
        self.tool_suggester = tool_suggester
        logger.info("✅ ReasoningChain initialized")
    
    def generate_approaches(self, query: str, n: int = 3) -> List[Approach]:
        """Generate N possible approaches to solve the query."""
        approaches = []
        
        # Get tool suggestions
        suggested_tools = self.tool_suggester.suggest(query)
        
        # Approach 1: Direct tool use
        if suggested_tools:
            approaches.append(Approach(
                description=f"Use {suggested_tools[0]} tool directly",
                tools=suggested_tools[:1],
                confidence=0.8
            ))
        
        # Approach 2: Multi-tool combination
        if len(suggested_tools) > 1:
            approaches.append(Approach(
                description=f"Combine {', '.join(suggested_tools[:2])} tools",
                tools=suggested_tools[:2],
                confidence=0.6
            ))
        
        # Approach 3: Web search fallback
        approaches.append(Approach(
            description="Search web for information",
            tools=["search"],
            confidence=0.5 if suggested_tools else 0.7
        ))
        
        # Sort by confidence
        approaches.sort(key=lambda x: x.confidence, reverse=True)
        
        return approaches[:n]
    
    def evaluate_approach(self, approach: Approach, context: str = "") -> float:
        """Evaluate confidence score for an approach."""
        # For now, just return the approach's confidence
        # In future, could use LLM to evaluate
        return approach.confidence
    
    def format_approach_hint(self, approaches: List[Approach]) -> str:
        """Format approaches as hint for LLM."""
        if not approaches:
            return ""
        
        hint = "SUGGESTED APPROACHES:\n"
        for i, approach in enumerate(approaches, 1):
            hint += f"{i}. {approach.description} (confidence: {approach.confidence:.0%})\n"
        
        return hint


class ErrorRecovery:
    """Handles errors and retries with alternative approaches."""
    
    MAX_RETRIES = 3
    
    def __init__(self):
        logger.info("✅ ErrorRecovery initialized")
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if should retry based on error type and attempt count."""
        if attempt >= self.MAX_RETRIES:
            return False
        
        # Retry on tool errors, not on LLM errors
        retryable_errors = ["ToolError", "TimeoutError", "ConnectionError"]
        return any(err in str(type(error).__name__) for err in retryable_errors)
    
    def get_alternative_prompt(self, original_prompt: str, error: str, attempt: int) -> str:
        """Generate alternative prompt after failure."""
        return f"""Previous approach failed (attempt {attempt}): {error}

Please try a different approach.

Original query: {original_prompt}"""


# Global instances (initialized by main.py)
tool_suggester = None
reasoning_chain = None
error_recovery = ErrorRecovery()
