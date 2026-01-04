#!/usr/bin/env python3
"""
ALFRED Real-World Test
Tests ALFRED through the actual launcher (alfred.py) like real usage.
Simulates typing queries into the running ALFRED system.

Run with: python tests/test_realworld.py
"""

import sys
import os
import subprocess
import time
import json
from datetime import datetime

# Add ALFRED root to path
alfred_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, alfred_root)

# Test queries - realistic user inputs
TEST_QUERIES = [
    "What time is it?",
    "What's 25 times 4?",
    "What's the weather in London?",
    "Summarize this: Python is a programming language that lets you work quickly.",
    "Create a todo list: buy milk, call mom, finish homework",
    "Take a screenshot and describe what you see",
    "How many days until Christmas?",
]

def run_realworld_test():
    """Run tests through the actual alfred.py launcher."""
    
    print("=" * 70)
    print("🎯 ALFRED REAL-WORLD TEST (via alfred.py)")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("-" * 70)
    
    results = []
    launcher = os.path.join(alfred_root, "launchers", "alfred.py")
    
    for query in TEST_QUERIES:
        print(f"\n🗣️ Query: \"{query}\"")
        
        try:
            # Create input with query followed by exit
            input_text = f"{query}\nexit\n"
            
            start = time.time()
            
            # Run alfred.py with query piped to stdin
            result = subprocess.run(
                [sys.executable, launcher, "--mode", "pro", "--quiet"],
                input=input_text,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=alfred_root,
                env={**os.environ, "PATH": f"C:\\Program Files\\Tesseract-OCR;{os.environ.get('PATH', '')}"}
            )
            
            elapsed = time.time() - start
            
            # Parse output
            output = result.stdout
            
            # Find the response (after "💬" or the answer line)
            lines = output.split('\n')
            answer_lines = []
            capture = False
            
            for line in lines:
                if '💬' in line or '✅ Answer:' in line or 'Final Answer:' in line:
                    capture = True
                    answer_lines.append(line)
                elif capture and line.strip() and not line.startswith('=') and 'Shutdown' not in line:
                    answer_lines.append(line)
                elif 'Shutdown' in line or 'You:' in line:
                    capture = False
            
            answer = '\n'.join(answer_lines).strip()
            if not answer:
                # Fallback: get last substantive lines
                answer = '\n'.join([l for l in lines if l.strip() and not l.startswith('=')])[-500:]
            
            success = len(answer) > 10 and "error" not in answer.lower()
            
            print(f"{'✅' if success else '❌'} Response: {answer[:200]}...")
            print(f"   ⏱️ {elapsed:.1f}s")
            
            results.append({
                "query": query,
                "answer": answer[:500],
                "success": success,
                "time": elapsed,
            })
            
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout (120s)")
            results.append({"query": query, "success": False, "error": "timeout"})
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({"query": query, "success": False, "error": str(e)})
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 REAL-WORLD TEST RESULTS")
    print("=" * 70)
    
    passed = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    print(f"\n🎯 Score: {passed}/{total} ({passed/total*100:.0f}%)")
    
    # Save results
    results_file = os.path.join(alfred_root, "tests", "realworld_results.json")
    with open(results_file, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "results": results}, f, indent=2)
    
    print(f"💾 Results saved: {results_file}")
    print("=" * 70)
    
    return passed, total


if __name__ == "__main__":
    passed, total = run_realworld_test()
    sys.exit(0 if passed >= total // 2 else 1)
