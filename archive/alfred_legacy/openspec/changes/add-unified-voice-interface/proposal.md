# Change: Add Unified Voice Interface

## Why

ALFRED currently has fragmented voice functionality spread across multiple files (`alfred_voice.py`, `alfred_hybrid.py`, `audio_processor.py`, `audio_sensor.py`, `hybrid_input.py`). The existing implementation:

1. Uses basic push-to-talk (requires pressing Enter) rather than wake word activation
2. Has fixed 5-second recording windows rather than intelligent Voice Activity Detection (VAD)
3. Uses CPU-only Whisper which is slow for real-time interaction
4. Lacks streaming responses during TTS output
5. Doesn't integrate with the SensorHub/GatingModel architecture already built

A unified voice interface will provide a seamless, hands-free experience comparable to commercial voice assistants like Alexa or Google Assistant.

## What Changes

### New Capabilities
- **Wake word detection** - "Hey ALFRED" or "ALFRED" activates listening
- **Continuous VAD** - Automatically detects speech start/end (no push-to-talk)
- **Streaming STT** - Real-time transcription as user speaks
- **Neural TTS** - High-quality voice using piper-tts
- **Interrupt handling** - Stop TTS when user starts speaking
- **Confidence-based fallback** - Falls back to text clarification if speech confidence is low

### Unified Architecture
- Single `VoiceManager` class orchestrating all voice components
- Integration with existing `SensorHub` and `GatingModel`
- Clean separation: Audio capture → VAD → STT → Processing → TTS

### Files Affected
- **NEW**: `agents/voice_manager.py` - Unified voice orchestration
- **MODIFY**: `launchers/alfred_voice.py` - Use new VoiceManager
- **MODIFY**: `agents/sensor_hub.py` - Integrate VoiceManager
- **DEPRECATE**: `utils/hybrid_input.py` - Functionality moved to VoiceManager

## Impact

- **Affected specs**: New `voice-interface` capability
- **Affected code**:
  - `agents/voice_manager.py` (new)
  - `launchers/alfred_voice.py` (modify)
  - `agents/sensor_hub.py` (modify)
  - `utils/hybrid_input.py` (deprecate)
- **Dependencies**: Existing dependencies are sufficient (sounddevice, faster-whisper, piper-tts, silero-vad, openwakeword)
- **Breaking changes**: None - existing `alfred_voice.py` will continue to work but use new architecture
