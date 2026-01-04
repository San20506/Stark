#!/usr/bin/env python3
"""Quick test of STARK integration"""
import sys
sys.path.insert(0, '/home/sandy/Projects/Projects/Stark')

from core.main import get_stark

print("Testing STARK Integration...")
print("="*50)

stark = get_stark()

# Test query
query = "list running applications"
print(f"\nQuery: {query}")
print("-"*50)

result = stark.predict(query)

print(f"Task: {result.task}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Latency: {result.latency_ms:.0f}ms")
print(f"\nResponse:\n{result.response[:500]}")
print("="*50)
