"""
ALFRED Feature Verification Test
Tests EVERY claimed feature and reports what actually works.

Run: python tests/verify_all_features.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix encoding for Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("[TEST] ALFRED Feature Verification Test")
print("=" * 70)
print("\nThis will test EVERY claimed feature.\n")

results = {
    "passed": [],
    "failed": [],
    "skipped": []
}


def test(name, test_func, skip_reason=None):
    """Run a test and record result."""
    if skip_reason:
        print(f"⏭️  {name}: SKIPPED - {skip_reason}")
        results["skipped"].append((name, skip_reason))
        return
    
    try:
        result = test_func()
        if result:
            print(f"✅ {name}: PASSED")
            results["passed"].append(name)
        else:
            print(f"❌ {name}: FAILED")
            results["failed"].append(name)
    except Exception as e:
        print(f"❌ {name}: ERROR - {e}")
        results["failed"].append(f"{name}: {e}")


# ============================================================================
# CATEGORY 1: NLU (Intent Detection)
# ============================================================================
print("\n" + "=" * 70)
print("📋 CATEGORY 1: NLU (Natural Language Understanding)")
print("=" * 70)

def test_nlu_model_loads():
    from core.nlu import IntentDetector
    detector = IntentDetector()
    detector.load_model("models/nlu_jarvis.h5", "data/jarvis/vocab.pkl")
    return detector.model_loaded

def test_nlu_time_intent():
    from core.nlu import IntentDetector
    detector = IntentDetector()
    detector.load_model("models/nlu_jarvis.h5", "data/jarvis/vocab.pkl")
    result = detector.detect("what time is it?")
    return result.intent == "time" and result.confidence >= 0.7

def test_nlu_weather_intent():
    from core.nlu import IntentDetector
    detector = IntentDetector()
    detector.load_model("models/nlu_jarvis.h5", "data/jarvis/vocab.pkl")
    result = detector.detect("what's the weather in Tokyo?")
    return "weather" in result.intent.lower() and result.confidence >= 0.7

def test_nlu_calculator_intent():
    from core.nlu import IntentDetector
    detector = IntentDetector()
    detector.load_model("models/nlu_jarvis.h5", "data/jarvis/vocab.pkl")
    result = detector.detect("calculate 5 times 7")
    return result.intent == "calculator" and result.confidence >= 0.7

test("NLU Model Loads", test_nlu_model_loads)
test("NLU Time Intent", test_nlu_time_intent)
test("NLU Weather Intent", test_nlu_weather_intent)
test("NLU Calculator Intent", test_nlu_calculator_intent)


# ============================================================================
# CATEGORY 2: MCP (Module Routing)
# ============================================================================
print("\n" + "=" * 70)
print("📋 CATEGORY 2: MCP (Master Control Program)")
print("=" * 70)

def test_mcp_initializes():
    from agents.llm import LLMClient
    from agents.mcp import MasterControlProgram
    llm = LLMClient()
    mcp = MasterControlProgram(llm)
    return mcp is not None

def test_mcp_time_query():
    from agents.llm import LLMClient
    from agents.mcp import MasterControlProgram
    llm = LLMClient()
    mcp = MasterControlProgram(llm)
    result = mcp.process("what time is it?")
    return result is not None and result.answer is not None

test("MCP Initializes", test_mcp_initializes)
test("MCP Time Query", test_mcp_time_query)


# ============================================================================
# CATEGORY 3: Basic Tools
# ============================================================================
print("\n" + "=" * 70)
print("📋 CATEGORY 3: Basic Tools")
print("=" * 70)

def test_tool_time():
    from core.benchmark_tools import get_current_time
    result = get_current_time()
    return "time" in result and result["time"] is not None

def test_tool_date():
    from core.benchmark_tools import get_current_date
    result = get_current_date()
    return "date" in result and result["date"] is not None

def test_tool_math():
    from core.benchmark_tools import solve_math
    result = solve_math("5 * 7")
    return result.get("result") == 35

def test_tool_convert():
    from core.benchmark_tools import convert_units
    result = convert_units(100, "km", "miles")
    return result.get("converted_value") is not None

def test_tool_sentiment():
    from core.benchmark_tools import classify_sentiment
    result = classify_sentiment("This is amazing!")
    return result.get("label") == "positive"

def test_tool_entities():
    from core.benchmark_tools import extract_entities
    result = extract_entities("John works at Google in New York")
    return len(result.get("entities", [])) > 0

test("Tool: Time", test_tool_time)
test("Tool: Date", test_tool_date)
test("Tool: Math", test_tool_math)
test("Tool: Unit Conversion", test_tool_convert)
test("Tool: Sentiment", test_tool_sentiment)
test("Tool: Entity Extraction", test_tool_entities)


# ============================================================================
# CATEGORY 4: Desktop Control
# ============================================================================
print("\n" + "=" * 70)
print("📋 CATEGORY 4: Desktop Control")
print("=" * 70)

def test_desktop_init():
    from agents.desktop_control import get_desktop_controller
    controller = get_desktop_controller()
    return controller.screen_width > 0 and controller.screen_height > 0

def test_desktop_mouse_position():
    from agents.desktop_control import get_desktop_controller
    controller = get_desktop_controller()
    x, y = controller.get_mouse_position()
    return x >= 0 and y >= 0

def test_desktop_get_windows():
    from agents.desktop_control import get_desktop_controller
    controller = get_desktop_controller()
    windows = controller.get_all_windows()
    return len(windows) > 0

def test_desktop_active_window():
    from agents.desktop_control import get_desktop_controller
    controller = get_desktop_controller()
    window = controller.get_active_window()
    return window is not None and window.title is not None

test("Desktop Control Init", test_desktop_init)
test("Desktop Mouse Position", test_desktop_mouse_position)
test("Desktop Get Windows", test_desktop_get_windows)
test("Desktop Active Window", test_desktop_active_window)


# ============================================================================
# CATEGORY 5: Vision (if available)
# ============================================================================
print("\n" + "=" * 70)
print("📋 CATEGORY 5: Vision")
print("=" * 70)

def test_vision_screenshot():
    from agents.vision import VisionModule
    vision = VisionModule()
    # Just test if it can take a screenshot
    import pyautogui
    img = pyautogui.screenshot()
    return img is not None

def test_vision_ocr():
    # This requires tesseract installed
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except:
        return False

test("Vision Screenshot", test_vision_screenshot)
test("Vision OCR Available", test_vision_ocr)


# ============================================================================
# CATEGORY 6: Memory (if available)
# ============================================================================
print("\n" + "=" * 70)
print("📋 CATEGORY 6: Memory")
print("=" * 70)

def test_memory_chromadb():
    try:
        import chromadb
        return True
    except ImportError:
        return False

def test_memory_conversation_db():
    try:
        from memory.conversation_db import ConversationDB
        db = ConversationDB()
        return db is not None
    except:
        return False

test("ChromaDB Available", test_memory_chromadb)
test("Conversation DB", test_memory_conversation_db)


# ============================================================================
# CATEGORY 7: Web Search
# ============================================================================
print("\n" + "=" * 70)
print("📋 CATEGORY 7: Web Search")
print("=" * 70)

def test_web_search():
    from core.benchmark_tools import web_search
    result = web_search("Python programming", 3)
    return result.get("count", 0) > 0

test("Web Search (DuckDuckGo)", test_web_search)


# ============================================================================
# CATEGORY 8: Scheduler
# ============================================================================
print("\n" + "=" * 70)
print("📋 CATEGORY 8: Scheduler")
print("=" * 70)

def test_scheduler_init():
    try:
        from agents.scheduler import ALFREDScheduler
        scheduler = ALFREDScheduler()
        return scheduler is not None
    except:
        return False

def test_apscheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        return True
    except ImportError:
        return False

test("APScheduler Available", test_apscheduler)
test("Scheduler Initializes", test_scheduler_init)


# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("📊 SUMMARY")
print("=" * 70)

total = len(results["passed"]) + len(results["failed"]) + len(results["skipped"])
print(f"\n✅ Passed: {len(results['passed'])}/{total}")
print(f"❌ Failed: {len(results['failed'])}/{total}")
print(f"⏭️  Skipped: {len(results['skipped'])}/{total}")

if results["failed"]:
    print("\n❌ FAILED TESTS:")
    for name in results["failed"]:
        print(f"   - {name}")

if results["skipped"]:
    print("\n⏭️  SKIPPED TESTS:")
    for name, reason in results["skipped"]:
        print(f"   - {name}: {reason}")

pass_rate = len(results["passed"]) / (len(results["passed"]) + len(results["failed"])) * 100 if (len(results["passed"]) + len(results["failed"])) > 0 else 0
print(f"\n📈 Pass Rate: {pass_rate:.1f}%")

print("\n" + "=" * 70)
if pass_rate >= 80:
    print("🎉 ALFRED is working well!")
elif pass_rate >= 50:
    print("⚠️  ALFRED has some issues to fix")
else:
    print("❌ ALFRED needs significant work")
print("=" * 70)
