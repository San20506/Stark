"""
STARK Base Model
================
Load and manage the base language model (Qwen3-8B) with INT8 quantization.

Module 2 of 9 - Base Model
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, Generator

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    GenerationConfig,
)

from core.constants import (
    BASE_MODEL_NAME,
    MODEL_QUANTIZATION,
    MAX_LENGTH,
    MAX_NEW_TOKENS,
    TEMPERATURE,
    TOP_P,
    TOP_K,
    REPETITION_PENALTY,
    GPU_DEVICE,
    TARGET_VRAM_USAGE_GB,
    USE_MIXED_PRECISION,
    AUTOCAST_DTYPE,
    MODELS_DIR,
)

logger = logging.getLogger(__name__)


class STARKBaseModel:
    """
    Base language model wrapper for STARK.
    
    Handles:
    - Loading quantized Qwen3-8B model
    - Efficient inference with KV cache
    - Memory management
    - Token generation
    
    Usage:
        model = STARKBaseModel()
        response = model.generate("How to fix this error?")
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        quantization: Optional[str] = None,
        device: Optional[str] = None,
        lazy_load: bool = False
    ):
        """
        Initialize the base model.
        
        Args:
            model_name: HuggingFace model name (default from constants)
            quantization: Quantization type: "int8", "int4", "fp16", "none"
            device: Device to load model on
            lazy_load: If True, defer model loading until first use
        """
        self.model_name = model_name or BASE_MODEL_NAME
        self.quantization = quantization or MODEL_QUANTIZATION
        self.device = device or GPU_DEVICE
        
        # Model components (loaded lazily or immediately)
        self._model = None
        self._tokenizer = None
        self._generation_config = None
        
        # State tracking
        self._is_loaded = False
        self._load_time_seconds = 0.0
        self._inference_count = 0
        self._total_tokens_generated = 0
        
        if not lazy_load:
            self.load()
        
        logger.info(f"STARKBaseModel initialized (model={self.model_name}, quant={self.quantization})")
    
    # =========================================================================
    # MODEL LOADING
    # =========================================================================
    
    def load(self) -> None:
        """Load the model and tokenizer."""
        if self._is_loaded:
            logger.warning("Model already loaded")
            return
        
        start_time = time.time()
        logger.info(f"Loading model: {self.model_name} ({self.quantization})")
        
        try:
            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                padding_side="left"
            )
            
            # Ensure pad token exists
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            # Configure quantization
            quant_config = self._get_quantization_config()
            
            # Load model
            load_kwargs = {
                "trust_remote_code": True,
                "device_map": "auto",
            }
            
            if quant_config:
                load_kwargs["quantization_config"] = quant_config
            else:
                # No quantization - use mixed precision
                dtype = torch.bfloat16 if AUTOCAST_DTYPE == "bfloat16" else torch.float16
                load_kwargs["torch_dtype"] = dtype
            
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **load_kwargs
            )
            
            # Set to eval mode
            self._model.eval()
            
            # Setup generation config
            self._generation_config = GenerationConfig(
                max_new_tokens=MAX_NEW_TOKENS,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                top_k=TOP_K,
                repetition_penalty=REPETITION_PENALTY,
                do_sample=True,
                pad_token_id=self._tokenizer.pad_token_id,
                eos_token_id=self._tokenizer.eos_token_id,
            )
            
            self._is_loaded = True
            self._load_time_seconds = time.time() - start_time
            
            # Log memory usage
            memory_gb = self.get_memory_usage_gb()
            logger.info(
                f"Model loaded in {self._load_time_seconds:.1f}s, "
                f"VRAM: {memory_gb:.2f}GB"
            )
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def _get_quantization_config(self) -> Optional[BitsAndBytesConfig]:
        """Get quantization configuration based on settings."""
        if self.quantization == "int8":
            return BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_enable_fp32_cpu_offload=True,
            )
        elif self.quantization == "int4":
            return BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        else:
            return None
    
    def unload(self) -> None:
        """Unload model and free memory."""
        if self._model is not None:
            del self._model
            self._model = None
        
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        
        self._is_loaded = False
        
        # Force garbage collection
        import gc
        gc.collect()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        logger.info("Model unloaded and memory freed")
    
    # =========================================================================
    # INFERENCE
    # =========================================================================
    
    def generate(
        self,
        prompt: str,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_strings: Optional[list] = None,
    ) -> str:
        """
        Generate response for given prompt.
        
        Args:
            prompt: Input text
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling probability
            stop_strings: Strings that stop generation
            
        Returns:
            Generated text (excluding prompt)
        """
        self._ensure_loaded()
        
        start_time = time.time()
        
        # Tokenize input
        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
            padding=True,
        ).to(self._model.device)
        
        input_length = inputs.input_ids.shape[1]
        
        # Override generation config if parameters provided
        gen_config = GenerationConfig(
            max_new_tokens=max_new_tokens or MAX_NEW_TOKENS,
            temperature=temperature or TEMPERATURE,
            top_p=top_p or TOP_P,
            top_k=TOP_K,
            repetition_penalty=REPETITION_PENALTY,
            do_sample=True,
            pad_token_id=self._tokenizer.pad_token_id,
            eos_token_id=self._tokenizer.eos_token_id,
        )
        
        # Generate
        with torch.inference_mode():
            if USE_MIXED_PRECISION:
                dtype = torch.bfloat16 if AUTOCAST_DTYPE == "bfloat16" else torch.float16
                with torch.autocast(device_type="cuda", dtype=dtype):
                    outputs = self._model.generate(
                        **inputs,
                        generation_config=gen_config,
                    )
            else:
                outputs = self._model.generate(
                    **inputs,
                    generation_config=gen_config,
                )
        
        # Decode output (excluding input)
        generated_ids = outputs[0][input_length:]
        response = self._tokenizer.decode(generated_ids, skip_special_tokens=True)
        
        # Handle stop strings
        if stop_strings:
            for stop in stop_strings:
                if stop in response:
                    response = response.split(stop)[0]
        
        # Update stats
        self._inference_count += 1
        self._total_tokens_generated += len(generated_ids)
        
        latency_ms = (time.time() - start_time) * 1000
        logger.debug(f"Generated {len(generated_ids)} tokens in {latency_ms:.1f}ms")
        
        return response.strip()
    
    def generate_stream(
        self,
        prompt: str,
        max_new_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """
        Stream tokens as they are generated.
        
        Args:
            prompt: Input text
            max_new_tokens: Maximum tokens to generate
            
        Yields:
            Generated tokens one at a time
        """
        self._ensure_loaded()
        
        from transformers import TextIteratorStreamer
        import threading
        
        # Tokenize
        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
        ).to(self._model.device)
        
        # Setup streamer
        streamer = TextIteratorStreamer(
            self._tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )
        
        # Generation config
        gen_kwargs = {
            **inputs,
            "max_new_tokens": max_new_tokens or MAX_NEW_TOKENS,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "do_sample": True,
            "streamer": streamer,
        }
        
        # Run generation in background thread
        thread = threading.Thread(target=self._model.generate, kwargs=gen_kwargs)
        thread.start()
        
        # Yield tokens as they come
        for token in streamer:
            yield token
        
        thread.join()
    
    def get_embeddings(self, text: str) -> torch.Tensor:
        """
        Get hidden state embeddings for text.
        
        Args:
            text: Input text
            
        Returns:
            Last hidden state tensor
        """
        self._ensure_loaded()
        
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
        ).to(self._model.device)
        
        with torch.inference_mode():
            outputs = self._model(
                **inputs,
                output_hidden_states=True,
                return_dict=True,
            )
        
        # Return last hidden state, mean pooled
        hidden_states = outputs.hidden_states[-1]
        embeddings = hidden_states.mean(dim=1)
        
        return embeddings
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _ensure_loaded(self) -> None:
        """Ensure model is loaded before use."""
        if not self._is_loaded:
            self.load()
    
    def get_memory_usage_gb(self) -> float:
        """Get current GPU memory usage in GB."""
        if not torch.cuda.is_available():
            return 0.0
        
        return torch.cuda.memory_allocated() / (1024 ** 3)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get model statistics."""
        return {
            "model_name": self.model_name,
            "quantization": self.quantization,
            "is_loaded": self._is_loaded,
            "load_time_seconds": self._load_time_seconds,
            "inference_count": self._inference_count,
            "total_tokens_generated": self._total_tokens_generated,
            "memory_usage_gb": self.get_memory_usage_gb(),
        }
    
    def warmup(self, prompt: str = "Hello") -> float:
        """
        Warm up the model with a simple inference.
        
        Returns:
            Warmup latency in milliseconds
        """
        start = time.time()
        _ = self.generate(prompt, max_new_tokens=5)
        return (time.time() - start) * 1000
    
    @property
    def is_loaded(self) -> bool:
        return self._is_loaded
    
    @property
    def model(self):
        """Get underlying model (for advanced use)."""
        self._ensure_loaded()
        return self._model
    
    @property
    def tokenizer(self):
        """Get tokenizer."""
        self._ensure_loaded()
        return self._tokenizer
    
    def __repr__(self) -> str:
        status = "loaded" if self._is_loaded else "not loaded"
        return f"STARKBaseModel(model={self.model_name}, {status})"


# =============================================================================
# SINGLETON
# =============================================================================

_model_instance: Optional[STARKBaseModel] = None


def get_model(lazy_load: bool = True) -> STARKBaseModel:
    """
    Get or create the global model instance.
    
    Args:
        lazy_load: If True, defer loading until first inference
        
    Returns:
        STARKBaseModel instance
    """
    global _model_instance
    
    if _model_instance is None:
        _model_instance = STARKBaseModel(lazy_load=lazy_load)
    
    return _model_instance


def unload_model() -> None:
    """Unload the global model instance."""
    global _model_instance
    
    if _model_instance is not None:
        _model_instance.unload()
        _model_instance = None
