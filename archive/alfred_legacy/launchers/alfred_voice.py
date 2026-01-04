"""
ALFRED Voice Mode
Simple voice interaction using existing audio utilities.
"""

import os
import sys

# Add ALFRED root to path
alfred_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, alfred_root)

from agents.llm import LLMClient
from agents.mcp import MasterControlProgram

try:
    import sounddevice as sd
    import numpy as np
    from faster_whisper import WhisperModel
    import pyttsx3
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    print("⚠️ Voice dependencies not installed")
    print("   Install: pip install sounddevice faster-whisper pyttsx3")


class VoiceInterface:
    """Simple voice interface for ALFRED."""
    
    def __init__(self, mcp):
        self.mcp = mcp
        
        # Initialize TTS
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 175)  # Speed
        self.tts.setProperty('volume', 0.9)  # Volume
        
        # Initialize STT
        print("Loading Whisper model (this may take a moment)...")
        self.whisper = WhisperModel("base", device="cpu", compute_type="int8")
        print("✓ Whisper loaded")
        
        self.sample_rate = 16000
        self.is_listening = False
    
    def speak(self, text: str):
        """Convert text to speech."""
        print(f"\n🔊 ALFRED: {text}")
        self.tts.say(text)
        self.tts.runAndWait()
    
    def listen(self, duration: int = 5) -> str:
        """
        Listen for voice input.
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Transcribed text
        """
        print(f"\n🎤 Listening for {duration} seconds...")
        
        # Record audio
        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32
        )
        sd.wait()
        
        print("🔄 Processing...")
        
        # Convert to int16
        audio_int16 = (recording.squeeze() * 32767).astype(np.int16)
        
        # Transcribe
        segments, info = self.whisper.transcribe(
            audio_int16,
            language="en",
            beam_size=5
        )
        
        text = " ".join([segment.text for segment in segments]).strip()
        
        if text:
            print(f"📝 You said: \"{text}\"")
        else:
            print("⚠️ No speech detected")
        
        return text
    
    def run(self):
        """Run voice interaction loop."""
        self.speak("Hello! I'm ALFRED. How can I help you?")
        
        print("\n" + "=" * 60)
        print("🎤 Voice Mode Active")
        print("=" * 60)
        print("\nInstructions:")
        print("  - Press ENTER to start recording")
        print("  - Speak your query (5 seconds)")
        print("  - Type 'quit' to exit")
        print("=" * 60)
        
        while True:
            try:
                # Wait for user to press enter
                user_input = input("\n[Press ENTER to speak, or type 'quit'] ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.speak("Goodbye!")
                    break
                
                # Listen for voice input
                query = self.listen(duration=5)
                
                if not query:
                    self.speak("I didn't catch that. Please try again.")
                    continue
                
                # Process through MCP
                print(f"\n🤔 Processing...")
                result = self.mcp.process(query)
                
                # Speak response
                self.speak(result.answer)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Interrupted")
                self.speak("Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                self.speak("Sorry, I encountered an error.")


def main():
    """Run ALFRED in voice mode."""
    
    if not VOICE_AVAILABLE:
        print("\n❌ Voice mode requires additional dependencies")
        print("   Install: pip install sounddevice faster-whisper pyttsx3")
        sys.exit(1)
    
    print("=" * 60)
    print("🤖 ALFRED - Voice Mode")
    print("=" * 60)
    
    # Initialize LLM and MCP
    print("\nInitializing ALFRED...")
    llm = LLMClient()
    mcp = MasterControlProgram(llm)
    
    print("✅ System Online")
    
    # Start voice interface
    voice = VoiceInterface(mcp)
    voice.run()
    
    print("\n👋 Shutdown.")


if __name__ == "__main__":
    main()
