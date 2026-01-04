"""
STARK Speech-to-Text
=====================
Whisper-based speech recognition for voice input.

Module 10 of Phase 2 - Voice
"""

import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from core.constants import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Model settings
DEFAULT_MODEL = "small.en"  # Good balance of speed and accuracy
COMPUTE_TYPE = "int8"  # CPU-friendly quantization


@dataclass
class TranscriptionResult:
    """Result from speech transcription."""
    text: str
    language: str
    confidence: float
    duration_seconds: float
    latency_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "confidence": self.confidence,
            "duration_seconds": self.duration_seconds,
            "latency_ms": self.latency_ms,
        }


class SpeechToText:
    """
    Whisper-based speech-to-text engine.
    
    Features:
    - faster-whisper for optimized inference
    - CPU and GPU support
    - Automatic language detection
    - Confidence scoring
    
    Usage:
        stt = SpeechToText()
        result = stt.transcribe(audio_data)
        print(result.text)
    """
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = "auto",
        compute_type: str = COMPUTE_TYPE,
        lazy_load: bool = True,
    ):
        """
        Initialize speech-to-text engine.
        
        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            device: "cpu", "cuda", or "auto"
            compute_type: Quantization type (int8, float16, float32)
            lazy_load: Defer model loading until first use
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        
        self._model = None
        self._available = False
        
        # Check if faster-whisper is available
        try:
            from faster_whisper import WhisperModel
            self._whisper_class = WhisperModel
            self._available = True
        except ImportError:
            self._whisper_class = None
            logger.warning("faster-whisper not installed. STT disabled.")
        
        if not lazy_load and self._available:
            self._load_model()
        
        logger.info(f"SpeechToText initialized (model={model_name}, available={self._available})")
    
    def is_available(self) -> bool:
        """Check if STT is available."""
        return self._available
    
    def _load_model(self) -> None:
        """Load the Whisper model."""
        if self._model is not None:
            return
        
        if not self._available:
            return
        
        logger.info(f"Loading Whisper model: {self.model_name}...")
        start = time.time()
        
        try:
            self._model = self._whisper_class(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            load_time = (time.time() - start) * 1000
            logger.info(f"Whisper model loaded in {load_time:.0f}ms")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self._available = False
    
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = "en",
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.
        
        Args:
            audio: Audio samples (float32 or int16, mono)
            sample_rate: Audio sample rate (16kHz recommended)
            language: Language code or None for auto-detection
            
        Returns:
            TranscriptionResult with text and metadata
        """
        if not self._available:
            return TranscriptionResult(
                text="[STT unavailable]",
                language="",
                confidence=0.0,
                duration_seconds=0.0,
                latency_ms=0.0,
            )
        
        # Ensure model is loaded
        if self._model is None:
            self._load_model()
        
        start_time = time.perf_counter()
        
        # Convert to float32 if needed
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        
        # Calculate duration
        duration = len(audio) / sample_rate
        
        try:
            # Transcribe with faster-whisper
            segments, info = self._model.transcribe(
                audio,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
            )
            
            # Collect text from segments
            texts = []
            confidences = []
            for segment in segments:
                texts.append(segment.text.strip())
                confidences.append(segment.avg_logprob)
            
            text = " ".join(texts)
            avg_confidence = np.mean(confidences) if confidences else 0.0
            # Convert log prob to pseudo-confidence (0-1)
            confidence = min(1.0, max(0.0, 1.0 + avg_confidence / 2.0))
            
            latency = (time.perf_counter() - start_time) * 1000
            
            logger.debug(f"Transcribed {duration:.1f}s audio in {latency:.0f}ms: {text[:50]}...")
            
            return TranscriptionResult(
                text=text,
                language=info.language if info else (language or "en"),
                confidence=confidence,
                duration_seconds=duration,
                latency_ms=latency,
            )
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            latency = (time.perf_counter() - start_time) * 1000
            return TranscriptionResult(
                text="",
                language="",
                confidence=0.0,
                duration_seconds=duration,
                latency_ms=latency,
            )
    
    def transcribe_file(self, path: str, language: Optional[str] = "en") -> TranscriptionResult:
        """
        Transcribe audio from file.
        
        Args:
            path: Path to audio file (WAV, MP3, etc.)
            language: Language code or None for auto-detection
        """
        if not self._available:
            return TranscriptionResult(
                text="[STT unavailable]",
                language="",
                confidence=0.0,
                duration_seconds=0.0,
                latency_ms=0.0,
            )
        
        # Ensure model is loaded
        if self._model is None:
            self._load_model()
        
        start_time = time.perf_counter()
        
        try:
            segments, info = self._model.transcribe(
                path,
                language=language,
                beam_size=5,
                vad_filter=True,
            )
            
            texts = []
            for segment in segments:
                texts.append(segment.text.strip())
            
            text = " ".join(texts)
            latency = (time.perf_counter() - start_time) * 1000
            
            return TranscriptionResult(
                text=text,
                language=info.language if info else (language or "en"),
                confidence=0.9,  # Assume high confidence for file transcription
                duration_seconds=info.duration if info else 0.0,
                latency_ms=latency,
            )
            
        except Exception as e:
            logger.error(f"File transcription failed: {e}")
            return TranscriptionResult(
                text="",
                language="",
                confidence=0.0,
                duration_seconds=0.0,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get STT statistics."""
        return {
            "available": self._available,
            "model": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "loaded": self._model is not None,
        }


# =============================================================================
# FACTORY
# =============================================================================

_stt_instance: Optional[SpeechToText] = None


def get_stt(model_name: str = DEFAULT_MODEL) -> SpeechToText:
    """
    Get or create the global STT instance.
    
    Args:
        model_name: Whisper model to use
        
    Returns:
        SpeechToText instance
    """
    global _stt_instance
    
    if _stt_instance is None:
        _stt_instance = SpeechToText(model_name=model_name)
    
    return _stt_instance
