# STARK Voice Setup Guide

## TTS Engine Priorities

STARK now uses a **3-tier TTS system** for optimal voice quality:

1. **ElevenLabs** (Best - Natural, smooth, premium)
2. **edge-tts** (Good - Cloud-based, free)
3. **pyttsx3** (Fallback - Offline, robotic)

---

## Option 1: ElevenLabs (Recommended) 🎤

**Best voice quality** - Natural, smooth, no breaking

### Setup:

1. Get your API key from ElevenLabs:
   - Go to https://elevenlabs.io
   - Sign up (free tier: 10,000 characters/month)
   - Get your API key from settings

2. Set the environment variable:
   ```bash
   export ELEVENLABS_API_KEY="your_api_key_here"
   ```

3. Install the package:
   ```bash
   pip install elevenlabs sounddevice soundfile
   ```

4. Run STARK:
   ```bash
   python3 run_voice.py --query "Test the new voice"
   ```

### Permanent Setup:

Add to your `~/.bashrc` or `~/.zshrc`:
```bash
export ELEVENLABS_API_KEY="sk_..."
```

---

## Option 2: edge-tts (Free, Good Quality) 🌐

**Cloud-based, no API key needed**

### Setup:

```bash
pip install edge-tts sounddevice soundfile
```

This will be used automatically if ElevenLabs isn't configured.

Voice: `en-GB-RyanNeural` (British male, similar to JARVIS)

---

## Option 3: pyttsx3 (Offline Fallback) 💻

Already installed - works offline but sounds robotic.

---

## Voice Selection

**Current voice:** Adam (British male, natural)
- Voice ID: `pNInz6obpgDQGcFmaJgB`

**Other ElevenLabs voices:**
- `21m00Tcm4TlvDq8ikWAM` - Rachel (neutral, clear)
- `AZnzlk1XvdvUeBnXmlld` - Domi (confident, assertive)
- `EXAVITQu4vr4xnSDxMaL` - Bella (soft, calm)

To change voice, edit `/home/sandy/Projects/Projects/Stark/voice/enhanced_tts.py`:
```python
self.voice_id = "21m00Tcm4TlvDq8ikWAM"  # Change this
```

---

## Testing

### Test with single query:
```bash
python3 run_voice.py --query "Hello, I am STARK with enhanced voice quality"
```

### Test interactive mode:
```bash
python3 run_voice.py --text
```

---

## Troubleshooting

### Issue: Voice still robotic

**Check logs:**
Look for "✅ ElevenLabs available" in the startup logs.

If you see "✅ pyttsx3 available" only, then:
1. Verify `ELEVENLABS_API_KEY` is set: `echo $ELEVENLABS_API_KEY`
2. Install elevenlabs: `pip install elevenlabs`

### Issue: API quota exceeded

ElevenLabs free tier: 10,000 chars/month

**Fallback:** edge-tts will be used automatically (still good quality)

---

## Cost Estimate

**ElevenLabs Free Tier:**
- 10,000 characters/month
- ~200 responses (assuming 50 chars each)
- Sufficient for testing

**Paid Plans:**
- Starter: $5/month, 30,000 chars
- Creator: $22/month, 100,000 chars

---

**Recommendation:** Start with edge-tts (free, good), upgrade to ElevenLabs if you want premium quality.
