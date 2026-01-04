# 🤖 ALFRED - Complete Voice Assistant Setup

## ✅ System Setup Complete!

All dependencies have been installed and tested. Alfred is ready to run.

### What's Been Set Up

1. **Virtual Environment**: `d:\ALFRED\.venv` (Python 3.11.8)
2. **Dependencies Installed**:
   - ✅ sounddevice (audio I/O)
   - ✅ numpy (signal processing)
   - ✅ faster-whisper (speech-to-text)
   - ✅ ollama (LLM client)
   - ✅ pyttsx3 (text-to-speech fallback)
   - ✅ edge-tts (cloud TTS fallback)
   - ✅ openwakeword (wake word detection)

3. **Ollama Models**:
   - ✅ **llama3.2:3b** (currently configured - 2GB, fits on any system)
   - phi4-mini, llama3:8b, mistral:7b, deepseek-coder, and others available

4. **Main Files**:
   - **main.py** (2,100+ lines) - Complete voice assistant with barge-in support
   - **test_setup.py** - System verification script
   - **run_alfred.bat** - Windows startup batch file

---

## 🎤 How to Run Alfred

### Option 1: Command Line (Recommended for Testing)

Open **two terminals**:

**Terminal 1** - Start Ollama Server:
```powershell
ollama serve
```

**Terminal 2** - Run Alfred:
```powershell
cd d:\ALFRED
.\.venv\Scripts\python.exe main.py
```

You should see:
```
======================================================================
🤖 ALFRED Voice Assistant Starting...
======================================================================
✅ Audio input stream started.
🧠 Processor loop started.
🎤 Listening for 'ALFRED'...
(Press Ctrl+C to exit)
```

### Option 2: Batch File (Easy Click & Run)

1. Open `d:\ALFRED\run_alfred.bat`
2. Make sure `ollama serve` is already running in another terminal
3. Alfred will start listening

---

## 🎯 Usage

Once Alfred is running:

1. **Say "ALFRED"** to wake up (or just start speaking)
2. **Ask a question** like:
   - "What time is it?"
   - "How many days until Christmas?"
   - "Tell me a joke"
   - "Open google.com" (opens browser)
   - "Search for Python documentation"

3. **Interrupt** by speaking again (barge-in)
4. **Exit** by pressing Ctrl+C

---

## 📊 Current Configuration

```python
# Wake Word
WAKEWORD_NAME = "alfred"          # Say "ALFRED" to activate

# STT Model
WHISPER_MODEL = "tiny.en"         # ~1GB, 5-10s per minute of audio

# LLM Model  
LLM_MODEL = "llama3.2:3b"         # 2GB, fast responses (~1-2s)
                                   # Alt: "phi4-mini" (needs 18GB RAM)

# System Personality
SYSTEM_PROMPT = "You are Alfred, a dry-witted, highly efficient, and 
                 slightly sarcastic British butler AI..."

# Audio Settings
SAMPLE_RATE = 16000               # Hz (Whisper standard)
RMS_THRESHOLD = 0.01              # VAD sensitivity (lower = more sensitive)
SILENCE_TIMEOUT = 1.0             # Seconds to wait after speech ends
```

---

## ⚙️ Tuning VAD (Voice Activity Detection)

If Alfred isn't picking up your voice:

**Lower `RMS_THRESHOLD`** (e.g., 0.005):
- More sensitive, picks up quieter voices
- May detect background noise

**Raise `RMS_THRESHOLD`** (e.g., 0.02):
- Less sensitive, requires louder voices
- Less false triggers

Edit `main.py` line ~83:
```python
RMS_THRESHOLD = 0.01  # Adjust this value
```

---

## 🔄 Changing LLM Models

To use a different model (faster or better quality):

1. **Install model** (one-time):
   ```powershell
   ollama pull phi4-mini      # Higher quality (18GB RAM needed)
   ollama pull llama3:8b      # Medium quality
   ollama pull mistral:7b     # Good balance
   ```

2. **Update `main.py`** line ~84:
   ```python
   LLM_MODEL = "llama3:8b"    # Change this
   ```

3. **Restart Alfred**

---

## 📋 Troubleshooting

### Problem: "No audio input"
- Check microphone in Windows Settings
- Verify `SAMPLE_RATE = 16000` matches your mic
- Try adjusting `RMS_THRESHOLD`

### Problem: "Whisper model not loading"
- First run downloads ~1GB from Hugging Face (check internet)
- Check disk space

### Problem: "Ollama connection failed"
- Make sure `ollama serve` is running in another terminal
- Check Ollama is listening on `http://127.0.0.1:11434`

### Problem: "Memory error with LLM"
- Switch to smaller model: `LLM_MODEL = "llama3.2:3b"`
- Close other applications
- Check available RAM

### Problem: "Piper TTS not available"
- Install: `pip install piper-tts`
- Requires: `pip install onnxruntime`

---

## 🛠️ System Requirements

**Minimum**:
- Windows 10+
- Python 3.9+
- 2GB RAM
- 5GB free disk (for models)
- Microphone + Speakers

**Recommended**:
- Windows 11
- Python 3.10+
- 8GB+ RAM
- 10GB free disk
- USB microphone (better quality)

---

## 📚 Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│         Microphone (Audio Input)                     │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │  sounddevice        │  Real-time audio callbacks
         └──────────┬──────────┘
                    │
                    ▼
    ┌────────────────────────────────┐
    │  Alfred Processor Loop          │  Main event loop
    │  - Voice Activity Detection     │  - RMS amplitude VAD
    │  - Wake Word Detection          │  - Ring buffer (pre-roll)
    │  - Silence timeout              │  - 1s silence = end utterance
    └───┬────────────────┬────────────┘
        │                │
        ▼                ▼
    ┌─────────────┐  ┌──────────────────┐
    │  Whisper    │  │  Openwakeword    │
    │  (STT)      │  │  (Wake Detection)│
    └──────┬──────┘  └──────────────────┘
           │
           ▼
    ┌─────────────────────┐
    │  Ollama (LLM)       │  llama3.2:3b / phi4-mini
    │  Local Inference    │  Alfred personality prompt
    └──────────┬──────────┘
               │
               ▼
    ┌──────────────────────────────┐
    │  TTS (Text-to-Speech)        │  Fallback chain:
    │  1. pyttsx3 (primary)        │  - offline, cross-platform
    │  2. edge-tts (cloud)         │  - cloud, high quality
    └──────────┬───────────────────┘
               │
               ▼
         ┌──────────────┐
         │  Speakers    │  Audio output
         └──────────────┘
```

---

## 🎓 Learning Resources

- **Whisper (STT)**: https://github.com/openai/whisper
- **Ollama (LLM)**: https://github.com/ollama/ollama
- **pyttsx3 (TTS)**: https://github.com/nateshmbhat/pyttsx3
- **openwakeword (Wake)**: https://github.com/dscripka/openWakeWord

---

## 📝 Notes

- **First run** may take 30-60s (downloading models)
- **STT** accuracy improves with clear speech
- **LLM responses** vary (set `SYSTEM_PROMPT` to adjust personality)
- **Barge-in** (interruption) works via threading + shared `stop_event`
- **Command execution**: Use `<cmd>browser</cmd> <url>google.com</url>` tags (future expansion)

---

## 🚀 Next Steps

1. ✅ Run Alfred and test voice commands
2. Adjust VAD threshold if needed
3. Try different LLM models
4. Add custom commands or integrations
5. Build a GUI (optional)

---

**Enjoy your personal AI butler! 🎩**
