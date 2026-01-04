"""
Audio Processing Module for ALFRED
Provides enhanced VAD and noise reduction capabilities.
"""

import torch
import numpy as np
import logging
from typing import Optional, Tuple
import noisereduce as nr

logger = logging.getLogger("Alfred.AudioProcessor")

# ============================================================================
# SILERO VAD - Neural Network Voice Activity Detection
# ============================================================================

class SileroVADProcessor:
    """
    Silero VAD - Neural network-based voice activity detection.
    Superior to RMS amplitude detection in noisy environments.
    """
    
    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5):
        """
        Initialize Silero VAD model.
        
        Args:
            sample_rate: Audio sample rate (8000 or 16000)
            threshold: Probability threshold for speech detection (0-1)
        """
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.model = None
        self.utils = None
        
        try:
            # Load pre-trained model
            self.model, self.utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            
            # Extract utilities
            (self.get_speech_timestamps,
             self.save_audio,
             self.read_audio,
             self.VADIterator,
             self.collect_chunks) = self.utils
            
            logger.info(f"✅ Silero VAD initialized (sr={sample_rate}Hz, threshold={threshold})")
            
        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}")
            self.model = None
    
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Detect if audio chunk contains speech.
        
        Args:
            audio_chunk: int16 PCM audio array
            
        Returns:
            True if speech detected, False otherwise
        """
        if self.model is None:
            # Fallback to simple amplitude check
            rms = np.sqrt(np.mean(np.square(audio_chunk.astype(float) / 32768.0)))
            return rms > 0.01
        
        try:
            # Convert int16 to float32 [-1, 1]
            audio_float = audio_chunk.astype(np.float32) / 32768.0
            
            # Silero VAD requires exactly 512 samples for 16kHz
            # If we have more, process in chunks and return True if ANY chunk has speech
            chunk_size = 512
            speech_detections = []
            
            for i in range(0, len(audio_float), chunk_size):
                chunk = audio_float[i:i+chunk_size]
                
                # Skip if chunk is too small
                if len(chunk) < chunk_size:
                    # Pad with zeros if needed
                    chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')
                
                # Convert to torch tensor
                audio_tensor = torch.from_numpy(chunk)
                
                # Get speech probability
                speech_prob = self.model(audio_tensor, self.sample_rate).item()
                speech_detections.append(speech_prob >= self.threshold)
            
            # Return True if ANY chunk detected speech
            return any(speech_detections) if speech_detections else False
            
        except Exception as e:
            logger.debug(f"VAD error: {e}")
            return False
    
    def get_speech_timestamps_from_audio(self, audio: np.ndarray) -> list:
        """
        Get precise timestamps of speech segments in audio.
        
        Args:
            audio: int16 PCM audio array
            
        Returns:
            List of dicts with 'start' and 'end' timestamps (in samples)
        """
        if self.model is None:
            return []
        
        try:
            # Convert to float32
            audio_float = audio.astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_float)
            
            # Get timestamps
            timestamps = self.get_speech_timestamps(
                audio_tensor,
                self.model,
                sampling_rate=self.sample_rate,
                threshold=self.threshold
            )
            
            return timestamps
            
        except Exception as e:
            logger.error(f"Timestamp extraction error: {e}")
            return []


# ============================================================================
# NOISE REDUCTION
# ============================================================================

class NoiseReducer:
    """
    Spectral gating noise reduction for cleaner audio.
    """
    
    def __init__(self, sample_rate: int = 16000):
        """
        Initialize noise reducer.
        
        Args:
            sample_rate: Audio sample rate
        """
        self.sample_rate = sample_rate
        logger.info(f"✅ Noise reducer initialized (sr={sample_rate}Hz)")
    
    def reduce_noise(self, audio: np.ndarray, noise_profile: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Apply noise reduction to audio.
        
        Args:
            audio: int16 PCM audio array
            noise_profile: Optional noise sample for profiling (first 0.5s recommended)
            
        Returns:
            Cleaned audio as int16 array
        """
        try:
            # Convert to float32
            audio_float = audio.astype(np.float32) / 32768.0
            
            # Apply noise reduction
            if noise_profile is not None:
                noise_float = noise_profile.astype(np.float32) / 32768.0
                reduced = nr.reduce_noise(
                    y=audio_float,
                    sr=self.sample_rate,
                    y_noise=noise_float,
                    stationary=True
                )
            else:
                # Stationary noise reduction (assumes first 0.5s is noise)
                reduced = nr.reduce_noise(
                    y=audio_float,
                    sr=self.sample_rate,
                    stationary=True
                )
            
            # Convert back to int16
            reduced_int16 = (reduced * 32768.0).astype(np.int16)
            
            return reduced_int16
            
        except Exception as e:
            logger.warning(f"Noise reduction failed: {e}")
            return audio  # Return original on failure


# ============================================================================
# COMBINED AUDIO PREPROCESSOR
# ============================================================================

class AudioPreprocessor:
    """
    Combines VAD and noise reduction for optimal speech recognition.
    """
    
    def __init__(self, sample_rate: int = 16000, vad_threshold: float = 0.5, enable_noise_reduction: bool = True):
        """
        Initialize audio preprocessor.
        
        Args:
            sample_rate: Audio sample rate
            vad_threshold: Silero VAD threshold
            enable_noise_reduction: Whether to apply noise reduction
        """
        self.sample_rate = sample_rate
        self.vad = SileroVADProcessor(sample_rate=sample_rate, threshold=vad_threshold)
        self.noise_reducer = NoiseReducer(sample_rate=sample_rate) if enable_noise_reduction else None
        
        logger.info(f"✅ AudioPreprocessor initialized (VAD + {'NoiseReduction' if enable_noise_reduction else 'No NoiseReduction'})")
    
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """Detect speech in audio chunk."""
        return self.vad.is_speech(audio_chunk)
    
    def preprocess(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply full preprocessing pipeline.
        
        Args:
            audio: int16 PCM audio array
            
        Returns:
            Cleaned audio as int16 array
        """
        if self.noise_reducer is not None:
            return self.noise_reducer.reduce_noise(audio)
        return audio
