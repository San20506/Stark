#!/usr/bin/env python3
"""
ALFRED PRO - The Autonomous Agent
Implements the 7-Tier JARVIS Benchmark Loop
"""

import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Alfred.Pro")

# Add path
sys.path.append("modules")

def main():
    print("=" * 60)
    print("🤖 ALFRED PRO - AUTONOMOUS AGENT v2.0")
    print("=" * 60)
    
    # 1. Initialize Components
    try:
        from tools import tool_registry
        from modules.llm import LLMClient
        from modules.brain import CognitiveEngine
        
        # Connect LLM
        llm = LLMClient()
        
        # Initialize Brain (The Cognitive Core)
        brain = CognitiveEngine(tool_registry, llm)
        
        print("✅ System Online. Ready for complex tasks.")
        print("(Try: 'Create a plan to research quantum computing')")
        
    except ImportError as e:
        print(f"❌ Startup Error: {e}")
        return

    # 2. Main Agent Execution Loop
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input: continue
            if user_input.lower() in ['/quit', 'exit']: break
            
            # --- PHASE 1: PERCEIVE (Tier 1) ---
            intent = brain.perceive(user_input)
            
            if intent == "complex_goal":
                print(f"🧠 Detected Complex Goal. Initiating Planning Sequence...")
                
                # --- PHASE 2: PLAN (Tier 3) ---
                goal = brain.formulate_plan(user_input)
                
                print(f"\n📋 PLAN GENERATED for: {goal.description}")
                for i, task in enumerate(goal.tasks):
                    print(f"  {i+1}. {task.description} [{task.tool or 'thinking'}]")
                
                confirm = input("\nExecute this plan? (y/n): ")
                if confirm.lower() == 'y':
                    # --- PHASE 3: EXECUTE (Tier 6) ---
                    print("🚀 Executing...")
                    status = brain.execute_goal(goal)
                    print(f"\n✅ Goal Status: {status.value}")
                    
            else:
                # Standard Direct Response (Chat/Simple Tools)
                response = brain.handle_direct_command(user_input)
                print(f"💬 {response}")
                
        except KeyboardInterrupt:
            break
            
    print("👋 Shutdown.")

if __name__ == "__main__":
    main()
