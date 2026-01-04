"""
ALFRED Interactive Feature Tester
Test all ALFRED features from a single menu interface.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def pause():
    input("\nPress Enter to continue...")

def print_menu():
    clear()
    print("=" * 60)
    print("        ALFRED Interactive Feature Tester")
    print("=" * 60)
    print("""
    [1] NLU - Test Intent Detection (157 intents)
    [2] Time/Date - Get current time and date
    [3] Calculator - Solve math expressions
    [4] Web Search - Search the web
    [5] Desktop - List open windows
    [6] Desktop - Get mouse position
    [7] Desktop - Open an app
    [8] Desktop - Type text (opens notepad)
    [9] Browser - Navigate to URL
    [10] Browser - Search Google
    [11] Full MCP Test - Interactive conversation
    
    [0] Exit
    """)
    print("=" * 60)

def test_nlu():
    print("\n=== NLU Intent Detection ===")
    try:
        from core.nlu import IntentDetector
        d = IntentDetector()
        d.load_model('models/nlu_jarvis.h5', 'data/jarvis/vocab.pkl')
        print(f"Model loaded: {d.model_loaded}")
        print(f"Intents: 157")
        
        while True:
            query = input("\nEnter query (or 'back' to return): ").strip()
            if query.lower() == 'back':
                break
            if not query:
                continue
            
            result = d.detect(query)
            print(f"\n  Intent: {result.intent}")
            print(f"  Confidence: {result.confidence:.1%}")
            print(f"  Slots: {result.slots}")
    except Exception as e:
        print(f"Error: {e}")
    pause()

def test_time_date():
    print("\n=== Time & Date ===")
    try:
        from core.benchmark_tools import get_current_time, get_current_date
        
        time_result = get_current_time()
        date_result = get_current_date()
        
        print(f"\nTime: {time_result['time']}")
        print(f"Timezone: {time_result['timezone']}")
        print(f"\nDate: {date_result['date']}")
        print(f"Day: {date_result['weekday']}")
    except Exception as e:
        print(f"Error: {e}")
    pause()

def test_calculator():
    print("\n=== Calculator ===")
    try:
        from core.benchmark_tools import solve_math
        
        while True:
            expr = input("\nEnter expression (or 'back'): ").strip()
            if expr.lower() == 'back':
                break
            if not expr:
                continue
            
            result = solve_math(expr)
            if 'result' in result:
                print(f"  Result: {result['result']}")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Error: {e}")
    pause()

def test_web_search():
    print("\n=== Web Search ===")
    try:
        from core.benchmark_tools import web_search
        
        query = input("\nEnter search query: ").strip()
        if not query:
            return
        
        print("\nSearching...")
        result = web_search(query, 5)
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        else:
            print(f"\nFound {result.get('count', 0)} results:\n")
            for i, r in enumerate(result.get('results', []), 1):
                print(f"{i}. {r.get('title', 'No title')}")
                print(f"   {r.get('url', '')[:60]}")
                print()
    except Exception as e:
        print(f"Error: {e}")
    pause()

def test_desktop_windows():
    print("\n=== Desktop - Open Windows ===")
    try:
        from agents.desktop_control import get_desktop_controller
        controller = get_desktop_controller()
        
        windows = controller.get_all_windows()
        print(f"\nFound {len(windows)} windows:\n")
        
        for i, w in enumerate(windows[:15], 1):
            status = "[ACTIVE]" if w.is_active else ""
            print(f"  {i:2}. {w.title[:50]} {status}")
    except Exception as e:
        print(f"Error: {e}")
    pause()

def test_mouse_position():
    print("\n=== Desktop - Mouse Position ===")
    try:
        from agents.desktop_control import get_desktop_controller
        controller = get_desktop_controller()
        
        print("\nMove your mouse around. Press Ctrl+C to stop.\n")
        
        import time
        try:
            for _ in range(20):
                x, y = controller.get_mouse_position()
                print(f"\rMouse position: ({x:4}, {y:4})", end="", flush=True)
                time.sleep(0.2)
        except KeyboardInterrupt:
            pass
        print()
    except Exception as e:
        print(f"Error: {e}")
    pause()

def test_open_app():
    print("\n=== Desktop - Open App ===")
    print("\nExamples: notepad, calc, chrome, code")
    try:
        from agents.desktop_control import get_desktop_controller
        controller = get_desktop_controller()
        
        app = input("\nEnter app name: ").strip()
        if not app:
            return
        
        print(f"\nOpening {app}...")
        result = controller.open_app(app)
        print(f"Result: {'Success' if result else 'Failed'}")
    except Exception as e:
        print(f"Error: {e}")
    pause()

def test_type_text():
    print("\n=== Desktop - Type Text ===")
    print("\nThis will open Notepad and type text.")
    
    confirm = input("Continue? (y/n): ").strip().lower()
    if confirm != 'y':
        return
    
    try:
        from agents.desktop_control import get_desktop_controller
        import time
        
        controller = get_desktop_controller()
        
        print("\nOpening Notepad...")
        controller.open_app('notepad')
        time.sleep(2)
        
        text = input("Enter text to type: ").strip()
        if text:
            print(f"\nTyping: {text}")
            controller.type_text(text)
            print("Done!")
    except Exception as e:
        print(f"Error: {e}")
    pause()

def test_browser_navigate():
    print("\n=== Browser - Navigate ===")
    try:
        from agents.browser_agent import BrowserAgent
        
        url = input("\nEnter URL (or press Enter for google.com): ").strip()
        if not url:
            url = "https://www.google.com"
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        print(f"\nOpening browser and navigating to {url}...")
        
        with BrowserAgent(headless=False) as browser:
            result = browser.goto(url)
            print(f"\nResult: {result.message}")
            if result.data:
                print(f"Title: {result.data.get('title', 'N/A')}")
            
            input("\nPress Enter to close browser...")
    except Exception as e:
        print(f"Error: {e}")
    pause()

def test_browser_google_search():
    print("\n=== Browser - Google Search ===")
    try:
        from agents.browser_agent import BrowserAgent
        
        query = input("\nEnter search query: ").strip()
        if not query:
            return
        
        print(f"\nSearching Google for: {query}")
        
        with BrowserAgent(headless=False) as browser:
            browser.goto("https://www.google.com")
            browser.fill('textarea[name="q"]', query)
            browser.press("Enter")
            browser.wait_for_navigation()
            
            result = browser.get_page_info()
            print(f"\nPage: {result.data.get('title', 'N/A')}")
            
            input("\nPress Enter to close browser...")
    except Exception as e:
        print(f"Error: {e}")
    pause()

def test_mcp_interactive():
    print("\n=== Full MCP Interactive Test ===")
    print("\nStarting ALFRED interactive mode...")
    print("Type 'quit' to return to menu.\n")
    
    try:
        from agents.llm import LLMClient
        from agents.mcp import MasterControlProgram
        
        llm = LLMClient()
        mcp = MasterControlProgram(llm)
        
        print("ALFRED is ready!\n")
        
        while True:
            query = input("You: ").strip()
            if query.lower() in ['quit', 'exit', 'back']:
                break
            if not query:
                continue
            
            print("\nProcessing...")
            result = mcp.process(query)
            
            print(f"\nALFRED: {result.answer}")
            print(f"\n[Modules: {[m.value for m in result.modules_used]}]\n")
    except Exception as e:
        print(f"Error: {e}")
    pause()


def main():
    while True:
        print_menu()
        choice = input("Select option: ").strip()
        
        if choice == '0':
            print("\nGoodbye!")
            break
        elif choice == '1':
            test_nlu()
        elif choice == '2':
            test_time_date()
        elif choice == '3':
            test_calculator()
        elif choice == '4':
            test_web_search()
        elif choice == '5':
            test_desktop_windows()
        elif choice == '6':
            test_mouse_position()
        elif choice == '7':
            test_open_app()
        elif choice == '8':
            test_type_text()
        elif choice == '9':
            test_browser_navigate()
        elif choice == '10':
            test_browser_google_search()
        elif choice == '11':
            test_mcp_interactive()
        else:
            print("Invalid option")
            pause()


if __name__ == "__main__":
    main()
