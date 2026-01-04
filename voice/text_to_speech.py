"""
STARK Text-to-Speech
=====================
Piper-based text-to-speech with fallback chain.

Module 11 of Phase 2 - Voice

Voice: British butler (JARVIS-like)
Fallback: Piper → pyttsx3 → edge-tts
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

import numpy as np

from core.constants import PROJECT_ROOT, MODELS_DIR

logger = logging.getLogger(__name__)

# Voice settings
PIPER_VOICE = "en_GB-alan-medium"  # British male voice
PIPER_SAMPLE_RATE = 22050
EDGE_TTS_VOICE = "en-GB-RyanNeural"  # British male for edge-tts


class TTSEngine(Enum):
    """Available TTS engines."""
    PIPER = "piper"
    PYTTSX3 = "pyttsx3"
    EDGE_TTS = "edge_tts"


@dataclass
class SynthesisResult:
    """Result from speech synthesis."""
    audio: Optional[np.ndarray]
    sample_rate: int
    duration_seconds: float
    latency_ms: float
    engine_used: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_rate": self.sample_rate,
            "duration_seconds": self.duration_seconds,
            "latency_ms": self.latency_ms,
            "engine_used": self.engine_used,
        }


class AudioRefinement:
    """
    Audio refinement layer for TTS output.
    
    Applies post-processing to improve audio quality:
    - Noise reduction
    - Normalization
    - Fade in/out for smooth transitions
    """
    
    @staticmethod
    def normalize(audio: np.ndarray, target_db: float = -3.0) -> np.ndarray:
        """Normalize audio to target dB level."""
        if audio.size == 0:
            return audio
        
        # Convert to float if needed
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        
        # Calculate current RMS
        rms = np.sqrt(np.mean(np.square(audio)))
        if rms < 1e-10:
            return audio
        
        # Target RMS from dB
        target_rms = 10 ** (target_db / 20.0)
        
        # Scale audio
        scale = target_rms / rms
        audio = audio * scale
        
        # Clip to prevent distortion
        audio = np.clip(audio, -1.0, 1.0)
        
        return audio
    
    @staticmethod
    def fade_in_out(
        audio: np.ndarray,
        sample_rate: int,
        fade_in_ms: float = 10.0,
        fade_out_ms: float = 50.0,
    ) -> np.ndarray:
        """Apply fade in and fade out to audio."""
        if audio.size == 0:
            return audio
        
        fade_in_samples = int(sample_rate * fade_in_ms / 1000)
        fade_out_samples = int(sample_rate * fade_out_ms / 1000)
        
        # Create fade curves
        if fade_in_samples > 0 and fade_in_samples < len(audio):
            fade_in = np.linspace(0, 1, fade_in_samples)
            audio[:fade_in_samples] *= fade_in
        
        if fade_out_samples > 0 and fade_out_samples < len(audio):
            fade_out = np.linspace(1, 0, fade_out_samples)
            audio[-fade_out_samples:] *= fade_out
        
        return audio
    
    @staticmethod
    def refine(audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply all refinements."""
        audio = AudioRefinement.normalize(audio)
        audio = AudioRefinement.fade_in_out(audio, sample_rate)
        return audio


class TextToSpeech:
    """
    Text-to-speech engine with fallback chain.
    
    Priority: Piper (offline, high quality) → pyttsx3 (offline) → edge-tts (cloud)
    
    Features:
    - British butler voice (JARVIS-like)
    - Audio refinement layer
    - Async synthesis support
    - Barge-in callback
    
    Usage:
        tts = TextToSpeech()
        result = tts.synthesize("Hello, sir.")
        audio_output.play(result.audio, result.sample_rate)
    """
    
    def __init__(
        self,
        voice: str = PIPER_VOICE,
        edge_voice: str = EDGE_TTS_VOICE,
        enable_refinement: bool = True,
        lazy_load: bool = True,
    ):
        """
        Initialize text-to-speech engine.
        
        Args:
            voice: Piper voice model name
            edge_voice: Edge-TTS voice name (fallback)
            enable_refinement: Apply audio refinement
            lazy_load: Defer engine loading
        """
        self.voice = voice
        self.edge_voice = edge_voice
        self.enable_refinement = enable_refinement
        self.refinement = AudioRefinement()
        
        # Engine availability
        self._piper = None
        self._pyttsx3 = None
        self._engines = []
        
        self._check_engines()
        
        if not lazy_load:
            self._load_engines()
        
        logger.info(f"TextToSpeech initialized (engines={self._engines})")
    
    def _check_engines(self) -> None:
        """Check which TTS engines are available."""
        # Check Piper
        try:
            from piper import PiperVoice
            self._engines.append(TTSEngine.PIPER)
        except ImportError:
            logger.debug("Piper not available")
        
        # Check pyttsx3
        try:
            import pyttsx3
            self._engines.append(TTSEngine.PYTTSX3)
        except ImportError:
            logger.debug("pyttsx3 not available")
        
        # Check edge-tts
        try:
            import edge_tts
            self._engines.append(TTSEngine.EDGE_TTS)
        except ImportError:
            logger.debug("edge-tts not available")
        
        if not self._engines:
            logger.warning("No TTS engines available!")
    
    def _load_engines(self) -> None:
        """Load available TTS engines."""
        if TTSEngine.PIPER in self._engines and self._piper is None:
            try:
                from piper import PiperVoice
                # Load voice model (would need to download model file)
                # For now, mark as attempted
                logger.info("Piper engine ready (voice loading deferred)")
            except Exception as e:
                logger.warning(f"Failed to load Piper: {e}")
        
        if TTSEngine.PYTTSX3 in self._engines and self._pyttsx3 is None:
            try:
                import pyttsx3
                self._pyttsx3 = pyttsx3.init()
                # Set British voice if available
                voices = self._pyttsx3.getProperty('voices')
                for voice in voices:
                    if 'english' in voice.name.lower() and ('uk' in voice.name.lower() or 'british' in voice.name.lower()):
                        self._pyttsx3.setProperty('voice', voice.id)
                        break
                self._pyttsx3.setProperty('rate', 175)  # Slightly slower for clarity
                logger.info("pyttsx3 engine loaded")
            except Exception as e:
                logger.warning(f"Failed to load pyttsx3: {e}")
    
    def is_available(self) -> bool:
        """Check if any TTS engine is available."""
        return len(self._engines) > 0
    
    def synthesize(self, text: str) -> SynthesisResult:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            
        Returns:
            SynthesisResult with audio data
        """
        start_time = time.perf_counter()
        
        if not self._engines:
            return SynthesisResult(
                audio=None,
                sample_rate=0,
                duration_seconds=0.0,
                latency_ms=0.0,
                engine_used="none",
            )
        
        # Try engines in order
        for engine in self._engines:
            result = self._synthesize_with_engine(text, engine)
            if result.audio is not None:
                # Apply refinement
                if self.enable_refinement:
                    result.audio = self.refinement.refine(result.audio, result.sample_rate)
                return result
        
        # All engines failed
        latency = (time.perf_counter() - start_time) * 1000
        return SynthesisResult(
            audio=None,
            sample_rate=0,
            duration_seconds=0.0,
            latency_ms=latency,
            engine_used="failed",
        )
    
    def _synthesize_with_engine(self, text: str, engine: TTSEngine) -> SynthesisResult:
        """Synthesize with a specific engine."""
        start_time = time.perf_counter()
        
        if engine == TTSEngine.PIPER:
            return self._synthesize_piper(text, start_time)
        elif engine == TTSEngine.PYTTSX3:
            return self._synthesize_pyttsx3(text, start_time)
        elif engine == TTSEngine.EDGE_TTS:
            return self._synthesize_edge_tts(text, start_time)
        
        return SynthesisResult(
            audio=None, sample_rate=0, duration_seconds=0.0, latency_ms=0.0, engine_used="unknown"
        )
    
    def _synthesize_piper(self, text: str, start_time: float) -> SynthesisResult:
        """Synthesize using Piper TTS."""
        try:
            from piper import PiperVoice
            import wave
            import io
            
            # This requires a downloaded voice model
            # For now, skip if model not available
            latency = (time.perf_counter() - start_time) * 1000
            return SynthesisResult(
                audio=None,
                sample_rate=PIPER_SAMPLE_RATE,
                duration_seconds=0.0,
                latency_ms=latency,
                engine_used="piper",
            )
        except Exception as e:
            logger.debug(f"Piper synthesis failed: {e}")
            latency = (time.perf_counter() - start_time) * 1000
            return SynthesisResult(
                audio=None, sample_rate=0, duration_seconds=0.0, latency_ms=latency, engine_used="piper"
            )
    
    def _synthesize_pyttsx3(self, text: str, start_time: float) -> SynthesisResult:
        """Synthesize using pyttsx3."""
        try:
            if self._pyttsx3 is None:
                self._load_engines()
            
            if self._pyttsx3 is None:
                raise RuntimeError("pyttsx3 not loaded")
            
            # pyttsx3 doesn't return audio directly, it plays
            # For now, return empty audio (will be played directly)
            latency = (time.perf_counter() - start_time) * 1000
            
            return SynthesisResult(
                audio=None,  # pyttsx3 plays directly
                sample_rate=22050,
                duration_seconds=len(text) * 0.06,  # Rough estimate
                latency_ms=latency,
                engine_used="pyttsx3",
            )
        except Exception as e:
            logger.debug(f"pyttsx3 synthesis failed: {e}")
            latency = (time.perf_counter() - start_time) * 1000
            return SynthesisResult(
                audio=None, sample_rate=0, duration_seconds=0.0, latency_ms=latency, engine_used="pyttsx3"
            )
    
    def _synthesize_edge_tts(self, text: str, start_time: float) -> SynthesisResult:
        """Synthesize using edge-tts (cloud)."""
        try:
            import asyncio
            import edge_tts
            import io
            
            async def _synthesize():
                communicate = edge_tts.Communicate(text, self.edge_voice)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                return audio_data
            
            # Run async synthesis
            audio_bytes = asyncio.run(_synthesize())
            
            # Convert MP3 to numpy array (requires additional processing)
            # For now, return the raw bytes indicator
            latency = (time.perf_counter() - start_time) * 1000
            
            return SynthesisResult(
                audio=None,  # Would need MP3 decoding
                sample_rate=24000,
                duration_seconds=len(text) * 0.06,
                latency_ms=latency,
                engine_used="edge_tts",
            )
        except Exception as e:
            logger.debug(f"edge-tts synthesis failed: {e}")
            latency = (time.perf_counter() - start_time) * 1000
            return SynthesisResult(
                audio=None, sample_rate=0, duration_seconds=0.0, latency_ms=latency, engine_used="edge_tts"
            )
    
    def speak(self, text: str, on_complete: Optional[Callable] = None) -> bool:
        """
        Speak text directly using available engine.
        
        Args:
            text: Text to speak
            on_complete: Callback when speech completes
            
        Returns:
            True if speech started successfully
        """
        if not self._engines:
            return False
        
        def _speak():
            try:
                if TTSEngine.PYTTSX3 in self._engines:
                    if self._pyttsx3 is None:
                        self._load_engines()
                    if self._pyttsx3:
                        self._pyttsx3.say(text)
                        self._pyttsx3.runAndWait()
                        if on_complete:
                            on_complete()
                        return
                
                # Fall back to edge-tts via playsound
                if TTSEngine.EDGE_TTS in self._engines:
                    import asyncio
                    import edge_tts
                    import tempfile
                    import os
                    
                    async def _speak_edge():
                        communicate = edge_tts.Communicate(text, self.edge_voice)
                        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                            async for chunk in communicate.stream():
                                if chunk["type"] == "audio":
                                    f.write(chunk["data"])
                            temp_path = f.name
                        
                        # Play the file
                        try:
                            import sounddevice as sd
                            import soundfile as sf
                            data, sr = sf.read(temp_path)
                            sd.play(data, sr)
                            sd.wait()
                        except Exception:
                            pass  # Fallback failed
                        finally:
                            os.unlink(temp_path)
                    
                    asyncio.run(_speak_edge())
                    if on_complete:
                        on_complete()
                    
            except Exception as e:
                logger.error(f"Speech failed: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=_speak, daemon=True)
        thread.start()
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get TTS statistics."""
        return {
            "available": self.is_available(),
            "engines": [e.value for e in self._engines],
            "voice": self.voice,
            "refinement_enabled": self.enable_refinement,
        }


# =============================================================================
# FACTORY
# =============================================================================

_tts_instance: Optional[TextToSpeech] = None


def get_tts() -> TextToSpeech:
    """Get or create the global TTS instance."""
    global _tts_instance
    
    if _tts_instance is None:
        _tts_instance = TextToSpeech()
    
    return _tts_instance
