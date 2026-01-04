#!/usr/bin/env python3
"""
Final Verification Test - All Components
"""

print("=" * 60)
print("🤖 ALFRED - Final Verification")
print("=" * 60)

tests_passed = 0
tests_total = 0

def test(name, check_func):
    """Run a test."""
    global tests_passed, tests_total
    tests_total += 1
    try:
        result = check_func()
        if result:
            print(f"✅ {name}")
            tests_passed += 1
            return True
        else:
            print(f"❌ {name}")
            return False
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

# Core Components
print("\n[CORE COMPONENTS]")
test("Tools Registry", lambda: __import__('tools').tool_registry is not None)
test("Reasoning Engine", lambda: __import__('reasoning').ToolSuggester is not None)
test("Skill Generator", lambda: __import__('skill_generator').skill_generator is not None)
test("Ollama Connection", lambda: __import__('ollama').list() is not None)

# Wake Word
print("\n[WAKE WORD DETECTION]")
def test_wake_word():
    from main import WakeWordDetector
    detector = WakeWordDetector()
    return detector.available

test("Wake Word (ONNX)", test_wake_word)

# Tools
print("\n[NATIVE TOOLS]")
from tools import tool_registry

test("Datetime Tool", lambda: 'datetime' in tool_registry.tools)
test("Calc Tool", lambda: 'calc' in tool_registry.tools)
test("Memory Tool", lambda: 'memory' in tool_registry.tools)
test("File Tool", lambda: 'file' in tool_registry.tools)

# Generated Skills
print("\n[GENERATED SKILLS]")
from skill_loader import skill_loader

skills = skill_loader.load_all_skills()
test("Skills Loaded", lambda: len(skills) > 0)
test("Weather Skill", lambda: 'get_weather' in skills)
test("Converter Skill", lambda: 'unit_converter' in skills)

# Tool Execution
print("\n[TOOL EXECUTION]")
test("Execute Datetime", lambda: ":" in tool_registry.execute('<tool:datetime args="time"/>'))
test("Execute Calc", lambda: tool_registry.execute('<tool:calc args="10+5"/>') == "15")

# Skill Execution
print("\n[SKILL EXECUTION]")
weather_mod = skill_loader.loaded_skills.get('get_weather')
if weather_mod:
    test("Weather Skill Runs", lambda: weather_mod.run(city="London") is not None)

converter_mod = skill_loader.loaded_skills.get('unit_converter')
if converter_mod:
    test("Converter Runs", lambda: "62.14" in converter_mod.run(value=100, from_unit="km", to_unit="miles"))

# Summary
print("\n" + "=" * 60)
print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
print("=" * 60)

if tests_passed == tests_total:
    print("\n🎉 ALL SYSTEMS OPERATIONAL!")
    print("\n✅ ALFRED is ready for use!")
    print("\nRun: python alfred_hybrid.py")
elif tests_passed >= tests_total * 0.8:
    print("\n✅ ALFRED is operational (some optional features disabled)")
else:
    print("\n⚠️ Some systems need attention")

print("=" * 60)
