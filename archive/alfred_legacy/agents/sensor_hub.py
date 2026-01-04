"""
ALFRED Sensor Hub
Unified interface to all perceptual inputs with gating.

Combines:
- Audio Sensor (voice detection)
- Visual Sensor (screen monitoring)
- Event Monitor (file/email/calendar)
- Gating Model (trigger filtering)
"""

import os
import sys
import time
import queue
import logging
import threading
from typing import Generator, Optional, Callable
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.gating_model import GatingModel, GatingResult, TriggerType, get_gating_model

logger = logging.getLogger("SensorHub")


class SensorType(Enum):
    AUDIO = "audio"
    VISUAL = "visual"
    EVENT = "event"


@dataclass
class SensorEvent:
    """Unified sensor event."""
    sensor_type: SensorType
    trigger_type: TriggerType
    payload: dict
    confidence: float
    timestamp: float
    transcript: str = ""


class SensorHub:
    """
    Unified interface to all perceptual inputs.
    
    Usage:
        hub = SensorHub()
        hub.start()
        
        for event in hub.stream_triggers():
            # Only receive filtered triggers
            process_trigger(event)
    """
    
    def __init__(self, enable_audio: bool = True, enable_visual: bool = False):
        """
        Initialize sensor hub.
        
        Args:
            enable_audio: Enable audio sensor
            enable_visual: Enable visual sensor (periodic screenshots)
        """
        self.enable_audio = enable_audio
        self.enable_visual = enable_visual
        
        self.gating = get_gating_model()
        self.audio_sensor = None
        self.event_queue = queue.Queue()
        self.running = False
        
        self._audio_thread = None
        self._visual_thread = None
    
    def start(self) -> bool:
        """Start all enabled sensors."""
        self.running = True
        
        # Start audio sensor
        if self.enable_audio:
            try:
                from agents.audio_sensor import get_audio_sensor
                self.audio_sensor = get_audio_sensor()
                if self.audio_sensor.start():
                    self._audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
                    self._audio_thread.start()
                    logger.info("🎤 Audio sensor started")
                else:
                    logger.warning("Audio sensor failed to start")
            except Exception as e:
                logger.error(f"Audio sensor error: {e}")
        
        # Start visual sensor (placeholder)
        if self.enable_visual:
            self._visual_thread = threading.Thread(target=self._visual_loop, daemon=True)
            self._visual_thread.start()
            logger.info("👁️ Visual sensor started")
        
        logger.info("✅ Sensor Hub started")
        return True
    
    def stop(self):
        """Stop all sensors."""
        self.running = False
        
        if self.audio_sensor:
            self.audio_sensor.stop()
        
        logger.info("🛑 Sensor Hub stopped")
    
    def _audio_loop(self):
        """Process audio events in background."""
        while self.running and self.audio_sensor:
            event = self.audio_sensor.get_event(timeout=0.1)
            if event and event.event_type == "speech_end":
                # Transcribe and gate
                is_trigger, transcript, conf = self.audio_sensor.is_addressed_to_alfred(
                    event.audio_data
                )
                
                if transcript:
                    # Run through gating model
                    gate_result = self.gating.evaluate_audio(transcript, conf)
                    
                    if gate_result.is_trigger:
                        self.event_queue.put(SensorEvent(
                            sensor_type=SensorType.AUDIO,
                            trigger_type=gate_result.trigger_type,
                            payload=gate_result.payload,
                            confidence=gate_result.confidence,
                            timestamp=event.timestamp,
                            transcript=transcript
                        ))
                        self.gating.record_trigger()
                        logger.info(f"🎯 Audio trigger: '{transcript[:50]}'")
                    else:
                        logger.debug(f"🔇 Ignored: '{transcript[:50]}'")
    
    def _visual_loop(self):
        """Monitor screen for visual triggers."""
        last_analysis = None
        
        while self.running:
            time.sleep(5)  # Check every 5 seconds
            
            try:
                from agents.vision import get_vision_client
                vision = get_vision_client()
                
                # Capture and analyze
                analysis = vision.describe_screen()
                
                if last_analysis and analysis:
                    # Compare for significant changes
                    # (simplified - real implementation would compare embeddings)
                    gate_result = self.gating.evaluate_visual({
                        "text": analysis,
                        "change_ratio": 0.0  # Placeholder
                    })
                    
                    if gate_result.is_trigger:
                        self.event_queue.put(SensorEvent(
                            sensor_type=SensorType.VISUAL,
                            trigger_type=gate_result.trigger_type,
                            payload={"analysis": analysis},
                            confidence=gate_result.confidence,
                            timestamp=time.time()
                        ))
                
                last_analysis = analysis
                
            except Exception as e:
                logger.debug(f"Visual check failed: {e}")
    
    def get_trigger(self, timeout: float = None) -> Optional[SensorEvent]:
        """Get next trigger event (blocking)."""
        try:
            return self.event_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def stream_triggers(self) -> Generator[SensorEvent, None, None]:
        """Yield trigger events as they occur."""
        while self.running:
            event = self.get_trigger(timeout=0.1)
            if event:
                yield event
    
    def add_event_trigger(self, event_type: str, payload: dict):
        """Manually add an event trigger (from EventMonitor)."""
        gate_result = self.gating.evaluate_event({
            "type": event_type,
            **payload
        })
        
        if gate_result.is_trigger:
            self.event_queue.put(SensorEvent(
                sensor_type=SensorType.EVENT,
                trigger_type=gate_result.trigger_type,
                payload=payload,
                confidence=gate_result.confidence,
                timestamp=time.time()
            ))


# Singleton
_sensor_hub = None

def get_sensor_hub() -> SensorHub:
    """Get or create sensor hub singleton."""
    global _sensor_hub
    if _sensor_hub is None:
        _sensor_hub = SensorHub()
    return _sensor_hub


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
    
    print("=" * 60)
    print("   ALFRED Sensor Hub Test")
    print("=" * 60)
    print("\n🎤 Listening for voice commands...")
    print("   Say 'Hey Alfred' or ask a question")
    print("   Press Ctrl+C to stop\n")
    
    hub = get_sensor_hub()
    hub.start()
    
    try:
        for event in hub.stream_triggers():
            print(f"\n🎯 TRIGGER DETECTED!")
            print(f"   Type: {event.trigger_type.value}")
            print(f"   Source: {event.sensor_type.value}")
            print(f"   Confidence: {event.confidence:.0%}")
            if event.transcript:
                print(f"   Transcript: '{event.transcript}'")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
    
    finally:
        hub.stop()
        print("✅ Done")
