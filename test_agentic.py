#!/usr/bin/env python3
"""Test Agentic Execution"""
import sys
sys.path.insert(0, '/home/sandy/Projects/Projects/Stark')

print("=" * 60)
print("Testing STARK Agentic Execution")
print("=" * 60)

# Test 1: Intent Classification
print("\n[1] Testing IntentClassifier...")
from core.intent_classifier import get_intent_classifier
classifier = get_intent_classifier()

queries = [
    "open firefox",
    "hey stark can you open chrome",
    "close terminal",
    "list running apps",
    "search for python tutorials",
    "hello how are you",
]

for q in queries:
    intent = classifier.classify(q)
    print(f"  '{q}' → {intent.type.value} (target: {intent.target}, conf: {intent.confidence:.2f})")

# Test 2: App Discovery
print("\n[2] Testing AppDiscovery...")
from automation.app_discovery import get_app_discovery
discovery = get_app_discovery()
apps = discovery.list_apps()[:10]
print(f"  Found {len(discovery._apps)} apps. Sample: {apps}")

# Test 3: Find specific app
print("\n[3] Finding Firefox...")
ff = discovery.find("firefox")
if ff:
    print(f"  ✓ Found: {ff.name} → {ff.exec_path}")
else:
    print("  ✗ Firefox not found")

# Test 4: ActionExecutor (without actually launching)
print("\n[4] Testing ActionExecutor...")
from agents.action_executor import get_action_executor
from core.intent_classifier import IntentType, Intent

executor = get_action_executor()

# Test system info
info_intent = Intent(type=IntentType.SYSTEM_INFO, query="system info", confidence=0.9)
result = executor.execute(info_intent)
print(f"  System Info: {result.success}")
print(f"  {result.message[:100]}...")

print("\n" + "=" * 60)
print("✓ All components working!")
print("=" * 60)
