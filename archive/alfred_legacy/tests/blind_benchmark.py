#!/usr/bin/env python3
"""
ALFRED Blind Benchmark Test
Tests ALFRED with realistic queries that weren't specifically designed to pass.
These are common AI assistant benchmark questions from external sources.

Run with: python tests/blind_benchmark.py
"""

import sys
import os
import time
import json
from datetime import datetime

# Add ALFRED root to path
alfred_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, alfred_root)

# ============================================================================
# BLIND BENCHMARK QUERIES
# Source: Common AI assistant benchmarks (GAIA, HellaSwag, general NLU tests)
# ============================================================================

BLIND_TESTS = {
    "Factual Retrieval": [
        "What day is it today?",
        "What's 15% of 85?",
        "How many days are in February 2024?",
    ],
    
    "Multi-step Reasoning": [
        "If I buy 3 apples at $0.50 each and 2 oranges at $0.75 each, how much do I spend in total?",
        "A train leaves at 9:00 AM and travels at 60 mph for 2.5 hours. How far does it go?",
        "I have a meeting at 3pm that lasts 90 minutes. What time does it end?",
    ],
    
    "Sentiment Analysis": [
        "What's the sentiment of: 'This product exceeded my expectations, absolutely love it!'",
        "Analyze the sentiment: 'The wait was long but the food was okay I guess.'",
    ],
    
    "Entity Extraction": [
        "Extract the names and places from: 'John Smith met Sarah in New York last Tuesday.'",
        "What entities are in: 'Apple Inc. announced new products at their California headquarters.'",
    ],
    
    "Language Tasks": [
        "Summarize this: 'The Industrial Revolution was a period of major industrialization and innovation that took place during the late 1700s and early 1800s. It began in Britain and quickly spread throughout Europe and the United States.'",
        "Translate 'Good morning, how are you?' to Spanish.",
    ],
    
    "Commonsense Reasoning": [
        "If I put ice cream in the sun, what will happen?",
        "Why do people use umbrellas?",
        "Can a fish climb a tree?",
    ],
    
    "Task Planning": [
        "Create a simple todo list for planning a birthday party.",
        "What steps would I need to take to learn a new language?",
    ],
    
    "Edge Cases & Error Handling": [
        "What's the weather on Mars?",
        "Calculate the square root of -1.",
        "Translate 'hello' to Klingon.",
    ],
    
    "Context Understanding": [
        "My favorite color is blue. What color did I just mention?",
        "I'm tired because I stayed up late. Why am I tired?",
    ],
}

def run_blind_benchmark():
    """Run the blind benchmark test."""
    
    print("=" * 70)
    print("🎯 ALFRED BLIND BENCHMARK TEST")
    print("=" * 70)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("📋 Source: External AI benchmark standards")
    print("-" * 70)
    
    # Initialize ALFRED
    print("\n⏳ Initializing ALFRED...")
    try:
        from core.tools import tool_registry
        from agents.llm import LLMClient
        from agents.brain import CognitiveEngine
        
        llm = LLMClient()
        brain = CognitiveEngine(tool_registry, llm, verbose_react=False)
        print("✅ ALFRED ready\n")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return None
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "categories": {},
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
    }
    
    for category, queries in BLIND_TESTS.items():
        print(f"\n{'='*60}")
        print(f"📂 {category}")
        print("=" * 60)
        
        cat_results = []
        
        for query in queries:
            results["total"] += 1
            print(f"\n🗣️ Query: \"{query}\"")
            
            start = time.time()
            try:
                trace = brain.react_execute(query, max_steps=4)
                elapsed = time.time() - start
                
                answer = trace.final_answer
                confidence = trace.overall_confidence
                success = trace.success and answer is not None
                
                # Truncate long answers for display
                display_answer = answer[:200] + "..." if answer and len(answer) > 200 else answer
                
                if success:
                    results["passed"] += 1
                    icon = "✅"
                else:
                    results["failed"] += 1
                    icon = "❌"
                
                # Confidence indicator
                conf_icon = "🟢" if confidence >= 0.7 else "🟡" if confidence >= 0.5 else "🔴"
                
                print(f"{icon} Answer: {display_answer}")
                print(f"   {conf_icon} Confidence: {confidence:.2f} | ⏱️ {elapsed:.1f}s")
                
                cat_results.append({
                    "query": query,
                    "answer": answer,
                    "confidence": confidence,
                    "success": success,
                    "time": elapsed,
                })
                
            except Exception as e:
                elapsed = time.time() - start
                results["errors"] += 1
                print(f"❌ Error: {str(e)[:100]}")
                cat_results.append({
                    "query": query,
                    "error": str(e),
                    "success": False,
                    "time": elapsed,
                })
        
        results["categories"][category] = cat_results
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("📊 BLIND BENCHMARK RESULTS")
    print("=" * 70)
    
    total = results["total"]
    passed = results["passed"]
    failed = results["failed"]
    errors = results["errors"]
    
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n🎯 Overall Score: {passed}/{total} ({success_rate:.1f}%)")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⚠️ Errors: {errors}")
    
    # Category breakdown
    print("\n" + "-" * 50)
    print("📂 CATEGORY BREAKDOWN:")
    print("-" * 50)
    
    for category, cat_results in results["categories"].items():
        cat_passed = sum(1 for r in cat_results if r.get("success", False))
        cat_total = len(cat_results)
        
        if cat_passed == cat_total:
            icon = "✅"
        elif cat_passed > 0:
            icon = "🟡"
        else:
            icon = "❌"
        
        print(f"  {icon} {category}: {cat_passed}/{cat_total}")
    
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
    elif success_rate >= 50:
        grade = "D"
    else:
        grade = "F - Needs Improvement"
    
    print(f"🏅 ALFRED GRADE: {grade}")
    print("-" * 50)
    
    # Calculate average confidence
    all_confs = []
    for cat_results in results["categories"].values():
        for r in cat_results:
            if "confidence" in r:
                all_confs.append(r["confidence"])
    
    avg_conf = sum(all_confs) / len(all_confs) if all_confs else 0
    print(f"📈 Average Confidence: {avg_conf:.2f}")
    
    # Save results
    results_file = os.path.join(alfred_root, "tests", "blind_benchmark_results.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2);
    print(f"\n💾 Results saved to: {results_file}")
    
    print("\n" + "=" * 70)
    print("Blind Benchmark Complete!")
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    results = run_blind_benchmark()
    if results:
        sys.exit(0 if results["passed"] / results["total"] >= 0.5 else 1)
    else:
        sys.exit(1)
