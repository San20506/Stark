"""
STARK Voice Module
==================
Voice interaction capabilities for STARK.

Components:
- speech_to_text.py: Whisper-based STT
- text_to_speech.py: Piper-based TTS with fallbacks
- wake_word.py: Wake word detection
- audio_io.py: Microphone and speaker handling
"""

from typing import Optional

# Lazy imports to avoid loading dependencies when not using voice
_stt_instance = None
_tts_instance = None
_wake_word_instance = None


def get_stt():
    """Get Speech-to-Text engine."""
    global _stt_instance
    if _stt_instance is None:
        from voice.speech_to_text import SpeechToText
        _stt_instance = SpeechToText()
    return _stt_instance


def get_tts():
    """Get Text-to-Speech engine."""
    global _tts_instance
    if _tts_instance is None:
        from voice.text_to_speech import TextToSpeech
        _tts_instance = TextToSpeech()
    return _tts_instance


def get_wake_word():
    """Get Wake Word detector."""
    global _wake_word_instance
    if _wake_word_instance is None:
        from voice.wake_word import WakeWordDetector
        _wake_word_instance = WakeWordDetector()
    return _wake_word_instance
