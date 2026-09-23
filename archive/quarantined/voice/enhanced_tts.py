"""
STARK Enhanced TTS with ElevenLabs
===================================
High-quality text-to-speech using ElevenLabs API.

Priority: ElevenLabs → edge-tts → pyttsx3
"""

import logging
import os
import threading
from typing import Optional
import time

logger = logging.getLogger(__name__)


class EnhancedTTS:
    """
    Enhanced TTS with ElevenLabs for natural voice.
    
    Features:
    - ElevenLabs (premium, natural)
    - GPT-SoVITS (self-hosted, high quality)
    - edge-tts (free, cloud)
    - pyttsx3 (offline fallback)
    """
    
    def __init__(self):
        """Initialize enhanced TTS."""
        self.api_key = os.environ.get('ELEVENLABS_API_KEY')
        self.voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam - natural British male
        
        self.gpt_sovits_url = os.environ.get('GPT_SOVITS_API_URL')
        
        # Check available engines
        self.has_elevenlabs = False
        self.has_gpt_sovits = False
        self.has_edge_tts = False
        self.has_pyttsx3 = False
        
        self._check_engines()
        
        logger.info(f"Enhanced TTS: ElevenLabs={self.has_elevenlabs}, GPT-SoVITS={self.has_gpt_sovits}, Edge={self.has_edge_tts}, pyttsx3={self.has_pyttsx3}")
    
    def _check_engines(self):
        """Check which engines are available."""
        # ElevenLabs
        if self.api_key:
            try:
                from elevenlabs import VoiceSettings, client
                self.has_elevenlabs = True
                logger.info("✅ ElevenLabs available (high quality)")
            except ImportError:
                logger.warning("ElevenLabs API key found but package not installed: pip install elevenlabs")
        
        # GPT-SoVITS
        if self.gpt_sovits_url:
            try:
                import requests
                # Basic check if the URL is reachable, though not a full API check
                response = requests.get(f"{self.gpt_sovits_url}/health", timeout=5)
                if response.status_code == 200:
                    self.has_gpt_sovits = True
                    logger.info(f"✅ GPT-SoVITS available at {self.gpt_sovits_url} (self-hosted)")
                else:
                    logger.warning(f"GPT-SoVITS API URL found but health check failed (status {response.status_code}): {self.gpt_sovits_url}")
            except ImportError:
                logger.warning("GPT-SoVITS API URL found but 'requests' package not installed: pip install requests")
            except requests.exceptions.RequestException as e:
                logger.warning(f"GPT-SoVITS API URL found but connection failed: {e}")
        
        # edge-tts
        try:
            import edge_tts
            self.has_edge_tts = True
            logger.info("✅ edge-tts available (cloud)")
        except ImportError:
            pass
        
        # pyttsx3
        try:
            import pyttsx3
            self.has_pyttsx3 = True
            logger.info("✅ pyttsx3 available (offline)")
        except ImportError:
            pass
    
    def speak(self, text: str) -> bool:
        """
        Speak text using best available engine.
        
        Args:
            text: Text to speak
            
        Returns:
            True if speech started
        """
        # Try ElevenLabs first
        if self.has_elevenlabs:
            try:
                return self._speak_elevenlabs(text)
            except Exception as e:
                logger.error(f"ElevenLabs failed: {e}")
        
        # Fallback to edge-tts
        if self.has_edge_tts:
            try:
                return self._speak_edge_tts(text)
            except Exception as e:
                logger.error(f"edge-tts failed: {e}")
        
        # Final fallback to pyttsx3
        if self.has_pyttsx3:
            try:
                return self._speak_pyttsx3(text)
            except Exception as e:
                logger.error(f"pyttsx3 failed: {e}")
        
        logger.error("No TTS engines available!")
        return False
    
    def _speak_elevenlabs(self, text: str) -> bool:
        """Speak using ElevenLabs API."""
        from elevenlabs import play, stream
        from elevenlabs.client import ElevenLabs
        
        client = ElevenLabs(api_key=self.api_key)
        
        audio = client.generate(
            text=text,
            voice=self.voice_id,
            model="eleven_monolingual_v1",
            stream=True
        )
        
        # Stream audio
        stream(audio)
        return True
    
    def _speak_edge_tts(self, text: str) -> bool:
        """Speak using edge-tts (Microsoft)."""
        import asyncio
        import edge_tts
        import tempfile
        import os
        
        async def _speak():
            voice = "en-GB-RyanNeural"  # British male
            communicate = edge_tts.Communicate(text, voice)
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name
                await communicate.save(temp_path)
            
            # Play audio
            try:
                import sounddevice as sd
                import soundfile as sf
                data, sr = sf.read(temp_path)
                sd.play(data, sr)
                sd.wait()
            finally:
                os.unlink(temp_path)
        
        asyncio.run(_speak())
        return True
    
    def _speak_pyttsx3(self, text: str) -> bool:
        """Speak using pyttsx3 (offline)."""
        import pyttsx3
        
        engine = pyttsx3.init()
        
        # Try to set British voice
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower() and 'british' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        engine.setProperty('rate', 175)  # Smooth pace
        engine.say(text)
        engine.runAndWait()
        return True


# Global instance
_enhanced_tts = None


def get_enhanced_tts() -> EnhancedTTS:
    """Get or create enhanced TTS."""
    global _enhanced_tts
    if _enhanced_tts is None:
        _enhanced_tts = EnhancedTTS()
    return _enhanced_tts
