"""
ALFRED Hybrid Input Handler
Allows simultaneous CLI and voice input.
"""

import threading
import queue
import sys
import logging
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger("Alfred.HybridInput")

class HybridInputHandler:
    """
    Handles both CLI and voice input simultaneously.
    Commands from either source are processed the same way.
    """
    
    def __init__(self, on_command: Callable[[str, str], None]):
        """
        Args:
            on_command: Callback function(text, source) where source is "cli" or "voice"
        """
        self.on_command = on_command
        self.command_queue = queue.Queue()
        self.running = False
        self.cli_thread = None
        self.voice_enabled = False
        logger.info("✅ HybridInputHandler initialized")
    
    def start(self):
        """Start listening for both CLI and voice input."""
        self.running = True
        
        # Start CLI input thread
        self.cli_thread = threading.Thread(target=self._cli_input_loop, daemon=True)
        self.cli_thread.start()
        
        logger.info("🎧 Hybrid input active (CLI + Voice)")
        self._print_help()
    
    def stop(self):
        """Stop all input handlers."""
        self.running = False
        logger.info("⏹️ Hybrid input stopped")
    
    def _print_help(self):
        """Print usage instructions."""
        print("\n" + "=" * 60)
        print("ALFRED - Hybrid Input Mode")
        print("=" * 60)
        print("✏️  Type a command and press Enter")
        print("🎤 Or speak (if voice is enabled)")
        print("📝 Commands: /quit, /voice on/off, /help, /tools")
        print("=" * 60 + "\n")
    
    def _cli_input_loop(self):
        """Background thread for CLI input."""
        while self.running:
            try:
                # Show prompt
                sys.stdout.write("You: ")
                sys.stdout.flush()
                
                user_input = input().strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.startswith("/"):
                    self._handle_cli_command(user_input)
                    continue
                
                # Queue the command
                self.command_queue.put(("cli", user_input))
                
                # Call the handler
                if self.on_command:
                    self.on_command(user_input, "cli")
                    
            except EOFError:
                break
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                logger.error(f"CLI input error: {e}")
    
    def _handle_cli_command(self, command: str):
        """Handle special CLI commands."""
        cmd = command.lower()
        
        if cmd in ["/quit", "/exit", "/q"]:
            print("👋 Goodbye!")
            self.running = False
            sys.exit(0)
            
        elif cmd == "/help":
            self._print_help()
            
        elif cmd in ["/voice on", "/v on"]:
            self.voice_enabled = True
            print("🎤 Voice input ENABLED")
            
        elif cmd in ["/voice off", "/v off"]:
            self.voice_enabled = False
            print("🔇 Voice input DISABLED")
            
        elif cmd == "/tools":
            try:
                from tools import tool_registry
                print(f"🔧 Available tools: {list(tool_registry.tools.keys())}")
            except:
                print("Tools not available")
                
        elif cmd == "/skills":
            try:
                from skill_loader import skill_loader
                skills = skill_loader.load_all_skills()
                print(f"🎓 Generated skills: {skills}")
            except:
                print("Skills not available")
                
        elif cmd == "/status":
            print(f"🎤 Voice: {'ON' if self.voice_enabled else 'OFF'}")
            print(f"✏️  CLI: ON")
            print(f"⏰ Time: {datetime.now().strftime('%I:%M %p')}")
            
        else:
            print(f"❓ Unknown command: {command}")
            print("   Try /help for available commands")
    
    def add_voice_command(self, text: str):
        """Add a command from voice input."""
        self.command_queue.put(("voice", text))
        if self.on_command:
            self.on_command(text, "voice")


class AlfredCLI:
    """
    Standalone CLI interface for ALFRED.
    Can run independently or alongside voice.
    """
    
    def __init__(self):
        self.hybrid = None
        self.ollama = None
        self.tts = None
        self.tool_registry = None
        self.suggester = None
        
    def initialize(self):
        """Initialize all ALFRED components."""
        print("🚀 Initializing ALFRED...")
        
        # Import components
        try:
            from tools import tool_registry
            self.tool_registry = tool_registry
            print(f"   ✅ Tools: {len(tool_registry.tools)}")
        except Exception as e:
            print(f"   ⚠️ Tools: {e}")
        
        try:
            from reasoning import ToolSuggester
            self.suggester = ToolSuggester(tool_registry, tool_registry.learning_memory)
            print("   ✅ Reasoning: Loaded")
        except Exception as e:
            print(f"   ⚠️ Reasoning: {e}")
        
        try:
            import ollama
            self.ollama = ollama
            print("   ✅ Ollama: Connected")
        except Exception as e:
            print(f"   ⚠️ Ollama: {e}")
        
        # Load generated skills
        try:
            from skill_loader import skill_loader
            skills = skill_loader.load_all_skills()
            print(f"   ✅ Skills: {len(skills)} loaded")
        except:
            pass
        
        print("✅ ALFRED Ready!\n")
    
    def handle_command(self, text: str, source: str):
        """Process a command from any source."""
        print(f"\n{'🎤' if source == 'voice' else '✏️'} [{source.upper()}]: {text}")
        
        # Get tool suggestions
        suggestions = []
        if self.suggester:
            suggestions = self.suggester.suggest(text)
            if suggestions:
                print(f"   💡 Suggested tools: {suggestions}")
        
        # Check for missing capability
        try:
            from skill_request import detect_missing_capability
            missing = detect_missing_capability(text, self.tool_registry, self.suggester)
            if missing:
                print(f"\n🤖 Alfred: {missing}")
                return
        except:
            pass
        
        # Get LLM response
        if self.ollama:
            try:
                response = self.ollama.chat(
                    model="llama3.2:3b",
                    messages=[
                        {"role": "system", "content": "You are Alfred, a helpful AI assistant. Keep responses brief."},
                        {"role": "user", "content": text}
                    ]
                )
                reply = response['message']['content']
                
                # Execute any tools in response
                if self.tool_registry and "<tool:" in reply:
                    tool_result = self.tool_registry.extract_and_execute_all(reply)
                    if tool_result:
                        print(f"\n🔧 Tool result: {tool_result}")
                        return
                
                print(f"\n🤖 Alfred: {reply}")
                
            except Exception as e:
                print(f"\n❌ LLM error: {e}")
        else:
            # Simple echo if no LLM
            print(f"\n🤖 Alfred: I heard: '{text}'")
    
    def run(self):
        """Run the CLI interface."""
        self.initialize()
        
        self.hybrid = HybridInputHandler(self.handle_command)
        self.hybrid.start()
        
        # Keep main thread alive
        try:
            while self.hybrid.running:
                import time
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            self.hybrid.stop()


if __name__ == "__main__":
    cli = AlfredCLI()
    cli.run()
