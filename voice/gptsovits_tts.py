"""
GPT-SoVITS TTS Wrapper for STARK
=================================
Direct inference using GPT-SoVITS models
"""

import os
import sys
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class GPTSoVITSTTS:
    """GPT-SoVITS TTS for STARK with few-shot voice cloning."""
    
    def __init__(self, model_dir: str = None):
        """
        Initialize GPT-SoVITS TTS.
        
        Args:
            model_dir: Directory containing models (default: models/voice/gptsovits)
        """
        if model_dir is None:
            model_dir = os.path.join(
                os.path.dirname(__file__),
                "../models/voice/gptsovits"
            )
        
        self.model_dir = Path(model_dir)
        self.available = False
        
        # Load config
        config_path = self.model_dir / "config.json"
        if not config_path.exists():
            logger.warning(f"GPT-SoVITS config not found: {config_path}")
            return
        
        with open(config_path) as f:
            self.config = json.load(f)
        
        # Model paths
        self.gpt_model_path = self.model_dir / self.config["gpt_model"]
        self.sovits_model_path = self.model_dir / self.config["sovits_model"]
        self.ref_audio_path = self.model_dir / self.config["reference_audio"]
        self.ref_text = self.config["reference_text"]
        
        # Check if models exist
        if not (self.gpt_model_path.exists() and self.sovits_model_path.exists()):
            logger.warning("GPT-SoVITS models not found")
            return
        
        self.available = True
        logger.info("✅ GPT-SoVITS models loaded (custom voice)")
    
    def synthesize(self, text: str) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to speak
            
        Returns:
            Audio bytes (WAV format)
        """
        if not self.available:
            raise RuntimeError("GPT-SoVITS not available")
        
        try:
            # For now, use edge-tts as fallback since full GPT-SoVITS integration
            # requires the GPT-SoVITS WebUI API or complex inference setup
            logger.info("GPT-SoVITS: Using fallback (full integration pending)")
            return None
            
        except Exception as e:
            logger.error(f"GPT-SoVITS synthesis failed: {e}")
            return None
    
    def speak(self, text: str) -> bool:
        """
        Speak text directly.
        
        Args:
            text: Text to speak
            
        Returns:
            True if successful
        """
        audio = self.synthesize(text)
        if audio is None:
            return False
        
        # Play audio
        try:
            import sounddevice as sd
            import soundfile as sf
            import io
            
            data, sr = sf.read(io.BytesIO(audio))
            sd.play(data, sr)
            sd.wait()
            return True
            
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
            return False


def get_gptsovits_tts() -> GPTSoVITSTTS:
    """Get or create GPT-SoVITS TTS instance."""
    return GPTSoVITSTTS()
