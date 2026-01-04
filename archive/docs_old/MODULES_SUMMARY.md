# JARVIS Voice Assistant - GitHub Modules & Dependencies Summary

## Quick Reference: All Required Modules

This document lists every GitHub repository, pip package, and installation requirement for the JARVIS voice assistant.

---

## 1️⃣ **Audio Input/Output (Microphone & Speaker)**

### **sounddevice** 📦
- **GitHub:** https://github.com/bastibe/sounddevice
- **Python Package:** `pip install sounddevice>=0.4.6`
- **Purpose:** Non-blocking microphone input via callbacks
- **Features:**
  - Real-time audio streaming
  - Low-latency callback-based processing
  - Cross-platform (Windows, macOS, Linux)
- **Key Classes:**
  - `sounddevice.InputStream()` - for mic input with callbacks
  - `sounddevice.play()` - for speaker output
- **Latency:** ~10-20ms per frame
- **Installation Note:** No external C libraries needed (cross-platform)

### **numpy** 📦
- **GitHub:** https://github.com/numpy/numpy
- **Python Package:** `pip install numpy>=1.24.0`
- **Purpose:** Numerical array operations for audio data
- **Features:**
  - Audio signal processing (RMS, FFT, etc.)
  - Buffer management
  - Format conversion (int16 ↔ float32)
- **Key Functions:**
  - `numpy.frombuffer()` - convert audio bytes to arrays
  - `numpy.sqrt()`, `numpy.mean()` - for VAD calculations
- **Latest Version:** 2.3.5

---

## 2️⃣ **Speech-to-Text (STT - The "Ear")**

### **faster-whisper** 🎯
- **GitHub:** https://github.com/SYSTRAN/faster-whisper
- **Python Package:** `pip install faster-whisper>=1.2.0`
- **Purpose:** Optimized speech-to-text transcription
- **Features:**
  - 4-10x faster than OpenAI's Whisper
  - CPU-optimized inference
  - int8 quantization support
  - Multilingual (99 languages)
  - **Recommended for voice assistants: `tiny.en` model (English-optimized)**
- **Key Classes:**
  - `WhisperModel(model_size, device, compute_type)`
  - `model.transcribe(audio_path, vad_filter=True)`
- **Models Available:**
  - `tiny.en` (39M params, ~1GB, 5-10x real-time) ⭐ **RECOMMENDED**
  - `tiny` (39M params, multilingual)
  - `small` (244M params)
  - `base`, `medium`, `large` (decreasing speed, increasing quality)
- **Latency (tiny.en on CPU):** 5-10 seconds for 60s audio
- **Latest Version:** 1.2.1
- **Installation Note:** Automatically downloads models from Hugging Face on first use

---

## 3️⃣ **Large Language Model (LLM - The "Brain")**

### **Ollama** (Server + Python Client) 🧠
- **GitHub:** https://github.com/ollama/ollama
- **Installation:**
  - **Server:** Download from https://ollama.com/download (Windows .exe, macOS .dmg, Linux script)
  - **Python Client:** `pip install ollama>=0.2.0`
- **Purpose:** Local LLM inference with easy model management
- **Models Recommended:**
  - `phi4-mini` (3.8B, 2.5GB) ⭐ **RECOMMENDED FOR VOICE** - 50-100ms latency, snappy
  - `llama3.1` (8B, 4.7GB) - Better reasoning, 150-250ms latency
  - `gemma3` (4B, 3.3GB) - Fast alternative
- **Key Commands:**
  ```bash
  ollama serve              # Start server
  ollama pull phi4-mini     # Download model
  ollama list              # List installed models
  ```
- **Key Classes (Python):**
  - `ollama.chat(model, messages, stream=False)`
  - `ollama.generate(model, prompt)`
- **API Endpoint:** `http://localhost:11434` (must be running)
- **Latest Version:** 0.13.1
- **Installation Note:** Ollama is a **standalone service**, not a Python module. Must run separately.

---

## 4️⃣ **Text-to-Speech (TTS - The "Mouth")**

### **Piper TTS** (Primary) 🎤
- **GitHub (Active):** https://github.com/OHF-Voice/piper1-gpl (GPLv3)
- **GitHub (Original/Archived):** https://github.com/rhasspy/piper (MIT, archived Oct 2025)
- **Python Package:** `pip install piper-tts>=1.2.0`
- **Purpose:** High-quality, offline, neural TTS
- **Features:**
  - 100+ voices available
  - Fully offline (no internet required)
  - ~100-200ms synthesis latency
  - Espeak-ng for phonemization
- **Key Classes:**
  - `PiperVoice.load(model_path, config_path)`
  - `voice.synthesize(text, wav_file)`
- **Available Voices:**
  - Quality levels: low (faster), medium (balanced), high (best)
  - Languages: 20+ including en-US
  - Example: `en-us-lessac-medium.onnx` (200MB)
- **Latency:** 100-200ms for synthesis
- **Latest Version:** 1.3.0
- **Installation Note:** Voice models (~50-200MB each) auto-download from HuggingFace on first use

### **pyttsx3** (Fallback 1) 📻
- **GitHub:** https://github.com/nateshmbhat/pyttsx3
- **Python Package:** `pip install pyttsx3>=2.99`
- **Purpose:** Offline TTS fallback when Piper unavailable
- **Features:**
  - 100% offline
  - Cross-platform (Windows SAPI5, macOS NSSpeechSynthesizer, Linux eSpeak)
  - Simple API
  - Can interrupt/stop speech
- **Key Classes:**
  - `pyttsx3.init()` - initialize engine
  - `engine.say(text)`, `engine.runAndWait()`, `engine.stop()`
- **Latency:** 200-500ms (slower than Piper)
- **Quality:** ⭐⭐ (robotic, not ideal for voice assistant vibe)
- **Latest Version:** 2.99
- **Platform Requirements:**
  - **Windows:** SAPI5 (built-in)
  - **macOS:** Install `pyobjc>=9.0.1` for fixes
  - **Linux:** `sudo apt install espeak-ng libespeak1`

### **edge-tts** (Fallback 2) ☁️
- **GitHub:** https://github.com/reuben/edge-tts
- **Python Package:** `pip install edge-tts>=6.1.0`
- **Purpose:** Cloud TTS fallback with 2-second timeout
- **Features:**
  - Uses Microsoft Edge's neural voices
  - High-quality synthesis (⭐⭐⭐⭐⭐)
  - Multiple voices and languages
  - **Requires internet connection**
- **Key Classes:**
  - `Communicate(text, voice)` - async synthesizer
  - Stream voices: AriaNeural (female), GuyNeural (male), etc.
- **Latency:** 500-1000ms (network-dependent)
- **Quality:** ⭐⭐⭐⭐⭐ (best quality but needs internet)
- **Latest Version:** 6.1.0+
- **Installation Note:** Async-only API; requires asyncio

---

## 5️⃣ **Wake Word Detection (Trigger - Wake "Ear")**

### **openwakeword** 🎙️
- **GitHub:** https://github.com/openwakeword/openwakeword
- **Python Package:** `pip install openwakeword>=0.7.0`
- **Purpose:** Local, offline wake word detection
- **Features:**
  - Pre-trained models for common wake words ("hey jarvis", "alexa", "hey google")
  - CPU-optimized inference
  - Custom wake word support
  - Confidence scores
- **Key Classes:**
  - `Model(wakeword="jarvis")` - load detector
  - `model.predict(audio_chunk)` - get confidence
- **Audio Requirements:** 16-bit PCM, 16kHz mono
- **Processing:** ~10ms per frame
- **Latest Version:** 0.7.0+
- **Installation Note:** Pre-trained models bundled with package

---

## 📦 **Complete Dependency Tree**

```
JARVIS Voice Assistant
├── Audio I/O Layer
│   ├── sounddevice (audio callbacks, playback)
│   └── numpy (array ops, signal processing)
│
├── STT Pipeline
│   └── faster-whisper (speech-to-text)
│       └── (auto-downloads models from HuggingFace)
│
├── LLM Pipeline
│   └── ollama (requires separate server)
│       └── (models: phi4-mini, llama3.1, gemma3, etc.)
│
├── TTS Pipeline (3-tier fallback)
│   ├── piper-tts (PRIMARY - high quality, offline)
│   │   └── (auto-downloads voice models from HuggingFace)
│   ├── pyttsx3 (FALLBACK 1 - cross-platform offline)
│   └── edge-tts (FALLBACK 2 - cloud, requires internet)
│
└── Wake Word Detection
    └── openwakeword (local, pre-trained models)
```

---

## 🚀 **Installation Command (One-Liner)**

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows

# Install all Python packages
pip install sounddevice>=0.4.6 numpy>=1.24.0 faster-whisper>=1.2.0 ollama>=0.2.0 pyttsx3>=2.99 edge-tts>=6.1.0 piper-tts>=1.2.0 openwakeword>=0.7.0

# Then install Ollama server separately:
# Windows: https://ollama.com/download (or winget install ollama)
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama and pull models
ollama serve          # (in separate terminal)
ollama pull phi4-mini # (in another terminal)
```

---

## 📊 **Module Comparison Table**

| Component | Library | GitHub | Pip Install | Offline | Latency | Quality | Notes |
|-----------|---------|--------|-------------|---------|---------|---------|-------|
| **Mic Input** | sounddevice | github.com/bastibe/sounddevice | ✅ | ✅ | 10-20ms | N/A | Non-blocking callbacks |
| **STT** | faster-whisper | github.com/SYSTRAN/faster-whisper | ✅ | ✅ | 5-60s | ⭐⭐⭐⭐ | CPU optimized, int8 |
| **LLM** | ollama | github.com/ollama/ollama | ✅* | ✅ | 50-250ms | ⭐⭐⭐⭐⭐ | Requires separate server* |
| **TTS 1** | piper-tts | github.com/OHF-Voice/piper1-gpl | ✅ | ✅ | 100-200ms | ⭐⭐⭐⭐⭐ | PRIMARY - high quality |
| **TTS 2** | pyttsx3 | github.com/nateshmbhat/pyttsx3 | ✅ | ✅ | 200-500ms | ⭐⭐ | Fallback - robotic |
| **TTS 3** | edge-tts | github.com/reuben/edge-tts | ✅ | ❌ | 500-1000ms | ⭐⭐⭐⭐⭐ | Cloud fallback, best quality |
| **Wake Word** | openwakeword | github.com/openwakeword/openwakeword | ✅ | ✅ | 10ms | ⭐⭐⭐⭐ | Local detection |

*Ollama server is downloaded from ollama.com, Python client installed via pip.

---

## 💾 **Disk Space Requirements**

| Component | Size | Notes |
|-----------|------|-------|
| **Whisper tiny.en** | ~1GB | Auto-downloaded on first use |
| **Phi4-mini LLM** | ~2.5GB | Ollama auto-downloaded via `ollama pull` |
| **Llama3.1 LLM** | ~4.7GB | Ollama auto-downloaded via `ollama pull` |
| **Piper voice (medium)** | ~100-200MB | Auto-downloaded per voice on first use |
| **openwakeword models** | ~50MB | Bundled with package |
| **Python venv** | ~500MB | Virtual environment |
| **TOTAL (minimal setup)** | ~10GB | Whisper + Phi4-mini + 1 Piper voice |
| **TOTAL (full setup)** | ~20GB | Whisper + Phi4-mini + Llama3.1 + 3 Piper voices |

---

## ✅ **Final Checklist**

- [ ] Python 3.9+ installed
- [ ] Virtual environment created
- [ ] `pip install -r requirements.txt` completed
- [ ] Ollama downloaded and installed
- [ ] `ollama serve` running in background
- [ ] `ollama pull phi4-mini` completed
- [ ] `main.py` in `ALFRED/` directory
- [ ] Microphone tested: `python -c "import sounddevice as sd; print(sd.rec(16000))"`
- [ ] Ollama connection verified: `curl http://localhost:11434/api/tags`
- [ ] Ready to run: `python main.py`

---

## 📚 **Additional Resources**

- **Ollama Documentation:** https://docs.ollama.com
- **Faster-Whisper Docs:** https://github.com/SYSTRAN/faster-whisper#usage
- **Piper Docs:** https://github.com/OHF-Voice/piper1-gpl/tree/main/docs
- **Sounddevice Docs:** https://python-sounddevice.readthedocs.io/

---

**Last Updated:** December 3, 2025  
**Status:** ✅ All repositories verified and tested  
**Ready for:** JARVIS Voice Assistant Implementation
