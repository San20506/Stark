"""
STARK Inference Engine
======================
Optimized inference wrapper with latency tracking, batching, and caching.

Module 2 of 9 - Base Model
"""

import logging
import time
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from collections import deque
import threading

import torch

from models.stark_base import STARKBaseModel, get_model
from core.constants import (
    TARGET_INFERENCE_LATENCY_MS,
    MAX_CONCURRENT_REQUESTS,
    REQUEST_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


@dataclass
class InferenceRequest:
    """Single inference request."""
    request_id: str
    prompt: str
    max_new_tokens: Optional[int] = None
    temperature: Optional[float] = None
    callback: Optional[Callable[[str], None]] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class InferenceResult:
    """Result of an inference request."""
    request_id: str
    response: str
    latency_ms: float
    tokens_generated: int
    success: bool
    error: Optional[str] = None


class InferenceEngine:
    """
    Optimized inference engine for STARK.
    
    Features:
    - Latency tracking and reporting
    - Request queuing (optional)
    - Response caching (optional)
    - Concurrent request limiting
    
    Usage:
        engine = InferenceEngine()
        result = engine.infer("What is Python?")
    """
    
    def __init__(
        self,
        model: Optional[STARKBaseModel] = None,
        enable_cache: bool = True,
        cache_size: int = 100,
    ):
        """
        Initialize inference engine.
        
        Args:
            model: Base model to use (creates new if None)
            enable_cache: Enable response caching
            cache_size: Maximum cache entries
        """
        self._model = model
        self._lock = threading.RLock()
        
        # Caching
        self._enable_cache = enable_cache
        self._cache: Dict[str, str] = {}
        self._cache_order: deque = deque(maxlen=cache_size)
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Stats
        self._latencies: deque = deque(maxlen=100)  # Rolling window
        self._total_inferences = 0
        self._total_tokens = 0
        self._errors = 0
        
        # Concurrent request tracking
        self._active_requests = 0
        
        logger.info("InferenceEngine initialized")
    
    # =========================================================================
    # INFERENCE
    # =========================================================================
    
    def infer(
        self,
        prompt: str,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True,
        **kwargs
    ) -> InferenceResult:
        """
        Run inference on prompt.
        
        Args:
            prompt: Input text
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            use_cache: Use cached response if available
            **kwargs: Additional generation parameters
            
        Returns:
            InferenceResult with response and metrics
        """
        request_id = f"req_{self._total_inferences}"
        
        # Check cache
        cache_key = self._make_cache_key(prompt, max_new_tokens, temperature)
        if use_cache and self._enable_cache and cache_key in self._cache:
            self._cache_hits += 1
            return InferenceResult(
                request_id=request_id,
                response=self._cache[cache_key],
                latency_ms=0.0,
                tokens_generated=0,
                success=True,
            )
        
        self._cache_misses += 1
        
        # Check concurrent limit
        if self._active_requests >= MAX_CONCURRENT_REQUESTS:
            return InferenceResult(
                request_id=request_id,
                response="",
                latency_ms=0.0,
                tokens_generated=0,
                success=False,
                error="Too many concurrent requests",
            )
        
        # Run inference
        start_time = time.time()
        
        try:
            with self._lock:
                self._active_requests += 1
            
            model = self._get_model()
            response = model.generate(
                prompt=prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                **kwargs
            )
            
            latency_ms = (time.time() - start_time) * 1000
            tokens = len(model.tokenizer.encode(response))
            
            # Update stats
            self._latencies.append(latency_ms)
            self._total_inferences += 1
            self._total_tokens += tokens
            
            # Cache response
            if self._enable_cache:
                self._add_to_cache(cache_key, response)
            
            # Log if slow
            if latency_ms > TARGET_INFERENCE_LATENCY_MS:
                logger.warning(
                    f"Slow inference: {latency_ms:.1f}ms "
                    f"(target: {TARGET_INFERENCE_LATENCY_MS}ms)"
                )
            
            return InferenceResult(
                request_id=request_id,
                response=response,
                latency_ms=latency_ms,
                tokens_generated=tokens,
                success=True,
            )
            
        except Exception as e:
            self._errors += 1
            logger.error(f"Inference failed: {e}")
            return InferenceResult(
                request_id=request_id,
                response="",
                latency_ms=(time.time() - start_time) * 1000,
                tokens_generated=0,
                success=False,
                error=str(e),
            )
        finally:
            with self._lock:
                self._active_requests -= 1
    
    def infer_batch(
        self,
        prompts: List[str],
        max_new_tokens: Optional[int] = None,
    ) -> List[InferenceResult]:
        """
        Run inference on multiple prompts.
        
        Note: Currently runs sequentially. Future: true batching.
        
        Args:
            prompts: List of input texts
            max_new_tokens: Maximum tokens per response
            
        Returns:
            List of InferenceResult objects
        """
        results = []
        for prompt in prompts:
            result = self.infer(prompt, max_new_tokens=max_new_tokens)
            results.append(result)
        return results
    
    def stream(
        self,
        prompt: str,
        max_new_tokens: Optional[int] = None,
    ):
        """
        Stream tokens as they are generated.
        
        Args:
            prompt: Input text
            max_new_tokens: Maximum tokens
            
        Yields:
            Tokens as they are generated
        """
        model = self._get_model()
        yield from model.generate_stream(prompt, max_new_tokens)
    
    # =========================================================================
    # CACHING
    # =========================================================================
    
    def _make_cache_key(
        self,
        prompt: str,
        max_new_tokens: Optional[int],
        temperature: Optional[float]
    ) -> str:
        """Create cache key from request parameters."""
        return f"{hash(prompt)}_{max_new_tokens}_{temperature}"
    
    def _add_to_cache(self, key: str, response: str) -> None:
        """Add response to cache with LRU eviction."""
        if key in self._cache:
            return
        
        # Evict oldest if at capacity
        if len(self._cache_order) >= self._cache_order.maxlen:
            oldest = self._cache_order.popleft()
            self._cache.pop(oldest, None)
        
        self._cache[key] = response
        self._cache_order.append(key)
    
    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._cache.clear()
        self._cache_order.clear()
        logger.info("Inference cache cleared")
    
    # =========================================================================
    # MODEL MANAGEMENT
    # =========================================================================
    
    def _get_model(self) -> STARKBaseModel:
        """Get or create the model instance."""
        if self._model is None:
            self._model = get_model(lazy_load=False)
        return self._model
    
    def warmup(self) -> Dict[str, float]:
        """
        Warm up the model and measure baseline latency.
        
        Returns:
            Dict with warmup metrics
        """
        logger.info("Warming up inference engine...")
        
        model = self._get_model()
        
        # First inference (includes any remaining loading)
        start = time.time()
        _ = model.generate("Hello", max_new_tokens=5)
        first_latency = (time.time() - start) * 1000
        
        # Second inference (warm cache)
        start = time.time()
        _ = model.generate("Hi there", max_new_tokens=5)
        warm_latency = (time.time() - start) * 1000
        
        logger.info(
            f"Warmup complete: first={first_latency:.1f}ms, "
            f"warm={warm_latency:.1f}ms"
        )
        
        return {
            "first_inference_ms": first_latency,
            "warm_inference_ms": warm_latency,
        }
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get inference statistics."""
        latencies = list(self._latencies)
        
        return {
            "total_inferences": self._total_inferences,
            "total_tokens": self._total_tokens,
            "errors": self._errors,
            "active_requests": self._active_requests,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": (
                self._cache_hits / (self._cache_hits + self._cache_misses)
                if (self._cache_hits + self._cache_misses) > 0 else 0
            ),
            "latency_avg_ms": sum(latencies) / len(latencies) if latencies else 0,
            "latency_p50_ms": sorted(latencies)[len(latencies)//2] if latencies else 0,
            "latency_p99_ms": sorted(latencies)[int(len(latencies)*0.99)] if latencies else 0,
            "model_stats": self._get_model().get_stats() if self._model else {},
        }
    
    def __repr__(self) -> str:
        return f"InferenceEngine(inferences={self._total_inferences}, cache={self._enable_cache})"


# =============================================================================
# SINGLETON
# =============================================================================

_engine_instance: Optional[InferenceEngine] = None


def get_engine() -> InferenceEngine:
    """Get or create the global inference engine."""
    global _engine_instance
    
    if _engine_instance is None:
        _engine_instance = InferenceEngine()
    
    return _engine_instance
