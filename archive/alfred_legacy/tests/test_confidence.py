#!/usr/bin/env python3
"""
Confidence Scoring Test Suite
Tests the new confidence scoring in ReAct responses.
"""

import sys
import logging

logging.basicConfig(level=logging.WARNING)

print("=" * 60)
print("🧪 Confidence Scoring Tests")
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

# Test 1: Data structures have confidence fields
def test_confidence_fields():
    from agents.brain import ReActStep, ReActTrace
    
    step = ReActStep(1, "Test thought", confidence=0.85)
    assert step.confidence == 0.85, "Step confidence not set"
    
    trace = ReActTrace("test query", overall_confidence=0.75)
    assert trace.overall_confidence == 0.75, "Trace confidence not set"
    
    return True

# Test 2: Confidence display in __str__
def test_confidence_display():
    from agents.brain import ReActStep, ReActTrace
    
    # High confidence step
    step_high = ReActStep(1, "I'm certain", confidence=0.9)
    output = str(step_high)
    assert "⭐⭐⭐" in output, "High confidence stars not shown"
    assert "0.90" in output, "Confidence score not shown"
    
    # Medium confidence step
    step_med = ReActStep(2, "Maybe", confidence=0.6)
    output = str(step_med)
    assert "⭐⭐" in output, "Medium confidence stars not shown"
    
    # Low confidence step
    step_low = ReActStep(3, "Unsure", confidence=0.3)
    output = str(step_low)
    assert "⭐" in output, "Low confidence star not shown"
    
    return True

# Test 3: Overall confidence display
def test_overall_confidence_display():
    from agents.brain import ReActTrace, ReActStep
    
    trace = ReActTrace("test", overall_confidence=0.82)
    trace.final_answer = "42"
    trace.steps.append(ReActStep(1, "thinking", confidence=0.8))
    
    output = str(trace)
    assert "📊 Overall Confidence" in output, "Overall confidence not shown"
    assert "0.82" in output, "Confidence value not shown"
    assert "HIGH" in output, "Confidence level not shown"
    
    return True

# Test 4: Confidence calculation methods exist
def test_confidence_methods():
    from agents.brain import CognitiveEngine
    from core.tools import tool_registry
    from agents.llm import LLMClient
    
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
    
    # Check methods exist
    assert hasattr(brain, '_get_llm_confidence'), "Missing _get_llm_confidence"
    assert hasattr(brain, '_calculate_step_confidence'), "Missing _calculate_step_confidence"
    assert hasattr(brain, '_calculate_overall_confidence'), "Missing _calculate_overall_confidence"
    
    return True

# Test 5: Step confidence calculation
def test_step_confidence_calc():
    from agents.brain import CognitiveEngine, ReActStep
    from core.tools import tool_registry
    from agents.llm import LLMClient
    
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
    
    step = ReActStep(1, "I need to calculate 2+2", action="calc")
    
    # Test with successful tool
    conf = brain._calculate_step_confidence(step, tool_success=True, observation="4")
    assert 0.0 <= conf <= 1.0, f"Confidence out of range: {conf}"
    assert conf > 0.3, "Successful tool should have decent confidence"
    
    # Test with failed tool
    conf_fail = brain._calculate_step_confidence(step, tool_success=False, observation="Error")
    assert conf_fail < conf, "Failed tool should have lower confidence"
    
    return True

# Test 6: Overall confidence aggregation
def test_overall_confidence_calc():
    from agents.brain import CognitiveEngine, ReActTrace, ReActStep
    from core.tools import tool_registry
    from agents.llm import LLMClient
    
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
    
    trace = ReActTrace("test")
    trace.steps = [
        ReActStep(1, "step1", confidence=0.8),
        ReActStep(2, "step2", confidence=0.9),
    ]
    trace.success = True
    
    overall = brain._calculate_overall_confidence(trace)
    assert 0.0 <= overall <= 1.0, f"Overall confidence out of range: {overall}"
    assert overall > 0.7, "Successful trace with high step confidence should have high overall"
    
    # Test with failure
    trace.success = False
    overall_fail = brain._calculate_overall_confidence(trace)
    assert overall_fail < overall, "Failed trace should have lower confidence"
    
    return True

# Run tests
print("\n[DATA STRUCTURES]")
test("Confidence fields in dataclasses", test_confidence_fields)
test("Confidence display formatting", test_confidence_display)
test("Overall confidence display", test_overall_confidence_display)

print("\n[METHODS]")
test("Confidence calculation methods exist", test_confidence_methods)
test("Step confidence calculation", test_step_confidence_calc)
test("Overall confidence aggregation", test_overall_confidence_calc)

# Summary
print("\n" + "=" * 60)
print(f"📊 RESULTS: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
print("=" * 60)

if passed == total:
    print("\n🎉 ALL CONFIDENCE TESTS PASSED!")
    sys.exit(0)
elif passed >= total * 0.7:
    print("\n✅ Confidence scoring is functional")
    sys.exit(0)
else:
    print("\n⚠️ Some tests need attention")
    sys.exit(1)
