"""
ALFRED Gating Model
Low-power classifier that determines if input is a trigger or noise.

Purpose: Filter environmental inputs to only process what requires cognitive attention.
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("GatingModel")


class TriggerType(Enum):
    """Types of triggers that require cognitive attention."""
    NONE = "none"           # No trigger (noise)
    VOICE = "voice"         # User speaking to ALFRED
    WAKE_WORD = "wake_word" # Explicit wake word detected
    VISUAL = "visual"       # Screen change requiring attention
    EVENT = "event"         # File/email/calendar trigger
    TIMER = "timer"         # Scheduled task due
    ANOMALY = "anomaly"     # Unexpected system state


@dataclass
class GatingResult:
    """Result from gating model evaluation."""
    is_trigger: bool
    trigger_type: TriggerType
    confidence: float
    should_process: bool
    payload: Dict[str, Any]
    reasoning: str


class GatingModel:
    """
    Low-power gating classifier.
    
    Determines if environmental input should trigger cognitive processing.
    Uses fast, rule-based checks before expensive processing.
    """
    
    # Wake words and trigger phrases
    WAKE_WORDS = ["alfred", "hey alfred", "ok alfred", "jarvis", "hey jarvis"]
    
    # Command indicators (phrases that suggest a command)
    COMMAND_PATTERNS = [
        "what", "when", "where", "how", "why", "who",
        "can you", "could you", "please", "tell me",
        "show me", "open", "close", "run", "start", "stop",
        "calculate", "search", "find", "set", "remind",
        "what's", "what is", "how's", "how is"
    ]
    
    # Visual anomaly indicators
    VISUAL_ANOMALIES = ["error", "warning", "failed", "exception", "crash"]
    
    def __init__(self, sensitivity: float = 0.6):
        """
        Initialize gating model.
        
        Args:
            sensitivity: Trigger threshold (0-1). Higher = more triggers.
        """
        self.sensitivity = sensitivity
        self.last_trigger_time = 0
        self.trigger_cooldown = 1.0  # Seconds between triggers
    
    def evaluate_audio(self, transcript: str, confidence: float = 0.5) -> GatingResult:
        """
        Evaluate audio input for triggers.
        
        Args:
            transcript: Transcribed text from speech
            confidence: Transcription confidence
            
        Returns:
            GatingResult indicating if should trigger
        """
        if not transcript:
            return self._no_trigger("Empty transcript")
        
        text_lower = transcript.lower().strip()
        
        # Check wake words (highest priority)
        for wake in self.WAKE_WORDS:
            if wake in text_lower:
                return GatingResult(
                    is_trigger=True,
                    trigger_type=TriggerType.WAKE_WORD,
                    confidence=0.95,
                    should_process=True,
                    payload={"transcript": transcript, "wake_word": wake},
                    reasoning=f"Wake word '{wake}' detected"
                )
        
        # Check command patterns (starts with = high conf, contains = med conf)
        for pattern in self.COMMAND_PATTERNS:
            if text_lower.startswith(pattern):
                conf = 0.85 * confidence
                return GatingResult(
                    is_trigger=True,
                    trigger_type=TriggerType.VOICE,
                    confidence=conf,
                    should_process=True,
                    payload={"transcript": transcript, "pattern": pattern},
                    reasoning=f"Command pattern '{pattern}' at start"
                )
            elif pattern in text_lower:
                conf = 0.65 * confidence
                if conf >= self.sensitivity:
                    return GatingResult(
                        is_trigger=True,
                        trigger_type=TriggerType.VOICE,
                        confidence=conf,
                        should_process=True,
                        payload={"transcript": transcript, "pattern": pattern},
                        reasoning=f"Command pattern '{pattern}' detected"
                    )
        
        # Check if addressing ALFRED contextually
        alfred_indicators = ["you", "can you", "will you", "please"]
        if any(ind in text_lower for ind in alfred_indicators):
            return GatingResult(
                is_trigger=True,
                trigger_type=TriggerType.VOICE,
                confidence=0.6,
                should_process=True,
                payload={"transcript": transcript},
                reasoning="Contextual addressing detected"
            )
        
        return self._no_trigger(f"No trigger in: '{transcript[:50]}'")
    
    def evaluate_visual(self, screen_analysis: Dict[str, Any]) -> GatingResult:
        """Evaluate visual input for triggers."""
        if not screen_analysis:
            return self._no_trigger("No visual data")
        
        # Check for errors/anomalies
        text = screen_analysis.get("text", "").lower()
        for anomaly in self.VISUAL_ANOMALIES:
            if anomaly in text:
                return GatingResult(
                    is_trigger=True,
                    trigger_type=TriggerType.ANOMALY,
                    confidence=0.8,
                    should_process=True,
                    payload=screen_analysis,
                    reasoning=f"Visual anomaly detected: {anomaly}"
                )
        
        # Check for significant change
        change_ratio = screen_analysis.get("change_ratio", 0)
        if change_ratio > 0.5:  # 50% screen change
            return GatingResult(
                is_trigger=True,
                trigger_type=TriggerType.VISUAL,
                confidence=change_ratio,
                should_process=True,
                payload=screen_analysis,
                reasoning=f"Significant screen change: {change_ratio:.0%}"
            )
        
        return self._no_trigger("No visual trigger")
    
    def evaluate_event(self, event_data: Dict[str, Any]) -> GatingResult:
        """Evaluate system event for triggers."""
        event_type = event_data.get("type", "")
        
        # File events
        if event_type in ["file_created", "file_modified"]:
            return GatingResult(
                is_trigger=True,
                trigger_type=TriggerType.EVENT,
                confidence=0.9,
                should_process=True,
                payload=event_data,
                reasoning=f"File event: {event_type}"
            )
        
        # Timer events
        if event_type == "timer":
            return GatingResult(
                is_trigger=True,
                trigger_type=TriggerType.TIMER,
                confidence=1.0,
                should_process=True,
                payload=event_data,
                reasoning="Scheduled timer triggered"
            )
        
        return self._no_trigger(f"Unhandled event type: {event_type}")
    
    def _no_trigger(self, reason: str) -> GatingResult:
        """Return a no-trigger result."""
        return GatingResult(
            is_trigger=False,
            trigger_type=TriggerType.NONE,
            confidence=0.0,
            should_process=False,
            payload={},
            reasoning=reason
        )
    
    def check_cooldown(self) -> bool:
        """Check if we're in trigger cooldown period."""
        elapsed = time.time() - self.last_trigger_time
        return elapsed >= self.trigger_cooldown
    
    def record_trigger(self):
        """Record that a trigger occurred."""
        self.last_trigger_time = time.time()


# Singleton
_gating_model = None

def get_gating_model() -> GatingModel:
    """Get or create gating model singleton."""
    global _gating_model
    if _gating_model is None:
        _gating_model = GatingModel()
    return _gating_model


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("   ALFRED Gating Model Test")
    print("=" * 60)
    
    model = get_gating_model()
    
    test_phrases = [
        "Hey Alfred, what time is it?",
        "What's the weather today?",
        "Can you open Chrome?",
        "The quick brown fox jumps over the lazy dog",
        "I'm just talking to myself here",
        "Please remind me to call mom",
        "Calculate 25 times 4",
    ]
    
    print("\n Testing audio triggers:")
    print("-" * 60)
    
    for phrase in test_phrases:
        result = model.evaluate_audio(phrase, confidence=0.8)
        status = "TRIGGER" if result.is_trigger else "IGNORE"
        print(f"  [{status}] '{phrase[:40]}'")
        if result.is_trigger:
            print(f"          Type: {result.trigger_type.value}, Conf: {result.confidence:.0%}")
    
    print("\n✅ Test complete!")
