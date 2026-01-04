## Context

ALFRED needs a production-quality voice interface that provides hands-free interaction. The current implementation is basic (push-to-talk, fixed recording windows) and scattered across multiple files.

### Stakeholders
- End users wanting voice-first interaction
- Developers extending ALFRED's capabilities

### Constraints
- Must work on CPU (GPU optional for faster processing)
- Must handle noisy environments
- Must have <1 second wake-to-listening latency
- Must support interrupt (user can stop ALFRED mid-speech)

## Goals / Non-Goals

### Goals
- Hands-free wake word activation ("Hey ALFRED")
- Intelligent voice activity detection (no push-to-talk)
- Real-time streaming transcription
- High-quality neural TTS
- Clean integration with existing cognitive architecture

### Non-Goals
- Speaker identification/diarization (future enhancement)
- Multi-language support (English only for v1)
- Cloud-based processing (local-first)
- Custom wake word training (use pre-trained)

## Decisions

### Decision 1: Use state machine architecture
**What**: Implement voice as a finite state machine (IDLE → WAKE_DETECTED → LISTENING → PROCESSING → SPEAKING)
**Why**: Clear state transitions, easier debugging, prevents race conditions
**Alternatives**: Event-driven (more flexible but harder to debug), Polling (simpler but wasteful)

### Decision 2: Singleton VoiceManager
**What**: Single VoiceManager instance managing all voice components
**Why**: Consistent with ALFRED's singleton pattern, prevents audio device conflicts
**Alternatives**: Multiple instances (causes audio conflicts), Factory pattern (unnecessary complexity)

### Decision 3: Ring buffer for audio capture
**What**: Continuous circular buffer capturing last N seconds of audio
**Why**: Enables pre-roll (capture audio before wake word detected), smooth VAD transitions
**Alternatives**: On-demand recording (misses audio, higher latency)

### Decision 4: Piper TTS with pyttsx3 fallback
**What**: Use piper-tts for neural quality, fall back to pyttsx3 if piper unavailable
**Why**: Best quality when available, always works as fallback
**Alternatives**: Edge-tts (requires internet), Coqui TTS (heavy)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      VoiceManager                            │
├──────────────┬──────────────┬───────────────┬───────────────┤
│ AudioCapture │  WakeWord    │     VAD       │    STT        │
│  (sounddev)  │ (openwake)   │  (silero)     │  (whisper)    │
├──────────────┴──────────────┴───────────────┴───────────────┤
│                         TTS Engine                           │
│              (piper-tts with pyttsx3 fallback)              │
├─────────────────────────────────────────────────────────────┤
│                     State Machine                            │
│   IDLE → WAKE_DETECTED → LISTENING → PROCESSING → SPEAKING  │
└─────────────────────────────────────────────────────────────┘
           │                                    ▲
           ▼                                    │
┌─────────────────────────────────────────────────────────────┐
│                    Cognitive Engine                          │
│                   (brain.py → MCP)                          │
└─────────────────────────────────────────────────────────────┘
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Wake word false positives | Adjustable sensitivity, confirmation prompt for low-confidence |
| High CPU usage from continuous listening | VAD-gated processing, model optimization |
| Audio device conflicts | Exclusive device locking, clear error messages |
| Background noise interference | Noise reduction preprocessing, VAD tuning |

## Migration Plan

1. **Phase 1**: Create VoiceManager alongside existing code (no breaking changes)
2. **Phase 2**: Update `alfred_voice.py` to use VoiceManager
3. **Phase 3**: Integrate with SensorHub
4. **Phase 4**: Deprecate `hybrid_input.py` (keep as reference)

### Rollback
If issues arise, users can run old voice implementation by reverting `alfred_voice.py` changes.

## Open Questions

1. Should wake word be configurable by user? (e.g., "Computer", "Jarvis")
2. Should we add a "mute" mode that disables wake word but allows push-to-talk?
3. What's the target latency for wake-to-response? (<2s seems reasonable)
