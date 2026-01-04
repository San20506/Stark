#!/usr/bin/env python3
"""
ALFRED v4.0 Demo
Demonstrates the new ReAct + Confidence + Verification features.
"""

import sys
import os

# Add ALFRED root to path
alfred_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, alfred_root)

from core.tools import tool_registry
from agents.llm import LLMClient
from agents.brain import CognitiveEngine

print("=" * 70)
print("🤖 ALFRED v4.0 - Enhanced Reasoning Demo")
print("=" * 70)

# Initialize
llm = LLMClient()
brain = CognitiveEngine(tool_registry, llm, verbose_react=True)

print("\n✅ System initialized with:")
print(f"   • ReAct reasoning (max {brain.REACT_DEFAULT_STEPS} steps)")
print(f"   • Confidence scoring")
print(f"   • Self-verification (triggers at <0.6 confidence)")
print(f"   • Dynamic replanning (up to {brain.REACT_MAX_REPLANS} attempts)")

# Demo 1: Simple high-confidence query
print("\n" + "=" * 70)
print("📝 DEMO 1: High-Confidence Query")
print("=" * 70)
print("\nQuery: What is 2 + 2?")
print("\nExpected: High confidence, quick answer\n")

try:
    trace = brain.react_execute("What is 2 + 2?", max_steps=3)
    print(f"\n📊 Result:")
    print(f"   Answer: {trace.final_answer}")
    print(f"   Confidence: {trace.overall_confidence:.2f}")
    print(f"   Steps taken: {len(trace.steps)}")
except Exception as e:
    print(f"❌ Error: {e}")

# Demo 2: Tool-based query
print("\n" + "=" * 70)
print("📝 DEMO 2: Tool-Based Query")
print("=" * 70)
print("\nQuery: What time is it?")
print("\nExpected: Uses get_current_time tool\n")

try:
    trace = brain.react_execute("What time is it?", max_steps=4)
    print(f"\n📊 Result:")
    print(f"   Answer: {trace.final_answer}")
    print(f"   Confidence: {trace.overall_confidence:.2f}")
    print(f"   Steps taken: {len(trace.steps)}")
    
    # Check if tool was used
    used_tools = [s.action for s in trace.steps if s.action]
    if used_tools:
        print(f"   Tools used: {used_tools}")
except Exception as e:
    print(f"❌ Error: {e}")

# Demo 3: Uncertain query (should trigger verification)
print("\n" + "=" * 70)
print("📝 DEMO 3: Uncertain Query (Self-Verification)")
print("=" * 70)
print("\nQuery: What will happen in the year 2100?")
print("\nExpected: Low confidence, triggers self-verification\n")

try:
    trace = brain.react_execute("What will happen in the year 2100?", max_steps=4)
    print(f"\n📊 Result:")
    print(f"   Answer: {trace.final_answer[:150]}...")
    print(f"   Confidence: {trace.overall_confidence:.2f}")
    print(f"   Steps taken: {len(trace.steps)}")
    
    if trace.overall_confidence < 0.6:
        print(f"   ⚠️ Low confidence - verification was triggered")
except Exception as e:
    print(f"❌ Error: {e}")

# Summary
print("\n" + "=" * 70)
print("✅ Demo Complete!")
print("=" * 70)
print("\n🎯 Key Features Demonstrated:")
print("   1. ✅ ReAct reasoning with visible Thought/Action/Observation")
print("   2. ✅ Confidence scoring (0-1 scale with star indicators)")
print("   3. ✅ Self-verification for low-confidence answers")
print("   4. ✅ Tool integration (time, calculations, etc.)")
print("\n💡 To interact with ALFRED:")
print("   python launchers/alfred.py")
print("\n" + "=" * 70)
