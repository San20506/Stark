## ADDED Requirements

### Requirement: Minimal Voice Surface
The system SHALL expose only STT/TTS interfaces, with wake-word, enhanced TTS,
and GPT-SoVITS removed and no references past `core/main.py:1113`.

#### Scenario: Voice block ends at boundary
- **WHEN** the voice section is inspected
- **THEN** it ends at `1113: Voice mode ended` and MCP begins at `1115+`

#### Scenario: CLI free of voice engines
- **WHEN** the CLI loads
- **THEN** no wake-word or GPT-SoVITS import executes
