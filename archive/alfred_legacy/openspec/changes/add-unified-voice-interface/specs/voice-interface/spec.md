## ADDED Requirements

### Requirement: Wake Word Detection
The system SHALL detect a configurable wake word (default: "ALFRED" or "Hey ALFRED") to activate voice listening mode.

#### Scenario: Wake word detected
- **WHEN** the user says "Hey ALFRED" or "ALFRED"
- **THEN** the system transitions to LISTENING state
- **AND** plays an acknowledgment sound or visual indicator

#### Scenario: Wake word not detected
- **WHEN** ambient speech does not contain the wake word
- **THEN** the system remains in IDLE state
- **AND** no processing occurs

#### Scenario: Low confidence wake word
- **WHEN** wake word is detected with confidence below threshold
- **THEN** the system MAY request confirmation before proceeding

---

### Requirement: Voice Activity Detection
The system SHALL automatically detect when the user starts and stops speaking, eliminating the need for push-to-talk.

#### Scenario: Speech start detected
- **WHEN** the user begins speaking after wake word activation
- **THEN** the system begins recording audio
- **AND** provides visual feedback that recording is active

#### Scenario: Speech end detected
- **WHEN** silence is detected for more than 1.5 seconds after speech
- **THEN** the system stops recording
- **AND** proceeds to transcription

#### Scenario: Timeout without speech
- **WHEN** no speech is detected within 10 seconds of wake word
- **THEN** the system returns to IDLE state
- **AND** optionally announces "I didn't hear anything"

---

### Requirement: Speech-to-Text Transcription
The system SHALL transcribe spoken audio to text using local Whisper model with streaming capability.

#### Scenario: Successful transcription
- **WHEN** audio is captured and processed
- **THEN** the transcribed text is passed to the cognitive engine
- **AND** the original query is displayed/logged

#### Scenario: Low confidence transcription
- **WHEN** transcription confidence is below 70%
- **THEN** the system SHALL display the uncertain text
- **AND** MAY ask "Did you say [transcription]?"

#### Scenario: No speech detected
- **WHEN** audio contains no recognizable speech
- **THEN** the system announces "I didn't catch that"
- **AND** returns to LISTENING or IDLE state

---

### Requirement: Text-to-Speech Output
The system SHALL convert response text to natural-sounding speech using neural TTS with fallback options.

#### Scenario: Neural TTS available
- **WHEN** piper-tts is installed and functional
- **THEN** responses are spoken using neural TTS
- **AND** voice sounds natural and clear

#### Scenario: Neural TTS unavailable
- **WHEN** piper-tts is not available
- **THEN** the system falls back to pyttsx3
- **AND** logs a warning about degraded quality

#### Scenario: Long response handling
- **WHEN** response exceeds 500 characters
- **THEN** the system MAY summarize for speech
- **AND** offers "Would you like me to continue?"

---

### Requirement: Interrupt Handling
The system SHALL allow users to interrupt TTS output by speaking or pressing a key.

#### Scenario: Voice interrupt
- **WHEN** wake word is detected during TTS playback
- **THEN** TTS stops immediately
- **AND** system transitions to LISTENING state

#### Scenario: Key interrupt
- **WHEN** user presses SPACE or ENTER during TTS
- **THEN** TTS stops immediately
- **AND** system awaits next input

---

### Requirement: Voice State Machine
The system SHALL maintain a clear state machine for voice interaction with defined transitions.

#### Scenario: Normal conversation flow
- **WHEN** system is in IDLE state and wake word detected
- **THEN** transitions: IDLE → LISTENING → PROCESSING → SPEAKING → IDLE

#### Scenario: Error recovery
- **WHEN** any error occurs during voice processing
- **THEN** system logs error, announces generic error message
- **AND** returns to IDLE state

#### Scenario: Continuous conversation
- **WHEN** user says "continue" or follows up immediately after response
- **THEN** system remains in LISTENING state
- **AND** maintains conversation context

---

### Requirement: Audio Device Management
The system SHALL properly manage audio input/output devices with clear error handling.

#### Scenario: Default device selection
- **WHEN** no device is specified
- **THEN** system uses default system input/output devices

#### Scenario: Device unavailable
- **WHEN** configured audio device is not available
- **THEN** system falls back to default device
- **AND** logs warning with device information

#### Scenario: Device conflict
- **WHEN** audio device is in use by another application
- **THEN** system displays clear error message
- **AND** suggests closing conflicting application
