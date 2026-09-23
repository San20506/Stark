## 1. Confirm Boundary
- [x] 1.1 `sed -n '1113,1117p' core/main.py` shows `Voice mode ended` → blank → `MCP INTEGRATION`; stop if not

## 2. Trim Voice
- [x] 2.1 Delete `voice/wake_word.py`, `voice/enhanced_tts.py`, `voice/gptsovits_tts.py` (quarantined to `archive/quarantined/voice/` via `git mv`, not deleted)
- [x] 2.2 Trim `core/main.py:932-1113` to STT/TTS interfaces only

## 3. Verify
- [x] 3.1 CLI path has zero wake-word/GPT-SoVITS imports
- [x] 3.2 `requirements-voice.txt` unneeded for `pytest`
