# Change: Quarantine Voice (S5)

## Why
Voice wake-word, GPT-SoVITS, and enhanced TTS are PRD §9 out-of-scope and pull
`requirements-voice.txt` weight. Only STT/TTS interfaces stay.

## What Changes
- Delete `voice/wake_word.py`, `enhanced_tts.py`, `gptsovits_tts.py`
- Trim `core/main.py:932-1113` voice block (header at 932-934 through `1113: Voice mode ended`)
- Keep `speech_to_text`/`text_to_speech` interfaces only

## Impact
- Affected specs: refactor-s5-voice (new)
- Affected code: `voice/` (3 files), `core/main.py:932-1113` ONLY
- Must not touch: `1115-1253` MCP, `1259-1326` media, `1328-1364` singleton
- Pre-condition: executor confirms `sed -n '1113,1117p'` shows `Voice mode ended` → blank → `MCP INTEGRATION` before deleting
