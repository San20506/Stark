"""
STARK Audio I/O
================
Microphone input and speaker output handling.

Module 10a of Phase 2 - Voice
"""

import logging
import threading
import queue
import time
from typing import Optional, Callable, Generator
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# Audio settings
SAMPLE_RATE = 16000  # Whisper prefers 16kHz
CHANNELS = 1  # Mono
FRAME_DURATION = 0.1  # 100ms chunks
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_DURATION)
RMS_THRESHOLD = 0.008  # VAD trigger threshold
SILENCE_TIMEOUT = 1.0  # End utterance after 1s silence
PRE_ROLL_SECONDS = 0.5  # Capture 500ms before speech detected


@dataclass
class AudioConfig:
    """Audio configuration."""
    sample_rate: int = SAMPLE_RATE
    channels: int = CHANNELS
    frame_duration: float = FRAME_DURATION
    rms_threshold: float = RMS_THRESHOLD
    silence_timeout: float = SILENCE_TIMEOUT


def rms(samples: np.ndarray) -> float:
    """Calculate RMS (Root Mean Square) amplitude for VAD."""
    if samples.size == 0:
        return 0.0
    try:
        if samples.dtype == np.int16:
            normalized = samples.astype("float32") / 32768.0
        else:
            normalized = samples.astype("float32")
        return float(np.sqrt(np.mean(np.square(normalized))))
    except Exception:
        return 0.0


class AudioInput:
    """
    Microphone input handler with Voice Activity Detection.
    
    Features:
    - Non-blocking audio capture
    - Simple RMS-based VAD
    - Pre-roll buffer for capturing speech start
    
    Usage:
        audio = AudioInput()
        audio.start()
        for chunk in audio.get_speech():
            process(chunk)
        audio.stop()
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self._stream = None
        self._running = False
        self._audio_queue = queue.Queue()
        self._lock = threading.Lock()
        
        # Check if sounddevice is available
        try:
            import sounddevice as sd
            self._sd = sd
            self._available = True
        except ImportError:
            self._sd = None
            self._available = False
            logger.warning("sounddevice not available. Audio input disabled.")
    
    def is_available(self) -> bool:
        """Check if audio input is available."""
        return self._available
    
    def start(self) -> bool:
        """Start microphone capture."""
        if not self._available:
            return False
        
        if self._running:
            return True
        
        try:
            self._stream = self._sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype='int16',
                blocksize=FRAME_SAMPLES,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._running = True
            logger.info("Audio input started")
            return True
        except Exception as e:
            logger.error(f"Failed to start audio input: {e}")
            return False
    
    def stop(self) -> None:
        """Stop microphone capture."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._running = False
        logger.info("Audio input stopped")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream."""
        if status:
            logger.warning(f"Audio status: {status}")
        self._audio_queue.put(indata.copy())
    
    def get_audio_chunk(self, timeout: float = 0.5) -> Optional[np.ndarray]:
        """Get a single audio chunk."""
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def record_utterance(self, max_duration: float = 10.0) -> Optional[np.ndarray]:
        """
        Record a complete utterance using VAD.
        
        Returns audio when speech is detected followed by silence.
        """
        if not self._running:
            self.start()
        
        frames = []
        pre_roll = []
        speaking = False
        silence_start = None
        start_time = time.time()
        
        pre_roll_frames = int(PRE_ROLL_SECONDS / self.config.frame_duration)
        
        while True:
            chunk = self.get_audio_chunk(timeout=0.2)
            if chunk is None:
                continue
            
            # Check duration limit
            if time.time() - start_time > max_duration:
                logger.warning("Max recording duration reached")
                break
            
            # Calculate RMS for VAD
            amplitude = rms(chunk)
            is_speech = amplitude > self.config.rms_threshold
            
            if is_speech:
                if not speaking:
                    # Speech started - include pre-roll
                    speaking = True
                    frames.extend(pre_roll)
                    logger.debug("Speech detected")
                frames.append(chunk)
                silence_start = None
            else:
                if speaking:
                    frames.append(chunk)
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > self.config.silence_timeout:
                        # Silence timeout - end of utterance
                        logger.debug("End of utterance")
                        break
                else:
                    # Maintain pre-roll buffer
                    pre_roll.append(chunk)
                    if len(pre_roll) > pre_roll_frames:
                        pre_roll.pop(0)
        
        if not frames:
            return None
        
        return np.concatenate(frames)


class AudioOutput:
    """
    Speaker output handler.
    
    Features:
    - Non-blocking audio playback
    - Barge-in support (stop playback on interrupt)
    
    Usage:
        audio = AudioOutput()
        audio.play(audio_data)
        audio.stop()  # Interrupt playback
    """
    
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
        self._playing = False
        self._stop_event = threading.Event()
        
        try:
            import sounddevice as sd
            self._sd = sd
            self._available = True
        except ImportError:
            self._sd = None
            self._available = False
            logger.warning("sounddevice not available. Audio output disabled.")
    
    def is_available(self) -> bool:
        """Check if audio output is available."""
        return self._available
    
    def play(self, audio: np.ndarray, sample_rate: Optional[int] = None, blocking: bool = True) -> bool:
        """
        Play audio data.
        
        Args:
            audio: Audio samples (float32 or int16)
            sample_rate: Sample rate (uses default if None)
            blocking: Wait for playback to complete
        """
        if not self._available:
            return False
        
        sr = sample_rate or self.sample_rate
        self._stop_event.clear()
        self._playing = True
        
        try:
            if blocking:
                self._sd.play(audio, sr)
                self._sd.wait()
            else:
                self._sd.play(audio, sr)
            return True
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
            return False
        finally:
            self._playing = False
    
    def stop(self) -> None:
        """Stop playback immediately (barge-in)."""
        if self._available:
            self._sd.stop()
        self._stop_event.set()
        self._playing = False
    
    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._playing


# =============================================================================
# FACTORY
# =============================================================================

_audio_input: Optional[AudioInput] = None
_audio_output: Optional[AudioOutput] = None


def get_audio_input() -> AudioInput:
    """Get or create audio input singleton."""
    global _audio_input
    if _audio_input is None:
        _audio_input = AudioInput()
    return _audio_input


def get_audio_output() -> AudioOutput:
    """Get or create audio output singleton."""
    global _audio_output
    if _audio_output is None:
        _audio_output = AudioOutput()
    return _audio_output
