"""
ALFRED MCP (Master Control Program)
Central Controller implementing the modular agentic architecture.

Based on: "Proposed Architecture for a Local Offline Jarvis AI System"

The MCP:
1. Receives user input
2. Parses intent (rule-based first, then LLM if needed)
3. Routes to specialized modules
4. Aggregates responses
5. Returns final answer

Modules communicate ONLY through the MCP - never directly with each other.
"""

import logging
import os
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger("Alfred.MCP")


class ModuleType(Enum):
    """Types of specialized modules."""
    CONVERSATIONAL = "conversational"
    MEMORY = "memory"
    MATH = "math"
    LOGIC = "logic"
    CODE = "code"
    VISION = "vision"
    TIME_DATE = "time_date"
    WEATHER = "weather"
    SEARCH = "search"
    TASK = "task"


@dataclass
class ModuleResult:
    """Result from a module execution."""
    success: bool
    data: Any
    confidence: float = 0.0
    source_module: ModuleType = None
    error: Optional[str] = None


@dataclass
class MCPResponse:
    """Final response from the MCP."""
    answer: str
    confidence: float
    modules_used: List[ModuleType] = field(default_factory=list)
    execution_time: float = 0.0
    raw_results: Dict[ModuleType, ModuleResult] = field(default_factory=dict)


class MasterControlProgram:
    """
    Central Controller / Task Planner (MCP).
    
    Implements the modular agentic architecture:
    - Rule-based intent detection
    - Module routing
    - Result aggregation
    - Fallback to conversational LLM
    """
    
    # Intent patterns: (keywords, ModuleType, requires_args)
    INTENT_PATTERNS = [
        # Time/Date - highest priority
        (["what time", "current time", "time now", "time is it", "tell me the time"], 
         ModuleType.TIME_DATE, False),
        (["what date", "today's date", "what day", "day is it", "which day"], 
         ModuleType.TIME_DATE, False),
        
        # Weather
        (["weather", "temperature", "forecast", "raining", "sunny"], 
         ModuleType.WEATHER, True),
        
        # Math
        (["calculate", "compute", "solve", "what is", "how much", "plus", "minus",
          "times", "divided", "multiply", "percent", "sqrt", "square root"], 
         ModuleType.MATH, True),
        
        # Vision
        (["screenshot", "screen", "what do you see", "describe screen", "my screen",
          "look at", "analyze image", "capture"], 
         ModuleType.VISION, False),
        
        # Search
        (["search", "look up", "find information", "google"], 
         ModuleType.SEARCH, True),
        
        # Task/Todo
        (["todo", "task list", "shopping list", "reminder", "remind me", "make a list"], 
         ModuleType.TASK, True),
        
        # Code
        (["write code", "python code", "javascript", "function to", "program that",
          "code for", "script that"], 
         ModuleType.CODE, True),
    ]
    
    def __init__(self, llm_client, memory_module=None):
        """
        Initialize the MCP.
        
        Args:
            llm_client: LLM client for conversational fallback
            memory_module: Optional memory/retrieval module
        """
        self.llm = llm_client
        self.memory = memory_module
        self._modules = {}
        self._init_modules()
        
        logger.info("🎛️ MCP initialized")
    
    def _init_modules(self):
        """Initialize all specialized modules."""
        # Import benchmark tools for direct execution
        try:
            from core.benchmark_tools import BENCHMARK_TOOLS
            self._benchmark_tools = BENCHMARK_TOOLS
        except ImportError:
            self._benchmark_tools = {}
            logger.warning("Benchmark tools not available")
        
        # Vision module
        try:
            from agents.vision import get_vision_client
            self._vision_client = get_vision_client()
        except ImportError:
            self._vision_client = None
            logger.warning("Vision module not available")

        # Neuromorphic Memory Integration
        try:
            from memory.neuromorphic_memory import get_neuromorphic_memory
            if self.memory is None:
                self.memory = get_neuromorphic_memory()
                logger.info("🧠 Neuromorphic Memory System initialized")
        except ImportError as e:
            logger.warning(f"Neuromorphic memory unavailable: {e}")
        
        # FastNLU (Primary - Ultra-fast semantic search)
        try:
            from core.fast_nlu import get_fast_nlu
            self._fast_nlu = get_fast_nlu()
            logger.info("✅ FastNLU initialized (semantic search, <10ms)")
        except Exception as e:
            self._fast_nlu = None
            logger.warning(f"FastNLU not available: {e}")
        
        # NLU Intent Detector (Fallback - BiLSTM model)
        try:
            from core.nlu import get_intent_detector
            self._nlu = get_intent_detector(self.llm)
            
            # Try to load trained model (prioritize JARVIS > unified > compact)
            if os.path.exists("models/nlu_jarvis.h5"):
                self._nlu.load_model("models/nlu_jarvis.h5", "data/jarvis/vocab.pkl")
                logger.info("✅ NLU Fallback: JARVIS model (157 intents)")
            elif os.path.exists("models/nlu_unified.h5"):
                self._nlu.load_model("models/nlu_unified.h5", "data/unified/vocab.pkl")
                logger.info("✅ NLU Fallback: unified model (37 intents)")
            else:
                logger.info("✅ NLU Fallback: rule-based mode")
        except ImportError:
            self._nlu = None
            logger.warning("NLU fallback not available")
    
    def process(self, query: str) -> MCPResponse:
        """
        Process a user query through the MCP.
        
        This is the main entry point. It:
        1. Detects intent
        2. Routes to appropriate module(s)
        3. Executes and aggregates results
        4. Returns formatted response
        
        Args:
            query: User's natural language query
            
        Returns:
            MCPResponse with final answer
        """
        start_time = datetime.now()
        modules_used = []
        raw_results = {}
        
        # Step 1: Intent Detection
        # Try FastNLU first (ultra-fast semantic search)
        intent = None
        args = {}
        
        if self._fast_nlu:
            try:
                fast_result = self._fast_nlu.classify(query)
                if fast_result.confidence >= 0.65:
                    # Map FastNLU intent to ModuleType
                    intent = self._map_fast_intent(fast_result.intent)
                    args = {"raw_query": query}
                    logger.info(f"🎯 FastNLU: {fast_result.intent} ({fast_result.confidence:.0%}) [{fast_result.processing_time_ms:.1f}ms]")
            except Exception as e:
                logger.warning(f"FastNLU error: {e}")
        
        # Fall back to BiLSTM/rule-based if FastNLU didn't match
        if not intent:
            intent, args = self._detect_intent(query)
        
        if intent:
            logger.info(f"🎯 Intent detected: {intent.value}")
            
            # Step 2: Route to specialized module
            result = self._execute_module(intent, query, args)
            raw_results[intent] = result
            modules_used.append(intent)
            
            if result.success:
                # Format the response
                answer = self._format_response(intent, result.data)
                elapsed = (datetime.now() - start_time).total_seconds()
                
                return MCPResponse(
                    answer=answer,
                    confidence=result.confidence,
                    modules_used=modules_used,
                    execution_time=elapsed,
                    raw_results=raw_results
                )
        
        # Step 3: Fallback to Conversational LLM
        logger.info("💬 Routing to conversational module")
        modules_used.append(ModuleType.CONVERSATIONAL)
        
        # Retrieve context from memory if available
        context = ""
        if self.memory:
            try:
                # Use associative recall from Neuromorphic Memory
                mem_results = self.memory.recall(query)
                
                # Combine contexts
                ctx_parts = []
                if mem_results.get("working_context"):
                    ctx_parts.append(f"Recent Context:\n{mem_results['working_context']}")
                if mem_results.get("semantic_related"):
                    related = "\n".join([f"- {m['user']} -> {m['assistant']}" for m in mem_results['semantic_related']])
                    ctx_parts.append(f"Related Memories:\n{related}")
                    
                context = "\n\n".join(ctx_parts)
                logger.info(f"🧠 Retrieved context ({len(context)} chars)")
            except Exception as e:
                logger.warning(f"Memory recall failed: {e}")
        
        # Generate response using LLM
        prompt = self._build_conversation_prompt(query, context)
        response = self.llm.generate(prompt)
        
        # Clean up response
        if "<think>" in response:
            response = response.split("</think>")[-1].strip()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Store in Neuromorphic Memory
        if self.memory:
            try:
                self.memory.store_interaction(query, response)
                logger.info("💾 Interaction encoded in distributed memory")
            except Exception as e:
                logger.warning(f"Memory storage failed: {e}")
        
        return MCPResponse(
            answer=response,
            confidence=0.7,
            modules_used=modules_used,
            execution_time=elapsed,
            raw_results=raw_results
        )
    
    def _map_fast_intent(self, fast_intent: str) -> Optional[ModuleType]:
        """Map FastNLU intent string to ModuleType enum."""
        intent_map = {
            # Core utility
            "time": ModuleType.TIME,
            "date": ModuleType.TIME,
            "weather": ModuleType.WEATHER,
            "calculator": ModuleType.CALCULATOR,
            
            # Tasks
            "alarm": ModuleType.REMINDER,
            "reminder": ModuleType.REMINDER,
            
            # Web & Search
            "search_web": ModuleType.WEB_SEARCH,
            "navigate": ModuleType.WEB_SEARCH,
            
            # Desktop control
            "open_app": ModuleType.TIME,  # Will be handled by tools
            "screenshot": ModuleType.TIME,
            "type_text": ModuleType.TIME,
            "click": ModuleType.TIME,
            "close": ModuleType.TIME,
            
            # Media
            "play_music": ModuleType.CONVERSATIONAL,
            "volume": ModuleType.CONVERSATIONAL,
            "stop": ModuleType.CONVERSATIONAL,
            
            # Conversation
            "greeting": ModuleType.CONVERSATIONAL,
            "goodbye": ModuleType.CONVERSATIONAL,
            "thank_you": ModuleType.CONVERSATIONAL,
            "general_conversation": ModuleType.CONVERSATIONAL,
        }
        return intent_map.get(fast_intent)
    
    def _detect_intent(self, query: str) -> Tuple[Optional[ModuleType], Optional[Dict]]:
        """
        Detect intent from query using NLU system.
        
        Returns:
            Tuple of (ModuleType or None, slots dict or None)
        """
        if self._nlu:
            # Use proper NLU intent detection
            nlu_result = self._nlu.detect(query)
            
            # Map NLU intent to ModuleType
            intent_mapping = {
                "get_time": ModuleType.TIME_DATE,
                "get_date": ModuleType.TIME_DATE,
                "get_weather": ModuleType.WEATHER,
                "calculate": ModuleType.MATH,
                "convert_units": ModuleType.MATH,  # Use math module for conversions
                "search_web": ModuleType.SEARCH,
                "create_todo": ModuleType.TASK,
                "take_screenshot": ModuleType.VISION,
                "describe_screen": ModuleType.VISION,
                "generate_code": ModuleType.CODE,
                "general_conversation": None
            }
            
            module_type = intent_mapping.get(nlu_result.intent)
            
            if module_type and nlu_result.confidence >= 0.7:
                logger.info(f"🎯 NLU: {nlu_result.intent} ({nlu_result.confidence:.0%}) | Slots: {nlu_result.slots}")
                return module_type, nlu_result.slots
        
        # Fallback to old pattern matching if NLU not available
        query_lower = query.lower()
        
        for keywords, module_type, requires_args in self.INTENT_PATTERNS:
            for keyword in keywords:
                if keyword in query_lower:
                    args = self._extract_args(query, module_type) if requires_args else None
                    return module_type, {"raw": args} if args else None
        
        return None, None

    
    def _extract_args(self, query: str, module_type: ModuleType) -> Optional[str]:
        """Extract arguments for a module from the query."""
        import re
        query_lower = query.lower()
        
        if module_type == ModuleType.WEATHER:
            match = re.search(r'weather (?:in|for|at) ([a-zA-Z\s]+)', query_lower)
            return match.group(1).strip() if match else "current location"
        
        elif module_type == ModuleType.MATH:
            # Remove common prefixes and filler words
            expr = query_lower
            for prefix in ["calculate", "compute", "solve", "what is", "what's", "how much is", "find"]:
                expr = expr.replace(prefix, "")
            # Remove question marks and common filler
            expr = expr.replace("?", "").replace("the", "").replace("of", "")
            return expr.strip()
        
        elif module_type == ModuleType.SEARCH:
            match = re.search(r'(?:search|look up|find) (?:for )?(.+)', query_lower)
            return match.group(1).strip() if match else query
        
        return query
    
    def _execute_module(self, module_type: ModuleType, query: str, slots: Optional[Dict]) -> ModuleResult:
        """
        Execute a specialized module using NLU slots.
        
        Args:
            module_type: Type of module to execute
            query: Original query
            slots: Extracted slots from NLU
        """
        
        try:
            if module_type == ModuleType.TIME_DATE:
                return self._execute_time_date(query)
            
            elif module_type == ModuleType.WEATHER:
                city = slots.get("city") if slots else None
                return self._execute_weather(city or "current location")
            
            elif module_type == ModuleType.MATH:
                expression = slots.get("expression") if slots else None
                if not expression and slots:
                    expression = slots.get("raw")  # Fallback for old pattern matching
                return self._execute_math(expression or query)
            
            elif module_type == ModuleType.VISION:
                return self._execute_vision(query)
            
            elif module_type == ModuleType.SEARCH:
                search_query = slots.get("query") if slots else None
                if not search_query and slots:
                    search_query = slots.get("raw")
                return self._execute_search(search_query or query)
            
            elif module_type == ModuleType.TASK:
                return self._execute_task(query)
            
            elif module_type == ModuleType.CODE:
                return self._execute_code(query)
            
            else:
                return ModuleResult(success=False, data=None, error="Module not implemented")
                
        except Exception as e:
            logger.error(f"Module execution error: {e}")
            return ModuleResult(success=False, data=None, error=str(e))
    
    def _execute_time_date(self, query: str) -> ModuleResult:
        """Execute time/date module."""
        query_lower = query.lower()
        
        if any(w in query_lower for w in ["time", "clock"]):
            if "time" in self._benchmark_tools:
                result = self._benchmark_tools["time"]()
                return ModuleResult(success=True, data=result, confidence=0.99, source_module=ModuleType.TIME_DATE)
        
        if any(w in query_lower for w in ["date", "day", "today"]):
            if "date" in self._benchmark_tools:
                result = self._benchmark_tools["date"]()
                return ModuleResult(success=True, data=result, confidence=0.99, source_module=ModuleType.TIME_DATE)
        
        # Fallback: try both
        if "time" in self._benchmark_tools:
            result = self._benchmark_tools["time"]()
            return ModuleResult(success=True, data=result, confidence=0.95, source_module=ModuleType.TIME_DATE)
        
        return ModuleResult(success=False, data=None, error="Time/date tools not available")
    
    def _execute_weather(self, city: str) -> ModuleResult:
        """Execute weather module."""
        if "weather" in self._benchmark_tools:
            result = self._benchmark_tools["weather"](city)
            return ModuleResult(success=True, data=result, confidence=0.9, source_module=ModuleType.WEATHER)
        return ModuleResult(success=False, data=None, error="Weather tool not available")
    
    def _execute_math(self, expression: str) -> ModuleResult:
        """Execute math module."""
        if "math" in self._benchmark_tools:
            result = self._benchmark_tools["math"](expression)
            return ModuleResult(success=True, data=result, confidence=0.95, source_module=ModuleType.MATH)
        return ModuleResult(success=False, data=None, error="Math tool not available")
    
    def _execute_vision(self, query: str) -> ModuleResult:
        """Execute vision module."""
        if self._vision_client:
            result = self._vision_client.describe_screen()
            if result.success:
                return ModuleResult(success=True, data=result.description, confidence=result.confidence, source_module=ModuleType.VISION)
            return ModuleResult(success=False, data=None, error=result.error)
        return ModuleResult(success=False, data=None, error="Vision module not available")
    
    def _execute_search(self, query: str) -> ModuleResult:
        """Execute search module."""
        if "search" in self._benchmark_tools:
            result = self._benchmark_tools["search"](query)
            return ModuleResult(success=True, data=result, confidence=0.8, source_module=ModuleType.SEARCH)
        return ModuleResult(success=False, data=None, error="Search tool not available")
    
    def _execute_task(self, query: str) -> ModuleResult:
        """Execute task/todo module."""
        if "todo" in self._benchmark_tools:
            result = self._benchmark_tools["todo"](query)
            return ModuleResult(success=True, data=result, confidence=0.85, source_module=ModuleType.TASK)
        return ModuleResult(success=False, data=None, error="Task tool not available")
    
    def _execute_code(self, query: str) -> ModuleResult:
        """Execute code generation module - uses LLM with code prompt."""
        prompt = f"""You are a code generation assistant. Write clean, working code for this request:

{query}

Provide the code with brief comments. Keep it concise."""
        
        response = self.llm.generate(prompt)
        if "<think>" in response:
            response = response.split("</think>")[-1].strip()
        
        return ModuleResult(success=True, data=response, confidence=0.75, source_module=ModuleType.CODE)
    
    def _format_response(self, module_type: ModuleType, data: Any) -> str:
        """Format module output into human-readable response."""
        
        if module_type == ModuleType.TIME_DATE:
            if isinstance(data, dict):
                if "time" in data:
                    return f"The current time is {data['time']} ({data.get('timezone', '')})."
                elif "date" in data:
                    return f"Today is {data.get('weekday', '')}, {data['date']}."
            return str(data)
        
        elif module_type == ModuleType.WEATHER:
            if isinstance(data, dict):
                if "error" in data:
                    return f"Sorry, I couldn't get the weather: {data['error']}"
                return f"Weather in {data.get('city', 'your area')}: {data.get('temperature', 'N/A')}, {data.get('condition', '')}. Humidity: {data.get('humidity', 'N/A')}"
            return str(data)
        
        elif module_type == ModuleType.MATH:
            if isinstance(data, dict):
                if "error" in data:
                    return f"Math error: {data['error']}"
                return f"The answer is: {data.get('result', data.get('formatted', str(data)))}"
            return str(data)
        
        elif module_type == ModuleType.VISION:
            return f"I can see: {data}"
        
        elif module_type == ModuleType.SEARCH:
            if isinstance(data, dict) and "results" in data:
                results = data["results"][:3]
                if results:
                    formatted = "\n".join([f"• {r.get('title', 'Result')}: {r.get('snippet', '')[:100]}" for r in results])
                    return f"Here's what I found:\n{formatted}"
                return "No results found."
            return str(data)
        
        elif module_type == ModuleType.TASK:
            if isinstance(data, dict) and "todo_list" in data:
                todos = data["todo_list"]
                formatted = "\n".join([f"{i+1}. {t.get('task', t)}" for i, t in enumerate(todos)])
                return f"Here's your list:\n{formatted}"
            return str(data)
        
        elif module_type == ModuleType.CODE:
            return data
        
        return str(data)
    
    def _build_conversation_prompt(self, query: str, context: str = "") -> str:
        """Build prompt for conversational fallback."""
        return f"""You are ALFRED, a helpful AI assistant. Be friendly, concise, and helpful.

{f"Context from memory: {context}" if context else ""}

User: {query}

Respond naturally and helpfully:"""


# Singleton
_mcp = None

def get_mcp(llm_client=None, memory_module=None) -> MasterControlProgram:
    """Get or create the MCP singleton."""
    global _mcp
    if _mcp is None:
        if llm_client is None:
            raise ValueError("LLM client required for first initialization")
        _mcp = MasterControlProgram(llm_client, memory_module)
    return _mcp


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test without LLM (just module routing)
    print("=" * 60)
    print("MCP Intent Detection Test")
    print("=" * 60)
    
    mcp = MasterControlProgram.__new__(MasterControlProgram)
    mcp.INTENT_PATTERNS = MasterControlProgram.INTENT_PATTERNS
    
    test_queries = [
        "What time is it?",
        "What's the weather in Tokyo?",
        "Calculate 25 * 4",
        "Take a screenshot",
        "Tell me a joke",
    ]
    
    for query in test_queries:
        intent, args = mcp._detect_intent(query)
        print(f"\n'{query}'")
        print(f"  → Intent: {intent.value if intent else 'CONVERSATIONAL'}")
        print(f"  → Args: {args or '-'}")
