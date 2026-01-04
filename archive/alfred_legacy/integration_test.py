#!/usr/bin/env python3
"""
ALFRED v4.0 Integration Test
Tests that all components work together end-to-end.
"""

import sys
import os

# Add ALFRED root to path
alfred_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, alfred_root)

print("=" * 60)
print("🧪 ALFRED v4.0 Integration Test")
print("=" * 60)

# Test 1: Imports
print("\n[TEST 1] Testing imports...")
try:
    from core.tools import tool_registry
    from agents.llm import LLMClient
    from agents.brain import CognitiveEngine, ReActStep, ReActTrace
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Initialize components
print("\n[TEST 2] Initializing components...")
try:
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
    print(f"✅ CognitiveEngine initialized")
    print(f"   - ReAct max steps: {brain.REACT_DEFAULT_STEPS}")
    print(f"   - Max replans: {brain.REACT_MAX_REPLANS}")
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    sys.exit(1)

# Test 3: Check methods exist
print("\n[TEST 3] Checking ReAct methods...")
methods = [
    'react_execute',
    '_parse_react_response',
    '_execute_react_action',
    '_get_llm_confidence',
    '_calculate_step_confidence',
    '_calculate_overall_confidence',
    '_verify_answer',
    '_improve_answer',
    'execute_goal_with_replan'
]

missing = []
for method in methods:
    if not hasattr(brain, method):
        missing.append(method)

if missing:
    print(f"❌ Missing methods: {missing}")
    sys.exit(1)
else:
    print(f"✅ All {len(methods)} methods present")

# Test 4: Data structures
print("\n[TEST 4] Testing data structures...")
try:
    step = ReActStep(1, "test thought", confidence=0.85)
    assert step.confidence == 0.85
    
    trace = ReActTrace("test query", overall_confidence=0.75)
    assert trace.overall_confidence == 0.75
    
    # Test string representation
    step_str = str(step)
    assert "⭐" in step_str
    assert "0.85" in step_str
    
    print("✅ Data structures working correctly")
except Exception as e:
    print(f"❌ Data structure test failed: {e}")
    sys.exit(1)

# Test 5: Tool registry
print("\n[TEST 5] Checking tool registry...")
try:
    tools = tool_registry.tools
    print(f"✅ Tool registry loaded with {len(tools)} tools")
    if len(tools) > 0:
        print(f"   Sample tools: {list(tools.keys())[:5]}")
except Exception as e:
    print(f"❌ Tool registry check failed: {e}")
    sys.exit(1)

# Test 6: Simple confidence calculation
print("\n[TEST 6] Testing confidence calculation...")
try:
    test_step = ReActStep(1, "I need to calculate 2+2", action="calc")
    conf = brain._calculate_step_confidence(test_step, tool_success=True, observation="4")
    
    assert 0.0 <= conf <= 1.0, f"Confidence out of range: {conf}"
    print(f"✅ Confidence calculation works: {conf:.2f}")
except Exception as e:
    print(f"❌ Confidence calculation failed: {e}")
    sys.exit(1)

# Test 7: Verification methods
print("\n[TEST 7] Testing verification methods...")
try:
    test_trace = ReActTrace("test")
    test_trace.steps.append(ReActStep(1, "thinking"))
    
    result = brain._verify_answer("What is 2+2?", "4", test_trace)
    assert 'needs_revision' in result
    assert 'issues' in result
    
    print(f"✅ Verification methods working")
except Exception as e:
    print(f"❌ Verification test failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 60)
print("✅ ALL INTEGRATION TESTS PASSED!")
print("=" * 60)
print("\n🚀 ALFRED v4.0 is ready to run!")
print("\nTo start ALFRED:")
print("  python launchers/alfred.py")
print("\nFor quiet mode (logs only):")
print("  python launchers/alfred.py --quiet")
print("\n" + "=" * 60)

sys.exit(0)
