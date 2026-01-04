"""
ALFRED COGNITIVE ENGINE (The Brain)
Implements:
- Tier 3: Multi-Agent Task Planning
- Tier 5: Goal-Seeking Autonomous Agent
- Tier 6: Fully Autonomous Execution
- Tier 7: Reasoning Under Uncertainty
- ReAct: Reason + Act loops with observable traces
- Planner-Executor: CoT planning with dynamic replanning
"""

import logging
import uuid
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger("Alfred.Brain")


# =============================================================================
# ReAct DATA STRUCTURES
# =============================================================================

@dataclass
class ReActStep:
    """Single step in a ReAct reasoning loop."""
    step_num: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[str] = None
    observation: Optional[str] = None
    confidence: float = 0.0  # 0-1 confidence score
    
    def __str__(self) -> str:
        # Confidence indicator
        if self.confidence >= 0.8:
            conf_str = f"⭐⭐⭐ {self.confidence:.2f}"
        elif self.confidence >= 0.5:
            conf_str = f"⭐⭐ {self.confidence:.2f}"
        else:
            conf_str = f"⭐ {self.confidence:.2f}"
        
        lines = [f"[Step {self.step_num}] (Confidence: {conf_str})"]
        lines.append(f"  💭 Thought: {self.thought}")
        if self.action:
            lines.append(f"  🔧 Action: {self.action}")
            lines.append(f"  📥 Input: {self.action_input}")
        if self.observation:
            lines.append(f"  👁️ Observation: {self.observation[:200]}...")
        return "\n".join(lines)


@dataclass
class ReActTrace:
    """Complete reasoning trace from a ReAct execution."""
    query: str
    steps: List[ReActStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    overall_confidence: float = 0.0  # Aggregated confidence score
    
    def __str__(self) -> str:
        lines = [f"=== ReAct Trace: {self.query[:50]}... ==="]
        for step in self.steps:
            lines.append(str(step))
        if self.final_answer:
            lines.append(f"\n✅ Final Answer: {self.final_answer}")
            
            # Overall confidence display
            if self.overall_confidence >= 0.8:
                conf_level = "HIGH"
            elif self.overall_confidence >= 0.5:
                conf_level = "MEDIUM"
            else:
                conf_level = "LOW"
            lines.append(f"📊 Overall Confidence: {self.overall_confidence:.2f} ({conf_level})")
        if self.error:
            lines.append(f"\n❌ Error: {self.error}")
        return "\n".join(lines)

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

class Task:
    """A single unit of work in a plan."""
    def __init__(self, description: str, tool: Optional[str] = None):
        self.id = str(uuid.uuid4())[:8]
        self.description = description
        self.tool = tool
        self.status = TaskStatus.PENDING
        self.result = None
        self.dependencies = []

class Goal:
    """High-level user objective."""
    def __init__(self, description: str):
        self.id = str(uuid.uuid4())[:8]
        self.description = description
        self.tasks: List[Task] = []
        self.created_at = time.time()
        self.status = TaskStatus.IN_PROGRESS
        self.context = {}  # Shared memory for this goal

class CognitiveEngine:
    """
    The central brain orchestrating perception, planning, and action.
    
    Now with ReAct (Reason + Act) loops and Planner-Executor architecture.
    """
    
    # ReAct Configuration
    REACT_MAX_STEPS_HARD_CAP = 10
    REACT_DEFAULT_STEPS = 6
    REACT_MAX_REPLANS = 2
    
    def __init__(self, tool_registry, llm_client, verbose_react: bool = True):
        self.tool_registry = tool_registry
        self.llm = llm_client
        self.verbose_react = verbose_react  # Print traces to console
        
        # Initialize Memory (Tier 1)
        from agents.memory import MemorySystem
        self.memory = MemorySystem()
        
        self.active_goals: List[Goal] = []
        self._react_scratchpad: List[str] = []  # Intermediate reasoning
        
        logger.info(f"🧠 Cognitive Engine Online (User: {self.memory.profile['name']})")
        logger.info(f"   ReAct: max_steps={self.REACT_DEFAULT_STEPS}, replans={self.REACT_MAX_REPLANS}")

    def perceive(self, input_text: str) -> str:
        """
        Tier 1: NLU & Intent Classification.
        Decides if this is a simple query, a complex goal, or a command.
        """
        # Store interaction
        self.memory.add_interaction("user", input_text)
        
        # Simple heuristic for now, can be LLM-based later
        if any(w in input_text.lower() for w in ["plan", "project", "research", "create a", "how do i"]):
            return "complex_goal"
        return "direct_command"

    # =========================================================================
    # ReAct (REASON + ACT) IMPLEMENTATION
    # =========================================================================
    
    def _format_tool_response(self, intent_type, tool_result: str) -> str:
        """Format raw tool output into a human-friendly response."""
        try:
            # Parse the tool result if it's a dict-like string
            import ast
            data = ast.literal_eval(tool_result)
            
            if intent_type.value == "time":
                return f"The current time is {data.get('time', 'unknown')} ({data.get('timezone', '')})."
            elif intent_type.value == "date":
                return f"Today is {data.get('weekday', '')}, {data.get('date', '')}."
            elif intent_type.value == "weather":
                return f"Weather in {data.get('city', 'your location')}: {data.get('temperature', 'N/A')}, {data.get('condition', '')}."
            elif intent_type.value == "math":
                return f"The result is: {data.get('result', data.get('formatted', tool_result))}"
            else:
                return str(data)
        except:
            return tool_result

    
    def react_execute(self, query: str, max_steps: Optional[int] = None) -> ReActTrace:
        """
        Execute a query using ReAct (Reason + Act) loop.
        
        The agent alternates between:
        - Thought: Natural language reasoning about what to do
        - Action: Tool call or final answer
        - Observation: Result from the action
        
        Args:
            query: The user query or task to solve
            max_steps: Maximum reasoning steps (default: REACT_DEFAULT_STEPS)
            
        Returns:
            ReActTrace with all reasoning steps and final answer
        """
        max_steps = min(max_steps or self.REACT_DEFAULT_STEPS, self.REACT_MAX_STEPS_HARD_CAP)
        trace = ReActTrace(query=query)
        self._react_scratchpad = []
        
        # ===== MCP PATTERN: Intent-based routing BEFORE LLM =====
        # This ensures factual queries (time, date, weather) use tools, not LLM guessing
        try:
            from core.intent_router import get_router, IntentType
            from core.benchmark_tools import BENCHMARK_TOOLS
            
            router = get_router()
            tool_result, intent = router.route_and_execute(query, self.tool_registry, BENCHMARK_TOOLS)
            
            if tool_result and not intent.requires_llm:
                # Direct tool response - no LLM needed
                trace.final_answer = self._format_tool_response(intent.intent_type, tool_result)
                trace.success = True
                trace.overall_confidence = 0.95
                
                step = ReActStep(
                    step_num=1,
                    thought=f"User asked about {intent.intent_type.value}. Using {intent.tool} tool.",
                    action=intent.tool,
                    action_input=intent.tool_args or "",
                    observation=tool_result,
                    confidence=0.95
                )
                trace.steps.append(step)
                
                if self.verbose_react:
                    print(f"\n⚡ Fast path: {intent.intent_type.value} → {intent.tool}")
                    print(f"✅ {trace.final_answer}")
                
                return trace
        except ImportError:
            pass  # Intent router not available, continue with ReAct
        
        # Build tool descriptions for prompt
        tool_list = self._get_react_tool_descriptions()
        
        # Initial prompt
        prompt = self._build_react_prompt(query, tool_list)
        
        if self.verbose_react:
            print(f"\n{'='*60}")
            print(f"🧠 ReAct Loop: {query[:50]}...")
            print(f"{'='*60}")
        
        for step_num in range(1, max_steps + 1):
            # Get LLM response
            response = self.llm.generate(prompt)
            
            # Clean thinking tokens
            if "<think>" in response:
                response = response.split("</think>")[-1].strip()
            
            # Parse the response
            thought, action, action_input, final_answer = self._parse_react_response(response)
            
            step = ReActStep(
                step_num=step_num,
                thought=thought,
                action=action,
                action_input=action_input
            )
            
            # Log step
            logger.info(f"[ReAct Step {step_num}] Thought: {thought[:100]}...")
            if self.verbose_react:
                print(f"\n[Step {step_num}]")
                print(f"  💭 Thought: {thought}")
            
            # Check for final answer
            if final_answer:
                trace.final_answer = final_answer
                trace.success = True
                trace.steps.append(step)
                
                if self.verbose_react:
                    print(f"\n✅ Final Answer: {final_answer}")
                
                logger.info(f"[ReAct] Completed in {step_num} steps")
                break
            
            # Execute action
            if action:
                if self.verbose_react:
                    print(f"  🔧 Action: {action}")
                    print(f"  📥 Input: {action_input}")
                
                tool_success = True
                try:
                    observation = self._execute_react_action(action, action_input)
                    step.observation = observation
                except Exception as e:
                    observation = f"Error: {str(e)}"
                    step.observation = observation
                    tool_success = False
                
                if self.verbose_react:
                    print(f"  👁️ Observation: {observation[:200]}...")
                
                # Calculate step confidence
                step.confidence = self._calculate_step_confidence(step, tool_success, observation)
                
                if self.verbose_react:
                    conf_indicator = "⭐⭐⭐" if step.confidence >= 0.8 else "⭐⭐" if step.confidence >= 0.5 else "⭐"
                    print(f"  📊 Confidence: {step.confidence:.2f} {conf_indicator}")
                
                # Add observation to prompt for next iteration
                self._react_scratchpad.append(
                    f"Thought: {thought}\nAction: {action}\nAction Input: {action_input}\nObservation: {observation}"
                )
                prompt = self._build_react_prompt(query, tool_list, self._react_scratchpad)
            else:
                # No action taken, calculate confidence based on thought only
                step.confidence = self._calculate_step_confidence(step, True, "")
            
            trace.steps.append(step)
        
        # Calculate final answer confidence if we have one
        if trace.final_answer and trace.steps:
            final_conf = self._get_llm_confidence(
                trace.steps[-1].thought if trace.steps else "",
                trace.final_answer
            )
            # Update last step confidence with final answer confidence
            if trace.steps:
                trace.steps[-1].confidence = max(trace.steps[-1].confidence, final_conf)
        
        # Calculate overall confidence
        trace.overall_confidence = self._calculate_overall_confidence(trace)
        
        # SELF-VERIFICATION LOOP
        # If confidence is low, trigger verification
        VERIFICATION_THRESHOLD = 0.6
        
        if trace.final_answer and trace.overall_confidence < VERIFICATION_THRESHOLD:
            if self.verbose_react:
                print(f"\n🔍 Low confidence detected ({trace.overall_confidence:.2f}). Running self-verification...")
            
            verification_result = self._verify_answer(query, trace.final_answer, trace)
            
            if verification_result['needs_revision']:
                if self.verbose_react:
                    print(f"⚠️ Issues found: {verification_result['issues']}")
                    print(f"🔄 Attempting to improve answer...")
                
                # Try to improve the answer
                improved_answer = self._improve_answer(
                    query, 
                    trace.final_answer, 
                    verification_result['issues']
                )
                
                if improved_answer:
                    trace.final_answer = improved_answer
                    # Recalculate confidence with improved answer
                    trace.overall_confidence = min(trace.overall_confidence * 1.3, 0.85)
                    
                    if self.verbose_react:
                        print(f"✅ Answer improved. New confidence: {trace.overall_confidence:.2f}")
            else:
                if self.verbose_react:
                    print(f"✅ Verification passed")
        
        # If we exhausted steps without final answer
        if not trace.final_answer:
            trace.error = f"Max steps ({max_steps}) reached without final answer"
            trace.success = False
            if self.verbose_react:
                print(f"\n⚠️ Max steps reached. Generating best-effort answer...")
            
            # Try to get a final answer anyway
            final_prompt = f"Based on your reasoning so far, provide a Final Answer to: {query}"
            final_response = self.llm.generate(final_prompt)
            trace.final_answer = final_response.strip()
            
            # Recalculate overall confidence with the fallback answer
            trace.overall_confidence = self._calculate_overall_confidence(trace) * 0.7  # Penalty for max steps
        
        # Display overall confidence in verbose mode
        if self.verbose_react and trace.final_answer:
            conf_level = "HIGH" if trace.overall_confidence >= 0.8 else "MEDIUM" if trace.overall_confidence >= 0.5 else "LOW"
            print(f"\n📊 Overall Confidence: {trace.overall_confidence:.2f} ({conf_level})")
        
        return trace
    
    def _get_react_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for ReAct prompt."""
        lines = ["Available tools:"]
        for name, info in self.tool_registry.tools.items():
            desc = info.get('description', 'No description')
            lines.append(f"  - {name}: {desc}")
        
        # Add benchmark tools with descriptions
        try:
            from core.benchmark_tools import BENCHMARK_TOOLS
            # Essential tools with descriptions
            essential_tools = {
                "time": "Get current time and timezone",
                "date": "Get current date and weekday",
                "weather": "Get weather for a city",
                "math": "Solve math expressions",
                "convert": "Convert units (temperature, distance, etc.)",
                "summarize": "Summarize text",
                "translate": "Translate text to another language",
                "search": "Search the web",
                "screenshot": "Take a screenshot",
                "describe_screen": "Describe what's on screen",
            }
            lines.append("\nBenchmark tools:")
            for name, desc in essential_tools.items():
                if name in BENCHMARK_TOOLS:
                    lines.append(f"  - {name}: {desc}")
        except ImportError:
            pass
        
        return "\n".join(lines)

    
    def _build_react_prompt(self, query: str, tool_list: str, scratchpad: List[str] = None) -> str:
        """Build the ReAct prompt with optional scratchpad."""
        scratchpad_text = "\n\n".join(scratchpad) if scratchpad else ""
        
        prompt = f"""You are ALFRED, a helpful AI assistant created to help users with their tasks.

ABOUT YOU:
- You are friendly, helpful, and knowledgeable
- You can answer questions, help with tasks, and use tools when needed
- You should give direct, concise answers
- If you don't know something, say so honestly
- You speak naturally like a helpful assistant

{tool_list}

RESPONSE FORMAT:
When you need to use a tool:
Thought: [Your brief reasoning]
Action: [tool_name]
Action Input: [arguments]

When you can answer directly:
Thought: [Your brief reasoning]
Final Answer: [Your helpful response to the user]

IMPORTANT RULES:
1. Give ONE clear answer, not multiple attempts
2. Keep thoughts brief (1-2 sentences)
3. Be direct and helpful
4. For FACTUAL information (time, date, weather, calculations), ALWAYS use a tool - do NOT guess
5. Use 'time' tool for current time, 'date' tool for current date, 'weather' for weather

USER QUESTION: {query}
{f"Previous context:{chr(10)}{scratchpad_text}" if scratchpad_text else ""}

Your response:"""
        return prompt

    
    def _parse_react_response(self, response: str) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        """
        Parse LLM response into thought, action, action_input, final_answer.
        Handles malformed responses from smaller models.
        """
        thought = ""
        action = None
        action_input = None
        final_answer = None
        
        # Clean up response - remove markdown formatting
        response = response.replace("**", "").strip()
        
        # Extract Thought (first occurrence only)
        thought_match = re.search(r'Thought:\s*(.+?)(?=\n(?:Action|Final Answer):|$)', response, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()
            # Clean up - take only first sentence if too long
            if len(thought) > 300:
                sentences = thought.split('.')
                thought = sentences[0] + '.' if sentences else thought[:300]
        
        # Check for Final Answer (FIRST occurrence only, limit length)
        final_match = re.search(r'Final Answer:\s*(.+?)(?=\n(?:Thought|Action|Wait|So):|$)', response, re.DOTALL | re.IGNORECASE)
        if final_match:
            final_answer = final_match.group(1).strip()
            # Limit to reasonable length
            if len(final_answer) > 500:
                # Take first paragraph or sentence
                paragraphs = final_answer.split('\n\n')
                final_answer = paragraphs[0] if paragraphs else final_answer[:500]
            
            # Remove any trailing "Wait" or meta-commentary
            final_answer = re.split(r'\n\s*(?:Wait|So|Actually|Let me)', final_answer, maxsplit=1)[0].strip()
            
            return thought, None, None, final_answer
        
        # Extract Action and Action Input
        action_match = re.search(r'Action:\s*(\w+)', response, re.IGNORECASE)
        input_match = re.search(r'Action Input:\s*(.+?)(?=\n(?:Thought|Action|Observation|Final):|$)', response, re.DOTALL | re.IGNORECASE)
        
        if action_match:
            action = action_match.group(1).strip()
        if input_match:
            action_input = input_match.group(1).strip()
            # Clean up action input
            if len(action_input) > 200:
                action_input = action_input[:200]
        
        return thought, action, action_input, final_answer
    
    def _execute_react_action(self, action: str, action_input: str) -> str:
        """Execute a tool action and return observation."""
        action_lower = action.lower()
        
        # Try benchmark tools first
        try:
            from core.benchmark_tools import BENCHMARK_TOOLS
            if action_lower in BENCHMARK_TOOLS:
                func = BENCHMARK_TOOLS[action_lower]
                # Try to parse action_input as argument
                try:
                    result = func(action_input)
                except TypeError:
                    # Function takes no args or different args
                    result = func()
                return str(result)
        except (ImportError, KeyError):
            pass
        
        # Try tool registry
        if action_lower in self.tool_registry.tools:
            tool_call = f'<tool:{action_lower} args="{action_input}"/>'
            result = self.tool_registry.execute(tool_call)
            return str(result) if result else "Tool executed successfully"
        
        # Fallback: use LLM for thinking tasks
        if action_lower in ["think", "reason", "analyze"]:
            result = self.llm.generate(f"Analyze: {action_input}")
            return result
        
        return f"Unknown action: {action}. Available: {list(self.tool_registry.tools.keys())}"

    # =========================================================================
    # CONFIDENCE SCORING
    # =========================================================================
    
    def _get_llm_confidence(self, thought: str, final_answer: Optional[str] = None) -> float:
        """
        Ask LLM to self-assess confidence in its reasoning.
        
        Returns:
            Float between 0.0 and 1.0
        """
        if final_answer:
            prompt = f"""Rate your confidence in this answer on a scale of 0-10.
            
Question context: {thought}
Your answer: {final_answer}

Respond with ONLY a number from 0-10. No explanation."""
        else:
            prompt = f"""Rate your confidence in this reasoning step on a scale of 0-10.

Your thought: {thought}

Respond with ONLY a number from 0-10. No explanation."""
        
        try:
            response = self.llm.generate(prompt).strip()
            # Extract first number found
            import re
            match = re.search(r'(\d+(?:\.\d+)?)', response)
            if match:
                score = float(match.group(1))
                # Normalize to 0-1
                return min(max(score / 10.0, 0.0), 1.0)
        except Exception as e:
            logger.warning(f"Failed to get LLM confidence: {e}")
        
        return 0.5  # Default to medium confidence
    
    def _calculate_step_confidence(
        self, 
        step: ReActStep, 
        tool_success: bool,
        observation: str = ""
    ) -> float:
        """
        Calculate confidence for a single ReAct step using hybrid approach.
        
        Factors:
        - LLM self-assessment (50%)
        - Tool success (30%)
        - Thought quality heuristic (20%)
        
        Returns:
            Float between 0.0 and 1.0
        """
        # 1. Get LLM self-assessment
        llm_conf = self._get_llm_confidence(step.thought)
        
        # 2. Tool success factor
        tool_factor = 1.0 if tool_success else 0.5
        
        # Check for error indicators in observation
        if observation and any(err in observation.lower() for err in ['error', 'failed', 'unknown']):
            tool_factor *= 0.7
        
        # 3. Thought quality heuristic
        # Longer, more detailed thoughts indicate higher confidence
        thought_length = len(step.thought)
        if thought_length > 100:
            thought_quality = 1.0
        elif thought_length > 50:
            thought_quality = 0.8
        elif thought_length > 20:
            thought_quality = 0.6
        else:
            thought_quality = 0.4
        
        # Check for uncertainty markers
        uncertainty_markers = ['maybe', 'might', 'possibly', 'unsure', 'not sure', 'unclear']
        if any(marker in step.thought.lower() for marker in uncertainty_markers):
            thought_quality *= 0.7
        
        # Weighted combination
        confidence = (
            0.5 * llm_conf +
            0.3 * tool_factor +
            0.2 * thought_quality
        )
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_overall_confidence(self, trace: ReActTrace) -> float:
        """
        Aggregate step confidences into overall trace confidence.
        
        Factors:
        - Average step confidence (70%)
        - Success status (20%)
        - Efficiency (10%)
        
        Returns:
            Float between 0.0 and 1.0
        """
        if not trace.steps:
            return 0.0
        
        # Average step confidence
        avg_step_conf = sum(s.confidence for s in trace.steps) / len(trace.steps)
        
        # Success factor
        success_factor = 1.0 if trace.success else 0.6
        
        # Efficiency factor (fewer steps relative to max = better)
        efficiency = 1.0 - (len(trace.steps) / self.REACT_MAX_STEPS_HARD_CAP)
        efficiency = max(0.0, efficiency)  # Ensure non-negative
        
        # Weighted combination
        overall = (
            0.7 * avg_step_conf +
            0.2 * success_factor +
            0.1 * efficiency
        )
        
        return max(0.0, min(1.0, overall))

    def _verify_answer(self, query: str, answer: str, trace: ReActTrace) -> Dict[str, Any]:
        """
        Verify the quality of an answer using self-critique.
        
        Returns:
            Dict with 'needs_revision' (bool) and 'issues' (list)
        """
        verification_prompt = f"""You are verifying the quality of an answer. Be critical and thorough.

QUESTION: {query}

ANSWER: {answer}

REASONING STEPS:
{chr(10).join([f"{i+1}. {s.thought[:100]}" for i, s in enumerate(trace.steps)])}

Check for these issues:
1. Factual errors or inconsistencies
2. Incomplete information
3. Logical flaws in reasoning
4. Unsupported claims
5. Ambiguity or vagueness

Respond in this format:
VERDICT: [PASS or FAIL]
ISSUES: [List any issues found, or "None"]
"""
        
        try:
            response = self.llm.generate(verification_prompt)
            
            # Parse response
            needs_revision = "FAIL" in response.upper()
            
            # Extract issues
            issues = []
            if "ISSUES:" in response:
                issues_text = response.split("ISSUES:")[-1].strip()
                if issues_text.lower() != "none" and issues_text:
                    issues = [issues_text[:200]]  # Truncate for brevity
            
            return {
                'needs_revision': needs_revision,
                'issues': issues
            }
        except Exception as e:
            logger.warning(f"Verification failed: {e}")
            return {'needs_revision': False, 'issues': []}
    
    def _improve_answer(self, query: str, original_answer: str, issues: List[str]) -> Optional[str]:
        """
        Attempt to improve an answer based on identified issues.
        
        Returns:
            Improved answer or None if improvement failed
        """
        improvement_prompt = f"""The following answer has issues. Improve it.

QUESTION: {query}

ORIGINAL ANSWER: {original_answer}

IDENTIFIED ISSUES:
{chr(10).join([f"- {issue}" for issue in issues])}

Provide an IMPROVED answer that addresses these issues. If you cannot confidently improve it, respond with "UNABLE TO IMPROVE" and explain why.

IMPROVED ANSWER:"""
        
        try:
            response = self.llm.generate(improvement_prompt).strip()
            
            # Check if LLM declined to improve
            if "UNABLE TO IMPROVE" in response.upper():
                return None
            
            # Clean up response
            if "<think>" in response:
                response = response.split("</think>")[-1].strip()
            
            # Return improved answer if it's substantively different
            if len(response) > 20 and response != original_answer:
                return response
            
        except Exception as e:
            logger.warning(f"Answer improvement failed: {e}")
        
        return None

    def formulate_plan(self, goal_text: str) -> Goal:
        """
        Tier 3/5: Autonomously break down a goal into a plan.
        """
        logger.info(f"🤔 Planning goal: {goal_text}")
        
        # Get Context
        context = self.memory.retrieve_context(goal_text)
        
        # PROMPT for the planner (Simplified for DeepSeek)
        tools_desc = list(self.tool_registry.tools.keys())
        prompt = f"""
        GOAL: {goal_text}
        CONTEXT: {context}
        TOOLS: {tools_desc}
        
        List the steps to achieve this goal. One step per line.
        Format: - Description [Tool]
        
        Example:
        - Search for market trends [search]
        - Summarize the findings [summarize]
        - Create a report [write_file]
        """
        
        try:
            response = self.llm.generate(prompt)
            # Remove thinking trace
            if "<think>" in response:
                response = response.split("</think>")[-1]
            
            goal = Goal(goal_text)
            
            # Simple line parsing
            import re
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    # Extract tool if present [tool]
                    tool_match = re.search(r'\[(.*?)\]', line)
                    tool = tool_match.group(1) if tool_match else None
                    desc = re.sub(r'\[.*?\]', '', line).strip("- *")
                    
                    if desc:
                        t = Task(desc, tool)
                        goal.tasks.append(t)
            
            self.active_goals.append(goal)
            
            # SMARTER: Self-Reflection (Tier 7)
            if len(goal.tasks) > 0:
                goal = self.refine_plan(goal)
            
            return goal
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return Goal(goal_text)

    def refine_plan(self, goal: Goal) -> Goal:
        """
        Tier 7: Self-Critique & Improvement.
        Ask LLM to review and improve the plan.
        """
        logger.info("🔍 Refining plan (self-critique)...")
        
        # Serialize current plan
        plan_text = "\n".join([f"{i+1}. {t.description}" for i, t in enumerate(goal.tasks)])
        
        critique_prompt = f"""
        GOAL: {goal.description}
        CURRENT PLAN:
        {plan_text}
        
        Review this plan. Is it:
        1. Complete (covers all steps)?
        2. Ordered correctly?
        3. Missing any critical steps?
        
        If improvements needed, output IMPROVED plan as bullet list.
        If plan is good, output: APPROVED
        """
        
        response = self.llm.generate(critique_prompt)
        
        # If LLM suggests improvements, re-parse
        if "APPROVED" not in response and ("-" in response or "*" in response):
            logger.info("✨ Plan improved via self-critique")
            goal.tasks.clear()
            
            import re
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    tool_match = re.search(r'\[(.*?)\]', line)
                    tool = tool_match.group(1) if tool_match else None
                    desc = re.sub(r'\[.*?\]', '', line).strip("- *")
                    
                    if desc:
                        t = Task(desc, tool)
                        goal.tasks.append(t)
        
        return goal # Return empty goal on failure

    # =========================================================================
    # PLANNER-EXECUTOR WITH DYNAMIC REPLANNING
    # =========================================================================
    
    def execute_goal_with_replan(self, goal: Goal, max_replans: Optional[int] = None) -> Tuple[TaskStatus, str]:
        """
        Execute a goal with ReAct-style execution and dynamic replanning on failure.
        
        This is the JARVIS-style planner-executor loop:
        1. Execute each task using ReAct reasoning
        2. On failure, analyze and generate alternative plan
        3. Retry up to max_replans times
        4. Return rich error on final failure
        
        Args:
            goal: The Goal object with tasks to execute
            max_replans: Max replan attempts (default: REACT_MAX_REPLANS)
            
        Returns:
            Tuple of (final_status, summary_message)
        """
        max_replans = max_replans if max_replans is not None else self.REACT_MAX_REPLANS
        replan_count = 0
        failed_task = None
        failure_reason = None
        
        if self.verbose_react:
            print(f"\n{'='*60}")
            print(f"🎯 PLANNER-EXECUTOR: {goal.description[:50]}...")
            print(f"   Tasks: {len(goal.tasks)} | Max Replans: {max_replans}")
            print(f"{'='*60}")
        
        logger.info(f"🎯 Starting Planner-Executor for: {goal.description}")
        
        while replan_count <= max_replans:
            # Try to execute all tasks
            all_success = True
            
            for task in goal.tasks:
                if task.status == TaskStatus.COMPLETED:
                    continue
                
                if self.verbose_react:
                    print(f"\n📋 Task {goal.tasks.index(task)+1}/{len(goal.tasks)}: {task.description}")
                
                task.status = TaskStatus.IN_PROGRESS
                
                try:
                    # Use ReAct for task execution
                    task_query = f"{task.description}. Context: {goal.context}"
                    trace = self.react_execute(task_query, max_steps=4)  # Shorter for subtasks
                    
                    if trace.success:
                        task.result = trace.final_answer
                        task.status = TaskStatus.COMPLETED
                        goal.context[task.id] = trace.final_answer
                        
                        if self.verbose_react:
                            print(f"   ✅ Completed")
                    else:
                        raise Exception(trace.error or "ReAct execution failed")
                        
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.result = str(e)
                    failed_task = task
                    failure_reason = str(e)
                    all_success = False
                    
                    logger.error(f"❌ Task failed: {task.description} - {e}")
                    if self.verbose_react:
                        print(f"   ❌ Failed: {e}")
                    break
            
            if all_success:
                goal.status = TaskStatus.COMPLETED
                summary = self._generate_goal_summary(goal)
                
                if self.verbose_react:
                    print(f"\n{'='*60}")
                    print(f"✅ GOAL ACHIEVED: {goal.description[:40]}...")
                    print(f"{'='*60}")
                
                return TaskStatus.COMPLETED, summary
            
            # Attempt replan
            replan_count += 1
            if replan_count <= max_replans:
                if self.verbose_react:
                    print(f"\n🔄 REPLANNING (attempt {replan_count}/{max_replans})...")
                    print(f"   Failed at: {failed_task.description}")
                    print(f"   Reason: {failure_reason}")
                
                # Generate alternative plan
                new_plan = self._generate_replan(goal, failed_task, failure_reason)
                
                if new_plan and len(new_plan.tasks) > 0:
                    goal.tasks = new_plan.tasks
                    goal.context['replan_attempt'] = replan_count
                    
                    if self.verbose_react:
                        print(f"   📝 New plan: {len(new_plan.tasks)} tasks")
                else:
                    if self.verbose_react:
                        print(f"   ⚠️ Could not generate alternative plan")
                    break
        
        # Final failure - return rich error
        goal.status = TaskStatus.FAILED
        error_summary = self._generate_failure_report(goal, failed_task, failure_reason, replan_count)
        
        if self.verbose_react:
            print(f"\n{'='*60}")
            print(f"❌ GOAL FAILED after {replan_count} replan attempts")
            print(f"{'='*60}")
            print(error_summary)
        
        return TaskStatus.FAILED, error_summary
    
    def _generate_replan(self, goal: Goal, failed_task: Task, failure_reason: str) -> Optional[Goal]:
        """Generate an alternative plan after a failure."""
        logger.info(f"🔄 Generating replan for: {goal.description}")
        
        completed_tasks = [t for t in goal.tasks if t.status == TaskStatus.COMPLETED]
        completed_text = "\n".join([f"- {t.description}: {t.result[:100] if t.result else 'done'}" for t in completed_tasks])
        
        replan_prompt = f"""
        GOAL: {goal.description}
        
        COMPLETED SO FAR:
        {completed_text or "Nothing yet"}
        
        FAILED TASK: {failed_task.description}
        FAILURE REASON: {failure_reason}
        
        Generate an ALTERNATIVE plan to achieve the goal.
        Avoid the approach that failed. Try a different strategy.
        
        Format: - Description [Tool]
        """
        
        response = self.llm.generate(replan_prompt)
        
        if "<think>" in response:
            response = response.split("</think>")[-1]
        
        new_goal = Goal(goal.description)
        
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                tool_match = re.search(r'\[(.*?)\]', line)
                tool = tool_match.group(1) if tool_match else None
                desc = re.sub(r'\[.*?\]', '', line).strip("- *")
                if desc:
                    new_goal.tasks.append(Task(desc, tool))
        
        # Preserve completed tasks at the start
        for ct in reversed(completed_tasks):
            new_goal.tasks.insert(0, ct)
        
        return new_goal if new_goal.tasks else None
    
    def _generate_goal_summary(self, goal: Goal) -> str:
        """Generate a summary of completed goal."""
        results = []
        for task in goal.tasks:
            if task.result:
                results.append(f"- {task.description}: {str(task.result)[:100]}")
        
        summary_prompt = f"""
        Goal: {goal.description}
        Results:
        {chr(10).join(results)}
        
        Write a brief summary of what was accomplished. 2-3 sentences max.
        """
        
        return self.llm.generate(summary_prompt).strip()
    
    def _generate_failure_report(self, goal: Goal, failed_task: Task, failure_reason: str, attempts: int) -> str:
        """Generate a detailed failure report."""
        completed = [t for t in goal.tasks if t.status == TaskStatus.COMPLETED]
        pending = [t for t in goal.tasks if t.status == TaskStatus.PENDING]
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    GOAL EXECUTION FAILED                      ║
╚══════════════════════════════════════════════════════════════╝

📎 GOAL: {goal.description}

❌ FAILED AT: {failed_task.description if failed_task else 'Unknown'}
🔍 REASON: {failure_reason}
🔄 REPLAN ATTEMPTS: {attempts}/{self.REACT_MAX_REPLANS}

✅ COMPLETED TASKS ({len(completed)}):
{chr(10).join([f'   - {t.description}' for t in completed]) or '   (none)'}

⏳ PENDING TASKS ({len(pending)}):
{chr(10).join([f'   - {t.description}' for t in pending]) or '   (none)'}

💡 SUGGESTIONS:
   - Review the failed task requirements
   - Check if required tools/APIs are available
   - Consider breaking the goal into smaller parts
"""
        return report

    def execute_goal(self, goal: Goal):
        """
        Tier 6: End-to-End Autonomous Execution Loop.
        """
        logger.info(f"🚀 Executing goal: {goal.description}")
        
        for task in goal.tasks:
            if task.status == TaskStatus.COMPLETED:
                continue
                
            logger.info(f"▶ Task: {task.description}")
            task.status = TaskStatus.IN_PROGRESS
            
            # Execute
            try:
                result = self._execute_task(task, goal.context)
                task.result = result
                task.status = TaskStatus.COMPLETED
                
                # Update context with result
                goal.context[task.id] = result
                
                # Self-correction check (Tier 7: Reliability)
                if not self._validate_result(result):
                    logger.warning("⚠️ Task result suspicious, retrying...")
                    # Implementation of retry logic would go here
                    
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.result = str(e)
                logger.error(f"❌ Task failed: {e}")
                # Dynamic replanning could happen here
                break
                
        goal.status = TaskStatus.COMPLETED if all(t.status == TaskStatus.COMPLETED for t in goal.tasks) else TaskStatus.FAILED
        return goal.status

    def _execute_task(self, task: Task, context: Dict) -> Any:
        """Execute a single task utilizing tools."""
        if task.tool and task.tool in self.tool_registry.tools:
            # Construct args based on description + context
            # This is where argument generation logic goes
            # For now, simple pass-through or mock
            return f"Executed {task.tool} for {task.description}"
        
        # If no specific tool, it might be a thinking/synthesis task
        return self.llm.generate(f"Perform text task: {task.description} given context: {context}")

    def _validate_result(self, result: Any) -> bool:
        """Tier 7: Hallucination Minimization check."""
        # Simple check
        if "error" in str(result).lower():
            return False
        return True

    def handle_direct_command(self, text: str) -> str:
        """
        Handle simple queries or chat (Tier 1).
        """
        text_lower = text.lower()
        
        # 1. Check for quick benchmark tools (Time, Calc, Weather)
        # This mirrors the 'alfred_hybrid' logic for speed
        try:
            from benchmark_tools import get_current_time, solve_math, get_weather
            
            if "time" in text_lower:
                return str(get_current_time()['time'])
            
            if "weather" in text_lower:
                import re
                city_match = re.search(r'(?:weather|in|for)\s+(\w+)', text_lower)
                city = city_match.group(1) if city_match else "Mumbai"
                return str(get_weather(city))
                
            if any(c in text for c in "+-*/") and any(d.isdigit() for d in text):
                # Extract expression (simple regex)
                import re
                expr_match = re.search(r'[\d\+\-\*\/\.\(\)\s]+', text)
                if expr_match:
                    res = solve_math(expr_match.group(0).strip())
                    if "result" in res:
                        return str(res['result'])
                    if "error" in res:
                        return f"Error: {res['error']}"
                
        except ImportError:
            pass
            
        # 2. Retrieval Retrieval (RAG)
        context = self.memory.retrieve_context(text)
        
        # 3. LLM Chat
        prompt = f"""
        CONTEXT: {context}
        USER: {text}
        
        Respond as ALFRED (helpful, concise assistant).
        """
        response = self.llm.generate(prompt)
        
        # Store response in memory
        self.memory.add_interaction("assistant", response)
        
        if "<think>" in response:
            response = response.split("</think>")[-1].strip()
            
        return response

    def _extract_json(self, text: str) -> str:
        """Helper to extract JSON from LLM response."""
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return match.group(0) if match else "{}"

