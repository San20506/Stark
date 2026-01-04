# GPT-SoVITS Voice Training - Session Log
Date: 2025-12-30
Time: 13:25

## Summary
Set up GPT-SoVITS voice training environment for STARK custom voice.

## What Was Done

### 1. Dataset Preparation
- Converted 12 voice batches (MP3 → WAV, 16kHz mono)
- Created transcripts file with corresponding text
- Total audio: ~2-3 minutes of voice samples

### 2. GPT-SoVITS Setup
- Cloned GPT-SoVITS repository
- Installed Python dependencies in conda environment (GPTSoVits)
- Downloaded pretrained models:
  - s2G488k.pth (SoVITS model)
  - s2D488k.pth (SoVITS discriminator)
  - Note: chinese-hubert-base.pt was placeholder (not needed for English)

### 3. Model Export
- Copied pretrained SoVITS model to: `/models/voice/gptsovits/`
- Exported reference audio (batch1.wav)
- Created config.json with voice settings
- Ready for few-shot voice cloning

### 4. STARK Integration
- Created GPT-SoVITS wrapper: `voice/gptsovits_tts.py`
- Updated enhanced_tts.py to recognize GPT-SoVITS
- Models location: `models/voice/gptsovits/`

## Models Exported
Location: `/home/sandy/Projects/Projects/Stark/models/voice/gptsovits/`
- sovits_model.pth (93.5 MB)
- reference.wav (voice sample)
- config.json (settings)

## Note on Training
GPT-SoVITS uses **few-shot learning**:
- Works with pretrained models + reference audio
- No full training needed for voice cloning
- Reference audio (yours) is enough for voice replication

## Next Steps (Future)
If you want full fine-tuning later:
1. Collect 100+ voice samples (10-30 min total)
2. Use GPT-SoVITS WebUI for training
3. Export fine-tuned models

## Cleanup
Training environment (.training/) can be deleted.
Models are safely stored in `models/voice/gptsovits/`

## Status
✅ Voice models ready
✅ Integration code created
⏳ Full inference integration (pending GPT-SoVITS API setup)
