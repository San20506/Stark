# JARVIS Voice Assistant - Complete Setup Guide

## Prerequisites
- **Python 3.9+** (3.12+ recommended)
- **Windows 10+**, **macOS 10.14+**, or **Linux** (Ubuntu 20.04+)
- **Ollama Server** (installed separately, not via pip)
- **Minimum 8GB RAM** (16GB recommended for Phi4-mini + Whisper)

---

## Installation Steps

### 1. Install Ollama Server (Local LLM Inference)

Ollama is a **separate application** (not a Python package) that runs as a background service.

#### Windows
```powershell
# Download installer from https://ollama.com/download
# Or use Windows Package Manager:
winget install ollama
```

#### macOS
```bash
# Download .dmg from https://ollama.com/download
# Or use Homebrew:
brew install ollama
```

#### Linux
```bash
# Official install script
curl -fsSL https://ollama.com/install.sh | sh

# Or manual: https://docs.ollama.com/linux#manual-install
```

#### Start Ollama Server
```bash
# Windows (PowerShell)
ollama serve

# macOS / Linux
ollama serve

# Or as background service (typically automatic on macOS/Windows)
```

**Verify Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

---

### 2. Pull Required LLM Models

Run these commands in a **separate terminal** while Ollama server is running:

```bash
# Option A: Phi4-mini (3.8B) - RECOMMENDED for voice assistants
# Fastest, snappiest, best for real-time responses
ollama pull phi4-mini

# Option B: Llama 3.1 8B - for complex queries (requires 16GB+ RAM)
ollama pull llama3.1

# Verify models are installed
ollama list
```

**Model Selection Guide:**
| Model | Size | Speed | Quality | RAM | Best For |
|-------|------|-------|---------|-----|----------|
| **phi4-mini** | 2.5GB | 🟢 Fast (50-100ms) | ⭐⭐⭐⭐ | 4GB | Voice Commands (Recommended) |
| **llama3.1** | 4.7GB | 🟡 Medium (150-250ms) | ⭐⭐⭐⭐⭐ | 8GB | Complex Reasoning |

---

### 3. Install Python Dependencies

```bash
# Clone or create project directory
mkdir ALFRED && cd ALFRED

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Windows CMD:
venv\Scripts\activate

# macOS / Linux:
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Verify installation
python -c "import ollama, faster_whisper, numpy, sounddevice, pyttsx3, edge_tts, openwakeword; print('All dependencies OK')"
```

---

### 4. System-Specific Setup

#### Windows
```powershell
# Ensure PowerShell ExecutionPolicy allows scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# For pyttsx3 (already includes SAPI5)
# No additional setup needed
```

#### macOS
```bash
# For pyttsx3 (uses NSSpeechSynthesizer)
pip install --upgrade pyobjc>=9.0.1

# For Piper TTS (optional, high-quality)
# Already included via pip install piper-tts
```

#### Linux (Ubuntu/Debian)
```bash
# For pyttsx3 audio synthesis
sudo apt update
sudo apt install espeak-ng libespeak1

# For sounddevice (PulseAudio/ALSA)
sudo apt install libportaudio2 libportaudiocpp0

# Verify audio device
arecord -l  # List available recording devices
```

---

## Verification Checklist

### 1. Test Ollama Connection
```python
import ollama

response = ollama.chat(
    model='phi4-mini',
    messages=[{'role': 'user', 'content': 'Hello, are you Alfred?'}],
    stream=False
)
print(response['message']['content'])
```

### 2. Test Audio Input
```python
import sounddevice as sd
import numpy as np

print("Recording 3 seconds...")
audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype='float32')
sd.wait()
print(f"Recorded {audio.shape[0]} samples")
```

### 3. Test Whisper STT
```python
from faster_whisper import WhisperModel

model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
segments, info = model.transcribe("test_audio.mp3")
print(f"Language: {info.language}")
for seg in segments:
    print(f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}")
```

### 4. Test TTS (Piper Primary, fallback to pyttsx3)
```python
import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.say("Hello, I am Alfred, your voice assistant")
engine.runAndWait()
```

### 5. Test Wake Word Detection
```python
import openwakeword

model = openwakeword.Model(wakeword="jarvis")
# Feed audio frames (16-bit PCM, 16kHz)
prediction = model.predict(audio_chunk)
print(f"Wake word confidence: {prediction}")
```

---

## Running the Main Assistant

```bash
# Ensure Ollama server is running in background
ollama serve  # (in separate terminal)

# Run the voice assistant
python main.py
```

**Expected output:**
```
2025-12-03 10:15:32 [INFO] Starting Jarvis assistant.
2025-12-03 10:15:33 [INFO] Audio input stream started.
2025-12-03 10:15:33 [INFO] Processor loop started.
2025-12-03 10:15:34 [INFO] Listening for wake word...
```

---

## Troubleshooting

### Audio Device Busy
If you get "Device Busy" error:
```bash
# Windows: Check if another app uses microphone
tasklist | findstr "audio|recorder|zoom"

# Linux: Kill conflicting PulseAudio/ALSA processes
sudo pkill -f pulseaudio

# macOS: Restart CoreAudio
sudo killall -9 coreaudiod
```

### Ollama Connection Failed
```python
# Check if Ollama server is running
curl http://localhost:11434/api/tags

# If not, start it:
ollama serve
```

### Whisper Model Not Found
```bash
# Download model manually
python -c "from faster_whisper import WhisperModel; WhisperModel('tiny.en')"

# Or ensure disk space (models ~1GB each)
du -sh ~/.cache/huggingface/
```

### No Audio Input
```bash
# Test default audio device
python -c "import sounddevice as sd; print(sd.default_device)"

# Change device in main.py (around line ~200):
# self.listener_stream = sd.InputStream(device=0, ...)  # device ID from above
```

### Piper TTS Not Working
```bash
# Install piper models
pip install piper-tts

# Download voice model (100MB)
python -c "from piper.voice import PiperVoice; PiperVoice.load('en-us-lessac-medium.onnx')"
```

---

## Performance Tuning

### For Low-Latency Voice Assistants
```python
# In main.py, adjust these constants:

# 1. Use faster STT model
WHISPER_MODEL = "tiny.en"  # or "tiny" for multilingual

# 2. Use fastest LLM model
LLM_MODEL = "phi4-mini"  # instead of llama3.1

# 3. Reduce silence timeout for faster utterance detection
SILENCE_TIMEOUT = 0.8  # seconds (default 1.0)

# 4. Use int8 quantization
# In main.py: compute_type="int8" for Whisper
```

### For Better Accuracy
```python
# Use larger models (requires more RAM/time)
WHISPER_MODEL = "small"  # or "base"
LLM_MODEL = "llama3.1"   # 8B model with better reasoning
```

---

## Project Structure

```
ALFRED/
├── main.py                 # Main JARVIS voice assistant glue
├── requirements.txt        # Python dependencies (this file)
└── SETUP_GUIDE.md         # Installation instructions (this file)

# After setup, you'll also have:
├── venv/                  # Python virtual environment
└── .cache/                # Model caches (Whisper, Piper voices)
```

---

## Key Repositories Used

| Component | Repo | GitHub |
|-----------|------|--------|
| **Wake Word** | openwakeword | https://github.com/openwakeword/openwakeword |
| **STT** | faster-whisper | https://github.com/SYSTRAN/faster-whisper |
| **LLM** | Ollama | https://github.com/ollama/ollama |
| **TTS (Primary)** | Piper | https://github.com/OHF-Voice/piper1-gpl |
| **TTS (Fallback)** | pyttsx3 | https://github.com/nateshmbhat/pyttsx3 |
| **TTS (Fallback 2)** | edge-tts | https://github.com/reuben/edge-tts |
| **Audio I/O** | sounddevice | https://github.com/bastibe/sounddevice |

---

## System Requirements Summary

| Requirement | Minimum | Recommended |
|------------|---------|-------------|
| **CPU** | Dual-core | Quad-core (i7/Ryzen5) |
| **RAM** | 8GB | 16GB |
| **Disk** | 10GB | 20GB (for models + OS) |
| **Internet** | Not required (all local) | For downloading models first-time |
| **Microphone** | USB mic OK | 3.5mm / Built-in |
| **Speaker** | Any | Quality matters for TTS |

---

## Next Steps

1. ✅ Complete this setup guide
2. ✅ Start `ollama serve` in background
3. ✅ Run `python main.py`
4. 🎤 Say "Jarvis" (or configured wake word)
5. 💬 Speak your command
6. 🎙️ Listen to Alfred's response

---

## Support & Debugging

For issues, check:
1. **Ollama running?** → `curl http://localhost:11434/api/tags`
2. **Microphone working?** → `python -c "import sounddevice as sd; print(sd.rec(16000))"`
3. **Models installed?** → `ollama list`
4. **Python packages OK?** → `pip list | grep -E "ollama|faster-whisper|piper"`

Good luck with your JARVIS assistant! 🚀
