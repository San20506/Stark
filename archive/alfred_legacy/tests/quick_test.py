"""
ALFRED Simple Feature Test
Quick verification of core features.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = 0
failed = 0

def test(name, func):
    global passed, failed
    try:
        if func():
            print(f"PASS: {name}")
            passed += 1
        else:
            print(f"FAIL: {name}")
            failed += 1
    except Exception as e:
        print(f"ERROR: {name} - {str(e)[:50]}")
        failed += 1

print("=" * 60)
print("ALFRED Feature Verification")
print("=" * 60)

# 1. NLU
print("\n[NLU TESTS]")
try:
    from core.nlu import IntentDetector
    detector = IntentDetector()
    detector.load_model("models/nlu_jarvis.h5", "data/jarvis/vocab.pkl")
    
    test("NLU Model Loads", lambda: detector.model_loaded)
    test("NLU Time Intent", lambda: detector.detect("what time is it?").intent == "time")
    test("NLU Calculator Intent", lambda: detector.detect("calculate 5 times 7").intent == "calculator")
except Exception as e:
    print(f"NLU TESTS FAILED: {e}")
    failed += 3

# 2. Tools
print("\n[TOOL TESTS]")
try:
    from core.benchmark_tools import get_current_time, get_current_date, solve_math
    
    test("Tool: Time", lambda: "time" in get_current_time())
    test("Tool: Date", lambda: "date" in get_current_date())
    test("Tool: Math", lambda: solve_math("5 * 7").get("result") == 35)
except Exception as e:
    print(f"TOOL TESTS FAILED: {e}")
    failed += 3

# 3. Desktop Control
print("\n[DESKTOP TESTS]")
try:
    from agents.desktop_control import get_desktop_controller
    controller = get_desktop_controller()
    
    test("Desktop Init", lambda: controller.screen_width > 0)
    test("Desktop Mouse", lambda: controller.get_mouse_position()[0] >= 0)
    test("Desktop Windows", lambda: len(controller.get_all_windows()) > 0)
except Exception as e:
    print(f"DESKTOP TESTS FAILED: {e}")
    failed += 3

# 4. Memory
print("\n[MEMORY TESTS]")
try:
    import chromadb
    test("ChromaDB Available", lambda: True)
except:
    print("SKIP: ChromaDB not installed")

# 5. Web Search
print("\n[WEB TESTS]")
try:
    from core.benchmark_tools import web_search
    result = web_search("Python", 2)
    test("Web Search", lambda: result.get("count", 0) > 0)
except Exception as e:
    print(f"WEB TEST FAILED: {e}")
    failed += 1

# Summary
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)
