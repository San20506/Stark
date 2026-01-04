#!/usr/bin/env python3
"""
ALFRED Siri/JARVIS-Style Test (MCP Architecture)
Real conversational queries like actual voice assistant usage.

Run with: python tests/test_jarvis.py
"""

import sys
import os
import time
from datetime import datetime

alfred_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, alfred_root)

# Natural conversational queries like Siri/JARVIS would receive
JARVIS_QUERIES = [
    # Morning routine
    "Hey, what time is it?",
    "What's the weather like today?",
    "What day is it?",
    
    # Quick calculations (like asking while cooking/shopping)
    "Quick math - what's 18 plus 27?",
    "How much is 15% tip on 45 dollars?",
    "Convert 100 fahrenheit to celsius",
    
    # Casual knowledge
    "Who won the last world cup?",
    "How far is the moon from earth?",
    "What's the capital of Japan?",
    
    # Task-oriented (like you'd ask a real assistant)
    "Remind me to call the dentist tomorrow",
    "Make a shopping list: eggs, bread, milk, cheese",
    "What's on my schedule today?",
    
    # Natural conversation
    "I'm feeling tired today",
    "Tell me something interesting",
    "What should I have for lunch?",
    
    # Reasoning
    "If I leave at 9am and it takes 45 minutes to get there, what time do I arrive?",
    "I have a meeting at 3pm. How many hours from now is that?",
]


def run_jarvis_test():
    """Run JARVIS-style natural language test with MCP architecture."""
    
    print("=" * 70)
    print("ALFRED MCP vs JARVIS - Natural Conversation Test")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("Testing with real-world conversational queries")
    print("-" * 70)
    
    # Initialize MCP
    from agents.llm import LLMClient
    from agents.mcp import MasterControlProgram
    
    llm = LLMClient()
    mcp = MasterControlProgram(llm)
    print("MCP Online\n")
    
    results = []
    
    for query in JARVIS_QUERIES:
        print(f"\nUser: \"{query}\"")
        
        start = time.time()
        try:
            response = mcp.process(query)
            elapsed = time.time() - start
            
            answer = response.answer or "No response"
            conf = response.confidence
            modules = [m.value for m in response.modules_used]
            
            # Truncate for display
            display = answer[:120] + "..." if len(answer) > 120 else answer
            
            icon = "[OK]" if conf >= 0.6 else "[??]" if conf >= 0.4 else "[!!]"
            print(f"ALFRED: {display}")
            print(f"   {icon} {conf:.0%} | Modules: {modules} | {elapsed:.1f}s")
            
            results.append({
                "query": query,
                "answer": answer,
                "confidence": conf,
                "time": elapsed,
                "success": True
            })
            
        except Exception as e:
            print(f"Error: {e}")
            results.append({"query": query, "success": False, "error": str(e)})
    
    # Summary
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    successful = [r for r in results if r.get("success", False)]
    high_conf = [r for r in results if r.get("confidence", 0) >= 0.6]
    
    print(f"Responded: {len(successful)}/{len(results)}")
    print(f"High confidence: {len(high_conf)}/{len(results)}")
    print(f"Avg time: {sum(r.get('time', 0) for r in results)/len(results):.1f}s")
    
    score = len(successful) / len(results) * 100
    print(f"\nJARVIS Score: {score:.0f}%")
    
    return results


if __name__ == "__main__":
    run_jarvis_test()
