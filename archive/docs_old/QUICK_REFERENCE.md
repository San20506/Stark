# JARVIS Voice Assistant - Quick Reference Card

## 🚀 Quick Start (5 Minutes)

### 1. Install Ollama Server
```bash
# Windows: Download from https://ollama.com/download or:
winget install ollama

# macOS:
brew install ollama

# Linux:
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Start Ollama Server
```bash
ollama serve
# Now open another terminal for step 3
```

### 3. Pull LLM Model
```bash
ollama pull phi4-mini
# Or for complex queries: ollama pull llama3.1
```

### 4. Install Python Packages
```bash
pip install -r requirements.txt
```

### 5. Run JARVIS
```bash
python main.py
```

---

## 📋 All GitHub Repositories

| Purpose | Repo | Status |
|---------|------|--------|
| Wake Word | https://github.com/openwakeword/openwakeword | ✅ Active |
| STT | https://github.com/SYSTRAN/faster-whisper | ✅ Active |
| LLM | https://github.com/ollama/ollama | ✅ Active (50k+ stars) |
| TTS (Primary) | https://github.com/OHF-Voice/piper1-gpl | ✅ Active Fork (GPLv3) |
| TTS (Original) | https://github.com/rhasspy/piper | ⚠️ Archived (MIT) |
| TTS (Fallback 1) | https://github.com/nateshmbhat/pyttsx3 | ✅ Active |
| TTS (Fallback 2) | https://github.com/reuben/edge-tts | ✅ Active |
| Audio I/O | https://github.com/bastibe/sounddevice | ✅ Active |
| Numerics | https://github.com/numpy/numpy | ✅ Active (30k+ stars) |

---

## 📦 All Python Packages (pip install)

```bash
# Core Audio
sounddevice>=0.4.6
numpy>=1.24.0

# STT (Ear)
faster-whisper>=1.2.0

# LLM (Brain) - Python client only
ollama>=0.2.0

# TTS (Mouth) - 3-tier fallback
piper-tts>=1.2.0         # Primary (high quality, offline)
pyttsx3>=2.99            # Fallback 1 (cross-platform)
edge-tts>=6.1.0          # Fallback 2 (cloud, best quality)

# Wake Word (Wake Trigger)
openwakeword>=0.7.0

# One-liner install:
pip install sounddevice numpy faster-whisper ollama pyttsx3 edge-tts piper-tts openwakeword
```

---

## 🧠 Model Selection

| Task | Model | Size | Speed | Command |
|------|-------|------|-------|---------|
| **STT** | tiny.en | 1GB | 5-10s/min | Built-in to faster-whisper |
| **LLM (Fast)** | phi4-mini | 2.5GB | 50-100ms | `ollama pull phi4-mini` |
| **LLM (Smart)** | llama3.1 | 4.7GB | 150-250ms | `ollama pull llama3.1` |
| **TTS (Best)** | piper medium | 100-200MB | 100-200ms | Auto-downloaded |
| **Wake Word** | jarvis | 50MB | 10ms | `openwakeword` |

---

## 🎯 Key System Prompts

```python
SYSTEM_PROMPT = (
    "You are Alfred, a dry-witted, highly efficient, and slightly sarcastic British butler AI."
    " You are helpful but brief. You do not fluff your answers. If asked to do something you cannot do,"
    " make a sarcastic remark about your lack of hands."
)
```

---

## ⚙️ Configuration Constants (in main.py)

```python
# Audio Settings
SAMPLE_RATE = 16000           # Whisper preference
CHANNELS = 1                  # Mono
FRAME_DURATION = 0.1          # 100ms chunks
RMS_THRESHOLD = 0.01          # VAD trigger

# Timeouts
SILENCE_TIMEOUT = 1.0         # End utterance after 1s silence
PRE_ROLL_SECONDS = 0.3        # Capture 300ms before speech detected

# Models
WAKEWORD_NAME = "jarvis"
WHISPER_MODEL = "tiny.en"     # English-optimized, fastest
LLM_MODEL = "phi4-mini"       # Recommended for voice (snappy)
# Alternative: "llama3.1"      # Better reasoning, slower

# TTS Fallback Chain
# 1. Piper (offline, high quality, 100-200ms)
# 2. pyttsx3 (offline, cross-platform, 200-500ms)
# 3. edge-tts (cloud, best quality, 500-1000ms + network)
```

---

## 🎤 Barge-In Support

The assistant **immediately stops speaking** if user starts talking:

```python
# How it works:
1. Microphone monitor thread detects speech (RMS amplitude)
2. Sets interrupt_event flag
3. TTS engine.stop() called
4. System returns to listening mode

# User experience:
User: "Jarvis speak something"
Alfred: "As you wish, I shall... [USER INTERRUPTS] Did you say something?"
```

---

## 🔌 Ollama Server Management

```bash
# Start server (terminal 1)
ollama serve

# In separate terminal (terminal 2+):

# List available models
ollama list

# Pull a model
ollama pull phi4-mini      # ~2.5GB
ollama pull llama3.1       # ~4.7GB

# Stop a running model
ollama stop phi4-mini

# Remove model from cache
ollama rm phi4-mini

# Check server health
curl http://localhost:11434/api/tags
```

---

## 🔧 Common Troubleshooting

| Problem | Solution |
|---------|----------|
| "Device Busy" | Kill other audio apps: `taskkill /F /IM zoom.exe` (Windows) or `pkill -f pulseaudio` (Linux) |
| Ollama not found | Run `ollama serve` in separate terminal |
| No models installed | Run `ollama pull phi4-mini` |
| Whisper download fails | Check internet, models auto-download from HuggingFace |
| Piper TTS fails | Install: `pip install piper-tts` |
| pyttsx3 no sound (Linux) | Install: `sudo apt install espeak-ng libespeak1` |
| Microphone not detected | Run: `python -c "import sounddevice as sd; print(sd.query_devices())"` |

---

## 📊 Performance Metrics

| Component | Latency | Memory | Notes |
|-----------|---------|--------|-------|
| Mic Input | 10-20ms | Minimal | Real-time |
| VAD (RMS) | <1ms | Minimal | Per-frame |
| Whisper STT | 5-60s | 1GB | Per utterance |
| Phi4-mini LLM | 50-100ms | 2.5GB | Per token (~5-10 tokens/sec) |
| Piper TTS | 100-200ms | 1GB | Per response |
| **Total E2E** | 6-70s | 4.5GB | Wake → Response → Speak |

---

## 💡 Pro Tips

1. **Fast responses:** Use `phi4-mini` + `tiny.en` + `piper medium`
2. **Better understanding:** Swap to `llama3.1` (slower but smarter)
3. **Best voice quality:** Use `piper-tts`, fallback to `edge-tts` for variety
4. **Reduce latency:** Lower `SILENCE_TIMEOUT` to 0.5s for faster utterance detection
5. **Offline mode:** Skip `edge-tts`, keep only Piper + pyttsx3 fallback
6. **Custom wake word:** Edit `WAKEWORD_NAME = "..."` (openwakeword has pre-trained models)
7. **Multiple voices:** Change Piper voice model in TTS initialization

---

## 📚 Documentation Links

- **Ollama Models Library:** https://ollama.com/library
- **Faster-Whisper Usage:** https://github.com/SYSTRAN/faster-whisper#usage
- **Piper Voices:** https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md
- **Pyttsx3 Docs:** https://pyttsx3.readthedocs.io/
- **Sounddevice Docs:** https://python-sounddevice.readthedocs.io/

---

## ✅ Verification Checklist

```bash
# 1. Check Ollama server running
curl http://localhost:11434/api/tags

# 2. Test microphone
python -c "import sounddevice as sd; print(sd.rec(16000, samplerate=16000).shape)"

# 3. Test STT model
python -c "from faster_whisper import WhisperModel; m = WhisperModel('tiny.en'); print('OK')"

# 4. Test LLM connection
python -c "import ollama; r = ollama.chat(model='phi4-mini', messages=[{'role':'user','content':'hi'}]); print(r['message']['content'])"

# 5. Test TTS
python -c "import pyttsx3; e = pyttsx3.init(); e.say('test'); e.runAndWait()"

# 6. Test wake word
python -c "import openwakeword; m = openwakeword.Model(wakeword='jarvis'); print('OK')"
```

---

## 🎯 Next Steps

1. ✅ Ensure Ollama server running (`ollama serve`)
2. ✅ Pull model (`ollama pull phi4-mini`)
3. ✅ Install Python deps (`pip install -r requirements.txt`)
4. ✅ Run assistant (`python main.py`)
5. 🎤 Say "Jarvis"
6. 💬 Speak command
7. 🎙️ Hear response

---

## 📞 Support

- **Ollama Issues:** https://github.com/ollama/ollama/issues
- **Faster-Whisper Issues:** https://github.com/SYSTRAN/faster-whisper/issues
- **Piper Issues:** https://github.com/OHF-Voice/piper1-gpl/issues
- **Sounddevice Issues:** https://github.com/bastibe/sounddevice/issues

---

**Created:** December 3, 2025  
**Status:** Ready for main.py implementation  
**Next:** Implement voice assistant glue code with all modules
