"""
ALFRED Interactive Test
Test ALFRED's NLU and MCP with various queries.
"""

import os
import sys

alfred_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, alfred_root)

from agents.llm import LLMClient
from agents.mcp import MasterControlProgram


def run_interactive_test():
    """Run interactive test with ALFRED."""
    
    print("=" * 70)
    print("🤖 ALFRED Interactive Test")
    print("=" * 70)
    
    # Initialize
    print("\nInitializing ALFRED...")
    llm = LLMClient()
    mcp = MasterControlProgram(llm)
    
    print("\n✅ System Online")
    print("\n" + "=" * 70)
    print("Try these queries:")
    print("  - What time is it?")
    print("  - What's the weather in Tokyo?")
    print("  - Calculate 25 times 4")
    print("  - Remind me to call mom")
    print("  - Tell me a joke")
    print("  - Search for Python tutorials")
    print("\nType 'quit' to exit")
    print("=" * 70)
    
    query_count = 0
    
    while True:
        try:
            # Get user input
            query = input("\n💬 You: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            query_count += 1
            
            # Process through MCP
            print(f"\n🤔 Processing...")
            result = mcp.process(query)
            
            # Display result
            print(f"\n🤖 ALFRED: {result.answer}")
            print(f"\n📊 Details:")
            print(f"   Modules used: {[m.value for m in result.modules_used]}")
            if hasattr(result, 'processing_time'):
                print(f"   Processing time: {result.processing_time:.2f}s")
            
        except KeyboardInterrupt:
            print("\n\n🛑 Interrupted")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n📊 Session Summary:")
    print(f"   Queries processed: {query_count}")
    print("\n👋 Goodbye!")


if __name__ == "__main__":
    run_interactive_test()
