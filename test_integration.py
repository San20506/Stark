#!/usr/bin/env python3
"""
Test Autonomous Integration
============================
Quick test to verify all Phase 4 components are connected.
"""

import sys
sys.path.insert(0, '/home/sandy/Projects/Projects/Stark')

from core.main import get_stark

print("=" * 70)
print("Testing STARK Autonomous Integration")
print("=" * 70)
print()

stark = get_stark()

# Test 1: Simple query (should use simple path)
print("Test 1: Simple conversation")
print("Query: 'Hello STARK'")
result1 = stark.predict("Hello STARK")
print(f"Response: {result1.response}")
print(f"Task: {result1.task}, Confidence: {result1.confidence:.2f}")
print()

# Test 2: System control (should use autonomous orchestrator)
print("Test 2: System control (autonomous path)")
print("Query: 'list running applications'")
result2 = stark.predict("list running applications")
print(f"Response: {result2.response[:200]}...")
print(f"Task: {result2.task}, Latency: {result2.latency_ms:.0f}ms")
print()

# Test 3: Code generation (should use autonomous + CodeAgent)
print("Test 3: Code generation")
print("Query: 'write a function to reverse a string'")
result3 = stark.predict("write a function to reverse a string")
print(f"Response: {result3.response[:300]}...")
print(f"Task: {result3.task}")
print()

print("=" * 70)
print("✓ Integration test complete!")
print("=" * 70)
