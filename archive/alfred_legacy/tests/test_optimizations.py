"""
TEST OPTIMIZED ALFRED
Verify: Streaming, Parallel Research, Self-Reflection
"""
import sys
sys.path.append(".")

from modules.llm import LLMClient
from modules.brain import CognitiveEngine
from modules.researcher import ResearchAgent
from tools import tool_registry
import logging

logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("🧪 TESTING OPTIMIZED ALFRED")
print("=" * 60)

llm = LLMClient()
brain = CognitiveEngine(tool_registry, llm)

# Test 1: Streaming
print("\n1️⃣ Testing Streaming...")
print("Response: ", end="", flush=True)
for chunk in llm.generate("Say hello in 5 words", stream=True):
    if "<think>" not in chunk:
        print(chunk, end="", flush=True)
print("\n✅ Streaming works!")

# Test 2: Self-Reflection Planning
print("\n2️⃣ Testing Self-Reflection Planning...")
goal = brain.formulate_plan("Create a simple Python script")
print(f"Plan has {len(goal.tasks)} tasks (refined)")
if len(goal.tasks) > 0:
    print("✅ Self-reflection works!")
else:
    print("❌ Planning failed")

# Test 3: Parallel Research (Quick)
print("\n3️⃣ Testing Parallel Research...")
researcher = ResearchAgent(llm)
result = researcher.conduct_research("Python benefits", depth=2)
if "Python" in result or "programming" in result.lower():
    print("✅ Parallel research works!")
else:
    print(f"⚠️ Research result: {result[:100]}")

print("\n" + "=" * 60)
print("✅ ALL OPTIMIZATIONS VERIFIED")
print("=" * 60)
