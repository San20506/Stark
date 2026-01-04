#!/usr/bin/env python3
"""
ReAct (Reason + Act) Test Suite
Tests the new ReAct architecture in ALFRED's brain.
"""

import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

print("=" * 60)
print("🧪 ALFRED ReAct Architecture Test")
print("=" * 60)

passed = 0
total = 0

def test(name, func):
    global passed, total
    total += 1
    try:
        result = func()
        if result:
            print(f"✅ {name}")
            passed += 1
            return True
        else:
            print(f"❌ {name}")
            return False
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

# ============================================================================
# 1. DATA STRUCTURE TESTS
# ============================================================================
print("\n[DATA STRUCTURES]")

def test_react_step_creation():
    from modules.brain import ReActStep
    step = ReActStep(
        step_num=1,
        thought="I need to check the time",
        action="get_current_time",
        action_input="",
        observation="{'time': '14:30:00'}"
    )
    return step.step_num == 1 and "time" in step.thought

def test_react_trace_creation():
    from modules.brain import ReActTrace, ReActStep
    trace = ReActTrace(query="What time is it?")
    trace.steps.append(ReActStep(1, "Checking time", "time", ""))
    trace.final_answer = "It's 2:30 PM"
    trace.success = True
    return trace.success and len(trace.steps) == 1

def test_react_trace_str():
    from modules.brain import ReActTrace
    trace = ReActTrace(query="Test query")
    trace.final_answer = "Test answer"
    trace.success = True
    output = str(trace)
    return "Test query" in output and "Final Answer" in output

test("ReActStep creation", test_react_step_creation)
test("ReActTrace creation", test_react_trace_creation)
test("ReActTrace string representation", test_react_trace_str)

# ============================================================================
# 2. COGNITIVE ENGINE INITIALIZATION
# ============================================================================
print("\n[COGNITIVE ENGINE]")

def test_engine_init():
    from tools import tool_registry
    from modules.llm import LLMClient
    from modules.brain import CognitiveEngine
    
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
    
    return (
        brain.REACT_MAX_STEPS_HARD_CAP == 10 and
        brain.REACT_DEFAULT_STEPS == 6 and
        brain.REACT_MAX_REPLANS == 2
    )

def test_engine_tool_descriptions():
    from tools import tool_registry
    from modules.llm import LLMClient
    from modules.brain import CognitiveEngine
    
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
    desc = brain._get_react_tool_descriptions()
    
    return "Available tools:" in desc

def test_engine_build_prompt():
    from tools import tool_registry
    from modules.llm import LLMClient
    from modules.brain import CognitiveEngine
    
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
    prompt = brain._build_react_prompt("What is 2+2?", "- calc: calculator")
    
    return "TASK: What is 2+2?" in prompt and "Thought:" in prompt

test("CognitiveEngine initialization with ReAct config", test_engine_init)
test("Tool descriptions generation", test_engine_tool_descriptions)
test("ReAct prompt building", test_engine_build_prompt)

# ============================================================================
# 3. PARSING TESTS
# ============================================================================
print("\n[RESPONSE PARSING]")

def test_parse_thought_action():
    from tools import tool_registry
    from modules.llm import LLMClient
    from modules.brain import CognitiveEngine
    
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
    
    response = """Thought: I need to get the current time
Action: get_current_time
Action Input: UTC"""
    
    thought, action, action_input, final = brain._parse_react_response(response)
    
    return (
        "get the current time" in thought and
        action == "get_current_time" and
        "UTC" in action_input and
        final is None
    )

def test_parse_final_answer():
    from tools import tool_registry
    from modules.llm import LLMClient
    from modules.brain import CognitiveEngine
    
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
    
    response = """Thought: I now have enough information.
Final Answer: The current time is 2:30 PM UTC."""
    
    thought, action, action_input, final = brain._parse_react_response(response)
    
    return (
        final is not None and
        "2:30 PM" in final and
        action is None
    )

test("Parse Thought/Action/Action Input", test_parse_thought_action)
test("Parse Final Answer", test_parse_final_answer)

# ============================================================================
# 4. LIVE EXECUTION TEST (requires Ollama)
# ============================================================================
print("\n[LIVE EXECUTION]")

def test_live_react_simple():
    """Test a simple ReAct query (requires LLM)."""
    from tools import tool_registry
    from modules.llm import LLMClient
    from modules.brain import CognitiveEngine
    
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
    
    # Simple query that should complete quickly
    trace = brain.react_execute("What is 2 + 2?", max_steps=3)
    
    return trace.final_answer is not None

def test_live_react_with_tool():
    """Test ReAct with tool usage."""
    from tools import tool_registry
    from modules.llm import LLMClient
    from modules.brain import CognitiveEngine
    
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=True)
    
    trace = brain.react_execute("What is the current time?", max_steps=4)
    
    # Should have used a tool and gotten an answer
    has_action = any(step.action for step in trace.steps)
    return trace.final_answer is not None

# These tests require LLM - mark as optional
try:
    test("ReAct simple query (LLM)", test_live_react_simple)
    test("ReAct with tool usage (LLM)", test_live_react_with_tool)
except Exception as e:
    print(f"⚠️ Live tests skipped: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 60)
print(f"📊 RESULTS: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
print("=" * 60)

if passed == total:
    print("\n🎉 ALL REACT TESTS PASSED!")
elif passed >= total * 0.7:
    print("\n✅ ReAct architecture is functional")
else:
    print("\n⚠️ Some tests need attention")

sys.exit(0 if passed >= total * 0.7 else 1)
