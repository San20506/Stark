## 1. Core Voice Manager
- [ ] 1.1 Create `agents/voice_manager.py` with `VoiceManager` class
- [ ] 1.2 Implement wake word detection using openwakeword
- [ ] 1.3 Implement continuous VAD using silero-vad
- [ ] 1.4 Implement streaming STT using faster-whisper
- [ ] 1.5 Implement neural TTS using piper-tts with fallback to pyttsx3
- [ ] 1.6 Add interrupt detection (stop TTS when user speaks)

## 2. Audio Pipeline
- [ ] 2.1 Create audio capture thread with ring buffer
- [ ] 2.2 Implement VAD-triggered recording (start on speech, stop on silence)
- [ ] 2.3 Add audio preprocessing (noise reduction, normalization)
- [ ] 2.4 Implement audio output with queue management

## 3. Integration
- [ ] 3.1 Integrate VoiceManager with SensorHub
- [ ] 3.2 Connect to GatingModel for trigger classification
- [ ] 3.3 Update `alfred_voice.py` to use VoiceManager
- [ ] 3.4 Add voice mode to main `alfred.py` launcher

## 4. State Machine
- [ ] 4.1 Implement voice states: IDLE → LISTENING → PROCESSING → SPEAKING → IDLE
- [ ] 4.2 Add state transition logging for debugging
- [ ] 4.3 Handle edge cases (timeout, error recovery, cancel)

## 5. Configuration
- [ ] 5.1 Add voice settings to config (wake word sensitivity, VAD threshold, etc.)
- [ ] 5.2 Add voice model selection (whisper model size, TTS voice)
- [ ] 5.3 Add audio device selection

## 6. Testing
- [ ] 6.1 Create `tests/test_voice_manager.py` with unit tests
- [ ] 6.2 Add integration test for full voice loop
- [ ] 6.3 Test wake word false positive/negative rates
- [ ] 6.4 Test VAD accuracy with background noise

## 7. Documentation
- [ ] 7.1 Update `README.md` with voice mode instructions
- [ ] 7.2 Create `docs/VOICE_INTERFACE.md` with detailed guide
- [ ] 7.3 Add troubleshooting section for common audio issues
