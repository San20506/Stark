#!/usr/bin/env python3
"""
ALFRED - Unified Launcher (MCP Architecture)
Autonomous Learning Framework for Reasoning, Execution, and Development

Now powered by the Master Control Program (MCP) - a modular agentic architecture
where specialized modules handle different types of queries.

Modes:
  - Pro: Full MCP with all modules
  - Chat: Simple conversational mode
  - Voice: Voice-activated assistant (future)
"""

import sys
import os
import argparse
import logging

# Add ALFRED root to path
alfred_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if alfred_root not in sys.path:
    sys.path.insert(0, alfred_root)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Alfred")


def run_mcp_mode(quiet: bool = False):
    """Run ALFRED with the MCP (Master Control Program) architecture."""
    from agents.llm import LLMClient
    from agents.mcp import MasterControlProgram
    
    print("=" * 60)
    print("🤖 ALFRED - MCP Architecture v5.0")
    print("=" * 60)
    
    # Initialize LLM
    llm = LLMClient()
    
    # Initialize MCP
    mcp = MasterControlProgram(llm)
    
    print("✅ System Online")
    print("💡 Specialized modules loaded:")
    print("   ⏰ Time & Date")
    print("   🌤️ Weather")
    print("   🔢 Math & Calculations")
    print("   👁️ Vision & Screenshots")
    print("   🔍 Web Search")
    print("   📝 Tasks & Todos")
    print("   💻 Code Generation")
    print("   💬 Conversation (LLM)")
    print("=" * 60)
    print("Type your query or 'exit' to quit.\n")
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['/quit', 'exit', 'q', 'quit']:
                break
            
            # Process through MCP
            response = mcp.process(user_input)
            
            # Display response
            print(f"\n🤖 ALFRED: {response.answer}")
            
            if not quiet:
                modules_str = ", ".join([m.value for m in response.modules_used])
                print(f"   📊 Confidence: {response.confidence:.0%} | Modules: {modules_str} | Time: {response.execution_time:.2f}s")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.exception("Error in main loop")
    
    print("\n👋 Goodbye!")


def run_legacy_mode(quiet: bool = False):
    """Run ALFRED with the legacy ReAct brain (for comparison)."""
    from core.tools import tool_registry
    from agents.llm import LLMClient
    from agents.brain import CognitiveEngine
    
    print("=" * 60)
    print("🤖 ALFRED PRO - Legacy ReAct Mode")
    print("=" * 60)
    
    llm = LLMClient()
    brain = CognitiveEngine(tool_registry, llm, verbose_react=not quiet)
    
    print("✅ System Online. ReAct reasoning enabled.")
    print("=" * 60 + "\n")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['/quit', 'exit', 'q']:
                break
            
            # Use ReAct
            trace = brain.react_execute(user_input)
            
            if not brain.verbose_react:
                print(f"\n💬 {trace.final_answer}")
            
        except KeyboardInterrupt:
            break
    
    print("\n👋 Shutdown.")


def run_voice_mode():
    """Run voice-activated mode (future)."""
    print("🎤 Voice mode coming soon!")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="ALFRED - AI Assistant with MCP Architecture"
    )
    parser.add_argument(
        '--mode', 
        choices=['mcp', 'legacy', 'voice'], 
        default='mcp',
        help='Run mode: mcp (default), legacy (ReAct), voice'
    )
    parser.add_argument(
        '--quiet', '-q', 
        action='store_true',
        help='Suppress detailed output'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'mcp':
        run_mcp_mode(quiet=args.quiet)
    elif args.mode == 'legacy':
        run_legacy_mode(quiet=args.quiet)
    elif args.mode == 'voice':
        run_voice_mode()


if __name__ == "__main__":
    main()
