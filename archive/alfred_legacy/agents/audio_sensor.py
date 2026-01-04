"""
ALFRED Audio Sensor
Continuous audio monitoring with Voice Activity Detection (VAD).

Features:
- Continuous microphone streaming
- Voice Activity Detection (Silero VAD)
- Audio buffering for speech segments
- Wake word detection integration
- Trigger classification (is user addressing ALFRED?)
"""

import os
import sys
import time
import queue
import logging
import threading
from typing import Callable, Optional, Generator
from dataclasses import dataclass

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("AudioSensor")

# Lazy imports
torch = None
sounddevice = None


@dataclass
class AudioEvent:
    """Audio event from sensor."""
    event_type: str  # "speech_start", "speech_end", "wake_word", "silence"
    audio_data: bytes
    duration_ms: float
    timestamp: float
    confidence: float = 0.0


class AudioSensor:
    """
    Continuous audio monitoring with VAD.
    
    Usage:
        sensor = AudioSensor()
        sensor.start()
        
        for event in sensor.stream():
            if event.event_type == "speech_end":
                process_speech(event.audio_data)
    """
    
    SAMPLE_RATE = 16000  # 16kHz for VAD
    CHUNK_MS = 30  # 30ms chunks
    CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_MS / 1000)
    
    def __init__(
        self,
        vad_threshold: float = 0.5,
        speech_pad_ms: int = 300,
        min_speech_ms: int = 250,
        max_speech_ms: int = 30000
    ):
        """
        Initialize audio sensor.
        
        Args:
            vad_threshold: VAD confidence threshold (0-1)
            speech_pad_ms: Padding around speech segments
            min_speech_ms: Minimum speech duration to trigger
            max_speech_ms: Maximum speech duration before forced cut
        """
        self.vad_threshold = vad_threshold
        self.speech_pad_ms = speech_pad_ms
        self.min_speech_ms = min_speech_ms
        self.max_speech_ms = max_speech_ms
        
        self.vad_model = None
        self.stream = None
        self.running = False
        
        self.audio_buffer = []
        self.speech_buffer = []
        self.is_speaking = False
        self.silence_chunks = 0
        
        self.event_queue = queue.Queue()
        self._load_dependencies()
    
    def _load_dependencies(self):
        """Load VAD model and audio libraries."""
        global torch, sounddevice
        
        try:
            import torch as _torch
            import sounddevice as _sd
            torch = _torch
            sounddevice = _sd
        except ImportError as e:
            logger.error(f"Missing dependencies: {e}")
            logger.info("Install with: pip install torch sounddevice")
            return
        
        # Load Silero VAD
        try:
            self.vad_model, self.vad_utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                trust_repo=True
            )
            logger.info("✅ Silero VAD model loaded")
        except Exception as e:
            logger.warning(f"Silero VAD failed: {e}")
            logger.info("Using energy-based VAD fallback")
            self.vad_model = None
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream."""
        if status:
            logger.warning(f"Audio status: {status}")
        
        # Convert to mono float32
        audio_chunk = indata[:, 0].copy()
        
        # Detect speech
        is_speech = self._detect_speech(audio_chunk)
        
        if is_speech:
            if not self.is_speaking:
                # Speech started
                self.is_speaking = True
                self.speech_buffer = list(self.audio_buffer)  # Include pre-buffer
                self.event_queue.put(AudioEvent(
                    event_type="speech_start",
                    audio_data=b"",
                    duration_ms=0,
                    timestamp=time.time()
                ))
            
            self.speech_buffer.append(audio_chunk)
            self.silence_chunks = 0
            
            # Check max duration
            speech_duration = len(self.speech_buffer) * self.CHUNK_MS
            if speech_duration >= self.max_speech_ms:
                self._end_speech()
        else:
            if self.is_speaking:
                self.speech_buffer.append(audio_chunk)
                self.silence_chunks += 1
                
                # End speech after padding
                silence_ms = self.silence_chunks * self.CHUNK_MS
                if silence_ms >= self.speech_pad_ms:
                    self._end_speech()
        
        # Maintain rolling buffer for pre-speech context
        self.audio_buffer.append(audio_chunk)
        max_buffer = int(self.speech_pad_ms / self.CHUNK_MS)
        if len(self.audio_buffer) > max_buffer:
            self.audio_buffer.pop(0)
    
    def _detect_speech(self, audio_chunk) -> bool:
        """Detect if audio chunk contains speech."""
        if self.vad_model is None:
            # Energy-based fallback
            energy = (audio_chunk ** 2).mean()
            return energy > 0.001
        
        try:
            # Silero VAD
            audio_tensor = torch.from_numpy(audio_chunk).float()
            confidence = self.vad_model(audio_tensor, self.SAMPLE_RATE).item()
            return confidence >= self.vad_threshold
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return False
    
    def _end_speech(self):
        """End current speech segment."""
        if not self.is_speaking:
            return
        
        self.is_speaking = False
        
        # Check minimum duration
        duration_ms = len(self.speech_buffer) * self.CHUNK_MS
        if duration_ms < self.min_speech_ms:
            self.speech_buffer = []
            return
        
        # Combine audio chunks
        import numpy as np
        audio_data = np.concatenate(self.speech_buffer)
        
        self.event_queue.put(AudioEvent(
            event_type="speech_end",
            audio_data=audio_data.tobytes(),
            duration_ms=duration_ms,
            timestamp=time.time(),
            confidence=0.8
        ))
        
        self.speech_buffer = []
        self.silence_chunks = 0
    
    def start(self) -> bool:
        """Start audio sensor."""
        if sounddevice is None:
            logger.error("sounddevice not available")
            return False
        
        try:
            self.running = True
            self.stream = sounddevice.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype='float32',
                blocksize=self.CHUNK_SIZE,
                callback=self._audio_callback
            )
            self.stream.start()
            logger.info("🎤 Audio sensor started")
            return True
        except Exception as e:
            logger.error(f"Failed to start audio: {e}")
            return False
    
    def stop(self):
        """Stop audio sensor."""
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        logger.info("🛑 Audio sensor stopped")
    
    def get_event(self, timeout: float = None) -> Optional[AudioEvent]:
        """Get next audio event (blocking)."""
        try:
            return self.event_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def stream_events(self) -> Generator[AudioEvent, None, None]:
        """Yield audio events as they occur."""
        while self.running:
            event = self.get_event(timeout=0.1)
            if event:
                yield event
    
    def is_active(self) -> bool:
        """Check if sensor is active."""
        return self.running and self.stream is not None


class GatingAudioSensor(AudioSensor):
    """
    Audio sensor with gating model integration.
    Determines if speech is addressed to ALFRED.
    """
    
    WAKE_WORDS = ["alfred", "hey alfred", "ok alfred", "jarvis"]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transcriber = None
    
    def _load_transcriber(self):
        """Load speech recognition for wake word detection."""
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            logger.info("✅ Speech recognition loaded")
        except ImportError:
            logger.warning("speech_recognition not available")
            self.recognizer = None
    
    def is_addressed_to_alfred(self, audio_data: bytes) -> tuple:
        """
        Check if speech is addressed to ALFRED.
        
        Returns:
            (is_trigger, transcript, confidence)
        """
        if self.recognizer is None:
            self._load_transcriber()
        
        if self.recognizer is None:
            return (True, "", 0.5)  # Default to trigger if no recognizer
        
        try:
            import speech_recognition as sr
            import numpy as np
            
            # Convert bytes to AudioData
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
            audio_int16 = (audio_array * 32767).astype(np.int16)
            audio = sr.AudioData(audio_int16.tobytes(), self.SAMPLE_RATE, 2)
            
            # Recognize
            transcript = self.recognizer.recognize_google(audio)
            transcript_lower = transcript.lower()
            
            # Check wake words
            for wake in self.WAKE_WORDS:
                if wake in transcript_lower:
                    return (True, transcript, 0.95)
            
            # Check if seems like a command
            command_patterns = ["what", "when", "how", "can you", "please", "tell me"]
            for pattern in command_patterns:
                if transcript_lower.startswith(pattern):
                    return (True, transcript, 0.7)
            
            return (False, transcript, 0.3)
            
        except Exception as e:
            logger.debug(f"Recognition failed: {e}")
            return (False, "", 0.0)


# Singleton
_audio_sensor = None

def get_audio_sensor() -> AudioSensor:
    """Get or create audio sensor singleton."""
    global _audio_sensor
    if _audio_sensor is None:
        _audio_sensor = GatingAudioSensor()
    return _audio_sensor


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("   ALFRED Audio Sensor Test")
    print("=" * 60)
    
    sensor = get_audio_sensor()
    
    print("\n🎤 Starting audio sensor...")
    print("   Speak to test VAD detection")
    print("   Press Ctrl+C to stop\n")
    
    if not sensor.start():
        print("Failed to start audio sensor")
        sys.exit(1)
    
    try:
        for event in sensor.stream_events():
            if event.event_type == "speech_start":
                print("🎙️ Speech detected...")
            elif event.event_type == "speech_end":
                print(f"✅ Speech ended: {event.duration_ms:.0f}ms")
                
                # Try to transcribe
                if isinstance(sensor, GatingAudioSensor):
                    is_trigger, transcript, conf = sensor.is_addressed_to_alfred(event.audio_data)
                    print(f"   Transcript: '{transcript}'")
                    print(f"   Is trigger: {is_trigger} ({conf:.0%})")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
    
    finally:
        sensor.stop()
        print("✅ Done")
