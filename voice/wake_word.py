"""
STARK Wake Word Detector
=========================
"Hey STARK" wake word detection.

Module 12 of Phase 2 - Voice
"""

import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

import numpy as np

from voice.audio_io import get_audio_input, AudioInput, SAMPLE_RATE

logger = logging.getLogger(__name__)

# Wake word settings
WAKE_WORD = "hey_stark"  # Custom wake word model name
DETECTION_THRESHOLD = 0.5  # Minimum confidence for activation


@dataclass
class WakeWordEvent:
    """Wake word detection event."""
    word: str
    confidence: float
    timestamp: float


class WakeWordDetector:
    """
    Wake word detection using openwakeword.
    
    Listens for "Hey STARK" to activate voice interaction.
    
    Features:
    - Low-latency detection
    - Configurable sensitivity
    - Callback on detection
    
    Usage:
        detector = WakeWordDetector()
        detector.on_wake(lambda: print("Wake word detected!"))
        detector.start()
    """
    
    def __init__(
        self,
        threshold: float = DETECTION_THRESHOLD,
        lazy_load: bool = True,
    ):
        """
        Initialize wake word detector.
        
        Args:
            threshold: Detection confidence threshold (0-1)
            lazy_load: Defer model loading
        """
        self.threshold = threshold
        self._model = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list = []
        self._audio_input: Optional[AudioInput] = None
        self._available = False
        
        # Check availability
        try:
            import openwakeword
            self._oww = openwakeword
            self._available = True
        except ImportError:
            self._oww = None
            logger.warning("openwakeword not installed. Wake word detection disabled.")
        
        if not lazy_load and self._available:
            self._load_model()
        
        logger.info(f"WakeWordDetector initialized (available={self._available})")
    
    def is_available(self) -> bool:
        """Check if wake word detection is available."""
        return self._available
    
    def _load_model(self) -> None:
        """Load the wake word model."""
        if self._model is not None:
            return
        
        if not self._available:
            return
        
        try:
            from openwakeword.model import Model
            
            # Try to load custom "hey_stark" model, fall back to built-in
            try:
                self._model = Model(wakeword_models=[WAKE_WORD])
                logger.info(f"Loaded custom wake word model: {WAKE_WORD}")
            except Exception:
                # Fall back to built-in models
                self._model = Model()
                logger.info("Loaded default wake word models (alexa, hey_jarvis, etc.)")
                
        except Exception as e:
            logger.error(f"Failed to load wake word model: {e}")
            self._available = False
    
    def on_wake(self, callback: Callable[[WakeWordEvent], None]) -> None:
        """
        Register callback for wake word detection.
        
        Args:
            callback: Function to call when wake word detected
        """
        self._callbacks.append(callback)
    
    def start(self) -> bool:
        """Start listening for wake word."""
        if not self._available:
            return False
        
        if self._running:
            return True
        
        # Load model
        if self._model is None:
            self._load_model()
        
        if self._model is None:
            return False
        
        # Start audio input
        self._audio_input = get_audio_input()
        if not self._audio_input.start():
            return False
        
        # Start detection thread
        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        
        logger.info("Wake word detection started")
        return True
    
    def stop(self) -> None:
        """Stop listening for wake word."""
        self._running = False
        
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        
        if self._audio_input is not None:
            self._audio_input.stop()
        
        logger.info("Wake word detection stopped")
    
    def _detection_loop(self) -> None:
        """Main detection loop."""
        while self._running:
            try:
                # Get audio chunk
                chunk = self._audio_input.get_audio_chunk(timeout=0.2)
                if chunk is None:
                    continue
                
                # Convert to int16 if needed
                if chunk.dtype != np.int16:
                    chunk = (chunk * 32768).astype(np.int16)
                
                # Run detection
                predictions = self._model.predict(chunk.flatten())
                
                # Check for wake word
                for word, score in predictions.items():
                    if score >= self.threshold:
                        event = WakeWordEvent(
                            word=word,
                            confidence=float(score),
                            timestamp=time.time(),
                        )
                        logger.info(f"Wake word detected: {word} ({score:.2f})")
                        self._trigger_callbacks(event)
                        
                        # Clear predictions to avoid repeat triggers
                        self._model.reset()
                        break
                        
            except Exception as e:
                logger.error(f"Detection error: {e}")
                time.sleep(0.1)
    
    def _trigger_callbacks(self, event: WakeWordEvent) -> None:
        """Trigger all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def is_running(self) -> bool:
        """Check if detector is running."""
        return self._running
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            "available": self._available,
            "running": self._running,
            "threshold": self.threshold,
            "callbacks_registered": len(self._callbacks),
        }


# =============================================================================
# FACTORY
# =============================================================================

_detector_instance: Optional[WakeWordDetector] = None


def get_wake_word_detector() -> WakeWordDetector:
    """Get or create the global wake word detector."""
    global _detector_instance
    
    if _detector_instance is None:
        _detector_instance = WakeWordDetector()
    
    return _detector_instance
