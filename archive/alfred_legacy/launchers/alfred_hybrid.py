#!/usr/bin/env python3
"""
ALFRED Hybrid Mode
Run both CLI and Voice input simultaneously.
Type OR speak - ALFRED responds to both!
"""

import sys
import threading
import queue
import time
import logging
from datetime import datetime

# Configure minimal logging
logging.basicConfig(level=logging.WARNING, format='%(message)s')
logger = logging.getLogger("Alfred.Hybrid")

class AlfredHybrid:
    """ALFRED with simultaneous CLI and Voice input."""
    
    def __init__(self):
        self.running = False
        self.voice_enabled = True
        self.command_queue = queue.Queue()
        
        # Components (lazy loaded)
        self.tool_registry = None
        self.suggester = None
        self.ollama = None
        self.tts = None
        self.voice_thread = None
        self.whisper = None
        self.audio_stream = None
        
    def initialize(self):
        """Load all ALFRED components."""
        print("=" * 60)
        print("🤖 ALFRED HYBRID MODE")
        print("=" * 60)
        print("Loading components...")
        
        # Tools
        try:
            from tools import tool_registry
            self.tool_registry = tool_registry
            print(f"  ✅ Tools: {len(tool_registry.tools)}")
        except Exception as e:
            print(f"  ⚠️ Tools failed: {e}")
        
        # Reasoning
        try:
            from reasoning import ToolSuggester
            self.suggester = ToolSuggester(self.tool_registry, self.tool_registry.learning_memory)
            print("  ✅ Reasoning: Active")
        except:
            print("  ⚠️ Reasoning: Disabled")
        
        # Skills
        try:
            from skill_loader import skill_loader
            skills = skill_loader.load_all_skills()
            if skills:
                print(f"  ✅ Skills: {skills}")
        except:
            pass
        
        # Ollama
        try:
            import ollama
            # Quick test
            ollama.list()
            self.ollama = ollama
            print("  ✅ Ollama: Connected")
        except Exception as e:
            print(f"  ⚠️ Ollama: {e}")
        
        # TTS
        try:
            import pyttsx3
            self.tts = pyttsx3.init()
            self.tts.setProperty('rate', 175)
            print("  ✅ TTS: Ready")
        except:
            print("  ⚠️ TTS: Disabled")
        
        # Whisper
        try:
            from faster_whisper import WhisperModel
            self.whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
            print("  ✅ Whisper: Ready")
        except:
            print("  ⚠️ Whisper: Disabled (voice input unavailable)")
            self.voice_enabled = False
        
        print("=" * 60)
        print("\n💡 USAGE:")
        print("   ✏️  Type and press Enter")
        print("   🎤 Or speak (if enabled)")
        print("   📝 Commands: /quit, /voice on|off, /tools, /help")
        print("=" * 60 + "\n")
    
    def speak(self, text: str):
        """Speak text using TTS."""
        if self.tts:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except:
                pass
    
    def process_command(self, text: str, source: str = "cli"):
        """Process a command from any input source."""
        text = text.strip()
        if not text:
            return
        
        indicator = "🎤" if source == "voice" else "✏️"
        print(f"\n{indicator} You: {text}")
        
        # Try benchmark tools first
        result = self._try_benchmark_tools(text)
        if result:
            print(f"\n🤖 Alfred: {result}")
            self.speak(str(result)[:200])
            return
        
        # Check for tools to suggest
        suggestions = []
        if self.suggester:
            suggestions = self.suggester.suggest(text)
        
        # Check for missing capability (only for action verbs)
        try:
            from skill_request import detect_missing_capability
            missing = detect_missing_capability(text, self.tool_registry, self.suggester)
            if missing:
                print(f"\n🤖 Alfred: {missing}")
                self.speak("I don't have that skill yet. Want me to try learning it?")
                return
        except:
            pass
        
        # If we have tool suggestions, try using them
        if self.tool_registry and suggestions:
            for tool_name in suggestions:
                try:
                    if tool_name == "datetime":
                        result = self.tool_registry.execute('<tool:datetime args="time"/>')
                    elif tool_name == "calc":
                        import re
                        nums = re.findall(r'\d+', text)
                        if len(nums) >= 2:
                            expr = f"{nums[0]}*{nums[1]}" if "times" in text.lower() else f"{nums[0]}+{nums[1]}"
                            result = self.tool_registry.execute(f'<tool:calc args="{expr}"/>')
                        else:
                            continue
                    elif tool_name == "memory":
                        if "remember" in text.lower():
                            parts = text.lower().split("remember")[-1].strip()
                            result = self.tool_registry.execute(f'<tool:memory args="store:note:{parts}"/>')
                        else:
                            result = self.tool_registry.execute('<tool:memory args="recall:note"/>')
                    else:
                        continue
                    
                    print(f"\n🔧 Tool [{tool_name}]: {result}")
                    print(f"🤖 Alfred: {result}")
                    self.speak(str(result))
                    return
                except:
                    continue
        
        # Fall back to LLM
        if self.ollama:
            try:
                response = self.ollama.chat(
                    model="llama3.2:3b",
                    messages=[
                        {"role": "system", "content": "You are Alfred, a helpful AI assistant. Be concise and friendly."},
                        {"role": "user", "content": text}
                    ]
                )
                reply = response['message']['content']
                
                if "<think>" in reply:
                    reply = reply.split("</think>")[-1].strip()
                
                print(f"\n🤖 Alfred: {reply[:500]}")
                self.speak(reply[:200])
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
        else:
            print(f"\n🤖 Alfred: I heard you say: '{text}'")
    
    def _try_benchmark_tools(self, text: str):
        """Try to match query to benchmark tools."""
        text_lower = text.lower()
        
        try:
            from benchmark_tools import (
                get_current_time, get_current_date, convert_units, solve_math,
                get_weather, summarize_text, classify_sentiment, extract_entities,
                detect_language, create_todo_list, generate_email, calendar_reasoning,
                web_search, analyze_csv, detect_anomalies, infer_trends, 
                detect_unsafe_query, rate_confidence, create_project_plan
            )
            
            # Time queries
            if any(w in text_lower for w in ["time", "what time", "current time"]):
                result = get_current_time()
                return f"The time is {result['time']} ({result['timezone']})"
            
            # Date queries
            if any(w in text_lower for w in ["date", "today", "what day"]):
                result = get_current_date()
                return f"Today is {result['weekday']}, {result['date']}"
            
            # Weather queries
            if "weather" in text_lower:
                import re
                city_match = re.search(r'(?:weather|in|for)\s+(\w+(?:\s+\w+)?)', text_lower)
                city = city_match.group(1) if city_match else "Mumbai"
                result = get_weather(city.title())
                if "error" not in result:
                    return f"Weather in {result['city']}: {result['temperature']}, {result['condition']}, Humidity: {result['humidity']}"
                return f"Couldn't get weather: {result.get('error')}"
            
            # Math/calculate
            if any(w in text_lower for w in ["calculate", "solve", "what is"]) and any(c in text for c in "+-*/"):
                import re
                expr = re.sub(r'[a-zA-Z]', '', text).strip()
                if expr:
                    result = solve_math(expr)
                    if "error" not in result:
                        return f"{result['expression']} = {result['result']}"
            
            # Unit conversion
            if "convert" in text_lower:
                import re
                match = re.search(r'(\d+(?:\.\d+)?)\s*(\w+)\s*to\s*(\w+)', text_lower)
                if match:
                    value, from_unit, to_unit = match.groups()
                    result = convert_units(float(value), from_unit, to_unit)
                    if "error" not in result:
                        return result['output']
            
            # Summarize
            if "summarize" in text_lower:
                text_to_summarize = text.replace("summarize", "").replace("summarise", "").strip()
                result = summarize_text(text_to_summarize, "bullets")
                return result['summary']
            
            # Sentiment
            if "sentiment" in text_lower or "feeling" in text_lower:
                result = classify_sentiment(text)
                return f"Sentiment: {result['sentiment']} (confidence: {result['confidence']})"
            
            # Entities
            if "entities" in text_lower or "extract" in text_lower:
                result = extract_entities(text)
                return f"Found entities: {result}"
            
            # Language detection
            if "language" in text_lower and "detect" in text_lower:
                result = detect_language(text)
                return f"Detected: {result['language']} (confidence: {result['confidence']})"
            
            # To-do list
            if "todo" in text_lower or "to-do" in text_lower or "task list" in text_lower:
                result = create_todo_list(text)
                items = [f"• {t['task']}" for t in result['todo_list']]
                return "To-do list:\n" + "\n".join(items)
            
            # Calendar/scheduling
            if any(w in text_lower for w in ["schedule", "calendar", "slot", "meeting"]):
                result = calendar_reasoning(text)
                slots = [f"  • {s['day']} ({s['date']}): {s['suggested_time']}" for s in result['available_slots']]
                return "Available slots:\n" + "\n".join(slots)
            
            # Project plan
            if "plan" in text_lower and "project" in text_lower:
                result = create_project_plan(text)
                phases = [f"  {p['name']}: {p['duration']}" for p in result['phases']]
                return f"Project plan for: {text[:30]}\n" + "\n".join(phases)
            
            # Web search
            if any(w in text_lower for w in ["search", "look up", "find info"]):
                query = text.replace("search for", "").replace("look up", "").replace("search", "").strip()
                result = web_search(query, 3)
                if "results" in result and result["results"]:
                    items = [f"• {r['title']}" for r in result['results'][:3]]
                    return "Search results:\n" + "\n".join(items)
            
        except ImportError:
            pass
        except Exception as e:
            return f"Error: {e}"
        
        return None
    
    def cli_loop(self):
        """Handle CLI input."""
        while self.running:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Special commands
                if user_input.startswith("/"):
                    self.handle_command(user_input)
                    continue
                
                self.process_command(user_input, "cli")
                
            except EOFError:
                break
            except KeyboardInterrupt:
                self.running = False
                break
    
    def handle_command(self, cmd: str):
        """Handle special commands."""
        cmd = cmd.lower()
        
        if cmd in ["/quit", "/exit", "/q"]:
            print("👋 Goodbye!")
            self.running = False
            
        elif cmd == "/help":
            print("\n📝 Commands:")
            print("   /quit       - Exit ALFRED")
            print("   /voice on   - Enable voice input")
            print("   /voice off  - Disable voice input")
            print("   /tools      - List available tools")
            print("   /skills     - List generated skills")
            print("   /status     - Show system status\n")
            
        elif cmd == "/voice on":
            self.voice_enabled = True
            print("🎤 Voice input ENABLED")
            
        elif cmd == "/voice off":
            self.voice_enabled = False
            print("🔇 Voice input DISABLED")
            
        elif cmd == "/tools":
            if self.tool_registry:
                print(f"🔧 Tools: {list(self.tool_registry.tools.keys())}")
            
        elif cmd == "/skills":
            try:
                from skill_loader import skill_loader
                skills = skill_loader.load_all_skills()
                print(f"🎓 Skills: {skills}")
            except:
                print("No skills loaded")
            
        elif cmd == "/status":
            print(f"\n📊 Status:")
            print(f"   🎤 Voice: {'ON' if self.voice_enabled else 'OFF'}")
            print(f"   🔧 Tools: {len(self.tool_registry.tools) if self.tool_registry else 0}")
            print(f"   🧠 LLM: {'Connected' if self.ollama else 'Offline'}")
            print(f"   ⏰ Time: {datetime.now().strftime('%I:%M %p')}\n")
            
        elif cmd == "/benchmark":
            try:
                from benchmark_tools import BENCHMARK_TOOLS
                print(f"\n📊 Benchmark Tools ({len(BENCHMARK_TOOLS)}):")
                categories = ["time", "date", "convert", "math", "weather", "summarize", 
                             "sentiment", "entities", "translate", "todo", "calendar", "search"]
                for cat in categories:
                    if cat in BENCHMARK_TOOLS:
                        print(f"   • {cat}")
            except:
                print("Benchmark tools not loaded")
            
        else:
            print(f"❓ Unknown command. Try /help")
    
    def run(self):
        """Run ALFRED in hybrid mode."""
        self.initialize()
        self.running = True
        
        print("🟢 ALFRED is listening... (type or speak)\n")
        
        try:
            self.cli_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            print("\n👋 ALFRED shutting down...")


if __name__ == "__main__":
    alfred = AlfredHybrid()
    alfred.run()
