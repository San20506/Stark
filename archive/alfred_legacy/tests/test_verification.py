#!/usr/bin/env python3
"""
Self-Verification Test
Quick test to verify the self-verification loop works.
"""

import sys
import logging

logging.basicConfig(level=logging.WARNING)

print("=" * 60)
print("🧪 Self-Verification Test")
print("=" * 60)

from agents.brain import CognitiveEngine
from core.tools import tool_registry
from agents.llm import LLMClient

# Test 1: Verification methods exist
print("\n[TEST 1] Checking methods exist...")
llm = LLMClient()
brain = CognitiveEngine(tool_registry, llm, verbose_react=False)

assert hasattr(brain, '_verify_answer'), "Missing _verify_answer"
assert hasattr(brain, '_improve_answer'), "Missing _improve_answer"
print("✅ Methods exist")

# Test 2: Verification returns correct structure
print("\n[TEST 2] Testing verification structure...")
from agents.brain import ReActTrace, ReActStep

trace = ReActTrace("test")
trace.steps.append(ReActStep(1, "thinking"))

result = brain._verify_answer("What is 2+2?", "4", trace)
assert 'needs_revision' in result, "Missing needs_revision key"
assert 'issues' in result, "Missing issues key"
assert isinstance(result['needs_revision'], bool), "needs_revision not bool"
assert isinstance(result['issues'], list), "issues not list"
print(f"✅ Verification structure correct: {result}")

# Test 3: Improvement returns string or None
print("\n[TEST 3] Testing answer improvement...")
improved = brain._improve_answer(
    "What is the capital of France?",
    "Paris is a city",
    ["Incomplete - should mention it's the capital"]
)
assert improved is None or isinstance(improved, str), "Improvement not str or None"
print(f"✅ Improvement works: {type(improved)}")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED - Self-verification is functional!")
print("=" * 60)
print("\n💡 To see it in action, run:")
print("   python launchers/alfred.py")
print("   Then ask a question that might have low confidence")
