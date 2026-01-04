"""
ALFRED Intent Router (MCP Pattern)
Implements the modular agentic architecture from the proposed Jarvis system.

Key Concept: Rule-based intent detection BEFORE sending to LLM.
This ensures tools like time/date/weather are ALWAYS called, not left to LLM guessing.
"""

import re
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum


class IntentType(Enum):
    """Categories of user intent - determines which module handles the request."""
    TIME = "time"
    DATE = "date"
    WEATHER = "weather"
    MATH = "math"
    CONVERSION = "conversion"
    TRANSLATION = "translation"
    SUMMARY = "summary"
    TODO = "todo"
    REMINDER = "reminder"
    SEARCH = "search"
    VISION = "vision"
    CODE = "code"
    GREETING = "greeting"
    CONVERSATION = "conversation"  # General fallback


@dataclass
class ParsedIntent:
    """Result of intent parsing."""
    intent_type: IntentType
    confidence: float
    tool: Optional[str]  # Tool to call, if any
    tool_args: Optional[str]  # Arguments for the tool
    requires_llm: bool  # Whether LLM is needed after tool
    raw_query: str


class IntentRouter:
    """
    Rule-based intent parser and router.
    
    Parses user input to determine intent BEFORE invoking LLM.
    This ensures factual queries (time, date, weather) use tools, not LLM guessing.
    """
    
    # Intent patterns: (keywords, IntentType, tool_name, requires_llm)
    INTENT_PATTERNS = [
        # Time - highest priority for time-related queries
        (["what time", "current time", "time now", "what's the time", "whats the time", 
          "tell me the time", "time is it"], IntentType.TIME, "time", False),
        
        # Date
        (["what date", "today's date", "current date", "what day", "which day",
          "date today", "day is it", "day of the week"], IntentType.DATE, "date", False),
        
        # Weather
        (["weather", "temperature", "forecast", "raining", "sunny", "cloudy", 
          "hot today", "cold today"], IntentType.WEATHER, "weather", False),
        
        # Math
        (["calculate", "compute", "solve", "what is", "how much is", "plus", "minus",
          "times", "divided", "multiply", "percent", "percentage", "%", "sqrt", 
          "square root", "sum of", "difference", "product"], IntentType.MATH, "math", False),
        
        # Conversion
        (["convert", "in celsius", "in fahrenheit", "in miles", "in kilometers",
          "to celsius", "to fahrenheit", "to miles", "to km", "pounds to kg",
          "kg to pounds"], IntentType.CONVERSION, "convert", False),
        
        # Translation
        (["translate", "in spanish", "in french", "in german", "in hindi",
          "how do you say", "say in"], IntentType.TRANSLATION, "translate", True),
        
        # Summary
        (["summarize", "summary", "tldr", "brief", "shorten"], IntentType.SUMMARY, "summarize", True),
        
        # Todo/Reminder
        (["todo", "to-do", "task list", "shopping list", "reminder", "remind me",
          "add to list", "make a list"], IntentType.TODO, "todo", True),
        
        # Vision/Screen
        (["screenshot", "screen", "what do you see", "describe screen", "my screen",
          "look at", "analyze image"], IntentType.VISION, "describe_screen", True),
        
        # Search
        (["search", "look up", "find information", "google", "search for"], 
         IntentType.SEARCH, "search", True),
        
        # Greetings (no tool needed)
        (["hello", "hi ", "hey ", "good morning", "good afternoon", "good evening",
          "how are you", "what's up", "whats up"], IntentType.GREETING, None, True),
    ]
    
    def __init__(self):
        """Initialize the intent router."""
        pass
    
    def parse(self, query: str) -> ParsedIntent:
        """
        Parse user query to determine intent and required tool.
        
        Args:
            query: Raw user input
            
        Returns:
            ParsedIntent with detected intent and tool to use
        """
        query_lower = query.lower().strip()
        
        # Check each pattern
        for keywords, intent_type, tool, requires_llm in self.INTENT_PATTERNS:
            for keyword in keywords:
                if keyword in query_lower:
                    # Extract tool arguments if needed
                    tool_args = self._extract_tool_args(query, intent_type)
                    
                    return ParsedIntent(
                        intent_type=intent_type,
                        confidence=0.9,
                        tool=tool,
                        tool_args=tool_args,
                        requires_llm=requires_llm,
                        raw_query=query
                    )
        
        # Default: general conversation (use LLM)
        return ParsedIntent(
            intent_type=IntentType.CONVERSATION,
            confidence=0.5,
            tool=None,
            tool_args=None,
            requires_llm=True,
            raw_query=query
        )
    
    def _extract_tool_args(self, query: str, intent_type: IntentType) -> Optional[str]:
        """Extract arguments for the tool based on intent type."""
        query_lower = query.lower()
        
        if intent_type == IntentType.WEATHER:
            # Extract city name
            # Pattern: "weather in [city]" or "weather for [city]"
            match = re.search(r'weather (?:in|for|at) ([a-zA-Z\s]+)', query_lower)
            if match:
                return match.group(1).strip()
            return None
        
        elif intent_type == IntentType.MATH:
            # Extract the math expression
            # Remove common prefixes
            expr = query_lower
            for prefix in ["calculate", "compute", "solve", "what is", "what's", 
                          "how much is", "find"]:
                expr = expr.replace(prefix, "")
            return expr.strip()
        
        elif intent_type == IntentType.CONVERSION:
            # Extract value and units
            match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)\s+(?:to|in)\s+([a-zA-Z]+)', query_lower)
            if match:
                return f"{match.group(1)} {match.group(2)} to {match.group(3)}"
            return query
        
        elif intent_type == IntentType.TRANSLATION:
            # Extract text and target language
            # Pattern: "translate [text] to [language]" or "[text] in [language]"
            match = re.search(r'translate ["\']?(.+?)["\']?\s+to\s+([a-zA-Z]+)', query_lower)
            if match:
                return f"{match.group(1)}|{match.group(2)}"
            return query
        
        return None
    
    def route_and_execute(self, query: str, tool_registry, benchmark_tools: Dict) -> Tuple[Optional[str], ParsedIntent]:
        """
        Parse intent and execute the appropriate tool.
        
        Args:
            query: User query
            tool_registry: Registry of tools
            benchmark_tools: Dict of benchmark tool functions
            
        Returns:
            Tuple of (tool_result or None, ParsedIntent)
        """
        intent = self.parse(query)
        
        if intent.tool is None:
            return None, intent
        
        # Execute tool
        if intent.tool in benchmark_tools:
            func = benchmark_tools[intent.tool]
            try:
                if intent.tool_args:
                    result = func(intent.tool_args)
                else:
                    result = func()
                return str(result), intent
            except Exception as e:
                return f"Tool error: {e}", intent
        
        return None, intent


# Singleton instance
_router = None

def get_router() -> IntentRouter:
    """Get the singleton intent router."""
    global _router
    if _router is None:
        _router = IntentRouter()
    return _router


# Quick test
if __name__ == "__main__":
    router = IntentRouter()
    
    test_queries = [
        "Hey, what time is it?",
        "What's the weather in London?",
        "Calculate 25 times 4",
        "Hello there!",
        "Convert 100 fahrenheit to celsius",
        "What day is it today?",
        "Tell me a joke",
        "Remind me to call mom",
    ]
    
    print("=" * 60)
    print("Intent Router Test")
    print("=" * 60)
    
    for query in test_queries:
        intent = router.parse(query)
        print(f"\n'{query}'")
        print(f"  → Intent: {intent.intent_type.value}")
        print(f"  → Tool: {intent.tool or 'None (LLM)'}")
        print(f"  → Args: {intent.tool_args or '-'}")
