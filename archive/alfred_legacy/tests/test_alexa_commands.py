#!/usr/bin/env python3
"""
ALFRED vs Alexa Command Benchmark Test
Tests ALFRED with natural language commands similar to Alexa voice commands.

Run with: python tests/test_alexa_commands.py
"""

import sys
import os
import time

# Add ALFRED root to path
alfred_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, alfred_root)

from core.tools import tool_registry
from agents.llm import LLMClient
from agents.brain import CognitiveEngine

# ============================================================================
# ALEXA-EQUIVALENT TEST COMMANDS
# ============================================================================

ALEXA_COMMANDS = {
    "⏰ Time & Date": [
        "What time is it?",
        "What's today's date?",
        "What day of the week is it?",
    ],
    
    "🌤️ Weather": [
        "What's the weather in Mumbai?",
        "Weather forecast for New York",
    ],
    
    "🔢 Math & Calculations": [
        "What is 25 times 4?",
        "Calculate 15 percent of 200",
        "What's the square root of 144?",
    ],
    
    "📏 Unit Conversion": [
        "Convert 100 kilometers to miles",
        "What is 30 degrees Celsius in Fahrenheit?",
        "Convert 5 pounds to kilograms",
    ],
    
    "🌐 Translation": [
        "Translate hello to Spanish",
        "How do you say thank you in French?",
    ],
    
    "📝 Tasks & Planning": [
        "Create a to-do list: buy groceries, call mom, finish report",
        "Set up a project plan for building a website",
    ],
    
    "📧 Email Generation": [
        "Write a professional email to schedule a meeting tomorrow at 3pm",
    ],
    
    "📊 Knowledge & Facts": [
        "Summarize: The Industrial Revolution marked a period of development from the 1760s to about 1820-1840 when predominantly agrarian societies transformed into industrial and urban societies.",
        "What is the sentiment of: I love this product! It works perfectly!",
    ],
    
    "🧠 Reasoning": [
        "If I have 3 apples and buy 5 more, then give away 2, how many do I have?",
        "What is 20% tip on a $85 restaurant bill?",
    ],
}


def run_alexa_test():
    """Run the Alexa-equivalent command tests."""
    
    print("=" * 70)
    print("🤖 ALFRED vs 🔵 ALEXA - Command Benchmark Test")
    print("=" * 70)
    print("\nThis test runs natural language commands like you'd speak to Alexa.\n")
    
    # Initialize ALFRED
    print("⏳ Initializing ALFRED...")
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
    print("✅ ALFRED ready!\n")
    
    results = []
    total_time = 0
    passed = 0
    total = 0
    
    for category, commands in ALEXA_COMMANDS.items():
        print("=" * 70)
        print(f"📂 {category}")
        print("=" * 70)
        
        for command in commands:
            total += 1
            print(f"\n🗣️ You: \"{command}\"")
            
            start_time = time.time()
            try:
                trace = brain.react_execute(command, max_steps=4)
                elapsed = time.time() - start_time
                total_time += elapsed
                
                # Extract answer
                answer = trace.final_answer
                if answer and len(answer) > 200:
                    answer = answer[:200] + "..."
                
                confidence = trace.overall_confidence
                success = trace.success and answer is not None
                
                if success:
                    passed += 1
                    status = "✅"
                else:
                    status = "❌"
                
                # Confidence indicator
                if confidence >= 0.8:
                    conf_icon = "🟢"
                elif confidence >= 0.6:
                    conf_icon = "🟡"
                else:
                    conf_icon = "🔴"
                
                print(f"\n{status} ALFRED: {answer}")
                print(f"   {conf_icon} Confidence: {confidence:.2f} | ⏱️ Time: {elapsed:.2f}s")
                
                # Show tools used
                used_tools = [s.action for s in trace.steps if s.action]
                if used_tools:
                    print(f"   🔧 Tools: {', '.join(used_tools)}")
                
                results.append({
                    "command": command,
                    "success": success,
                    "confidence": confidence,
                    "time": elapsed,
                    "tools": used_tools,
                })
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"\n❌ ALFRED: Error - {e}")
                print(f"   ⏱️ Time: {elapsed:.2f}s")
                results.append({
                    "command": command,
                    "success": False,
                    "confidence": 0,
                    "time": elapsed,
                    "error": str(e),
                })
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("📊 BENCHMARK RESULTS")
    print("=" * 70)
    
    avg_time = total_time / total if total > 0 else 0
    success_rate = (passed / total * 100) if total > 0 else 0
    
    avg_confidence = sum(r.get("confidence", 0) for r in results) / len(results) if results else 0
    
    print(f"\n🎯 Success Rate: {passed}/{total} ({success_rate:.1f}%)")
    print(f"⏱️ Average Response Time: {avg_time:.2f}s")
    print(f"📈 Average Confidence: {avg_confidence:.2f}")
    print(f"⏱️ Total Test Time: {total_time:.2f}s")
    
    # Category breakdown
    print("\n" + "-" * 50)
    print("📂 CATEGORY BREAKDOWN:")
    print("-" * 50)
    
    idx = 0
    for category, commands in ALEXA_COMMANDS.items():
        cat_results = results[idx:idx + len(commands)]
        idx += len(commands)
        
        cat_passed = sum(1 for r in cat_results if r.get("success", False))
        cat_total = len(cat_results)
        
        status = "✅" if cat_passed == cat_total else "⚠️" if cat_passed > 0 else "❌"
        print(f"  {status} {category}: {cat_passed}/{cat_total}")
    
    # Grade
    print("\n" + "-" * 50)
    if success_rate >= 90:
        grade = "A+ 🏆"
    elif success_rate >= 80:
        grade = "A"
    elif success_rate >= 70:
        grade = "B"
    elif success_rate >= 60:
        grade = "C"
    else:
        grade = "D - Needs Improvement"
    
    print(f"🏅 ALFRED GRADE: {grade}")
    print("-" * 50)
    
    # Comparison note
    print("\n💡 Alexa Comparison Notes:")
    print("   • Alexa has cloud processing, ALFRED runs locally")
    print("   • Alexa has pre-trained skills, ALFRED uses general reasoning")
    print("   • ALFRED shows transparent Thought→Action→Observation chain")
    print("   • ALFRED provides confidence scores for self-awareness")
    
    print("\n" + "=" * 70)
    print("✅ Benchmark Complete!")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = run_alexa_test()
    sys.exit(0 if success else 1)
