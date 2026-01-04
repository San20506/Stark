"""
STARK Performance Profiler
===========================
Memory and latency profiling for performance analysis.

Module 9 of 9 - Utilities
"""

import functools
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from collections import defaultdict

from core.constants import (
    VRAM_LIMIT_GB,
    VRAM_CRITICAL_THRESHOLD_GB,
)

logger = logging.getLogger(__name__)

# GPU profiling is optional
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class TimingStats:
    """Statistics for a profiled operation."""
    name: str
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0
    
    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count > 0 else 0.0
    
    def record(self, duration_ms: float) -> None:
        self.count += 1
        self.total_ms += duration_ms
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "count": self.count,
            "avg_ms": round(self.avg_ms, 2),
            "min_ms": round(self.min_ms, 2) if self.min_ms != float("inf") else 0,
            "max_ms": round(self.max_ms, 2),
            "total_ms": round(self.total_ms, 2),
        }


class Profiler:
    """
    Performance profiler for STARK.
    
    Features:
    - Function timing via decorator or context manager
    - VRAM and system RAM monitoring
    - Latency breakdown by pipeline stage
    - Bottleneck identification
    
    Usage:
        profiler = Profiler()
        
        # Decorator
        @profiler.profile
        def my_function():
            pass
        
        # Context manager
        with profiler.measure("my_operation"):
            # code here
        
        # Get stats
        print(profiler.get_stats())
    """
    
    def __init__(self):
        self._timings: Dict[str, TimingStats] = defaultdict(
            lambda: TimingStats(name="unknown")
        )
        self._active_timers: Dict[str, float] = {}
    
    # =========================================================================
    # TIMING
    # =========================================================================
    
    @contextmanager
    def measure(self, name: str):
        """
        Context manager for timing a code block.
        
        Args:
            name: Name for this operation
            
        Usage:
            with profiler.measure("inference"):
                result = model.generate(prompt)
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self._record_timing(name, duration_ms)
    
    def profile(self, func: Callable) -> Callable:
        """
        Decorator for profiling a function.
        
        Args:
            func: Function to profile
            
        Returns:
            Wrapped function
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self.measure(func.__name__):
                return func(*args, **kwargs)
        return wrapper
    
    def start(self, name: str) -> None:
        """Start a named timer."""
        self._active_timers[name] = time.perf_counter()
    
    def stop(self, name: str) -> float:
        """
        Stop a named timer and record.
        
        Returns:
            Duration in milliseconds
        """
        if name not in self._active_timers:
            logger.warning(f"Timer '{name}' not started")
            return 0.0
        
        start = self._active_timers.pop(name)
        duration_ms = (time.perf_counter() - start) * 1000
        self._record_timing(name, duration_ms)
        return duration_ms
    
    def _record_timing(self, name: str, duration_ms: float) -> None:
        """Record timing for an operation."""
        if name not in self._timings:
            self._timings[name] = TimingStats(name=name)
        self._timings[name].record(duration_ms)
    
    # =========================================================================
    # MEMORY PROFILING
    # =========================================================================
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get current memory usage.
        
        Returns:
            Dict with VRAM and RAM stats
        """
        stats = {
            "vram_available": TORCH_AVAILABLE,
            "vram_used_gb": 0.0,
            "vram_total_gb": 0.0,
            "vram_percent": 0.0,
            "vram_critical": False,
        }
        
        if TORCH_AVAILABLE and torch.cuda.is_available():
            try:
                vram_used = torch.cuda.memory_allocated() / (1024**3)
                vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                
                stats["vram_used_gb"] = round(vram_used, 2)
                stats["vram_total_gb"] = round(vram_total, 2)
                stats["vram_percent"] = round(vram_used / vram_total * 100, 1)
                stats["vram_critical"] = vram_used > VRAM_CRITICAL_THRESHOLD_GB
            except Exception as e:
                logger.warning(f"Failed to get VRAM stats: {e}")
        
        # System RAM (optional)
        try:
            import psutil
            mem = psutil.virtual_memory()
            stats["ram_used_gb"] = round(mem.used / (1024**3), 2)
            stats["ram_total_gb"] = round(mem.total / (1024**3), 2)
            stats["ram_percent"] = mem.percent
        except ImportError:
            pass
        
        return stats
    
    def check_memory(self) -> bool:
        """
        Check if memory is within limits.
        
        Returns:
            True if OK, False if critical
        """
        stats = self.get_memory_stats()
        
        if stats.get("vram_critical"):
            logger.warning(
                f"VRAM critical: {stats['vram_used_gb']:.1f}GB / "
                f"{VRAM_CRITICAL_THRESHOLD_GB}GB threshold"
            )
            return False
        
        return True
    
    def force_cleanup(self) -> Dict[str, float]:
        """
        Force memory cleanup.
        
        Returns:
            Memory freed stats
        """
        before = self.get_memory_stats()
        
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        import gc
        gc.collect()
        
        after = self.get_memory_stats()
        
        freed = {
            "vram_freed_gb": before.get("vram_used_gb", 0) - after.get("vram_used_gb", 0),
            "ram_freed_gb": before.get("ram_used_gb", 0) - after.get("ram_used_gb", 0),
        }
        
        logger.info(f"Memory cleanup: freed {freed['vram_freed_gb']:.2f}GB VRAM")
        return freed
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all profiling statistics."""
        return {
            "timings": {
                name: stats.to_dict()
                for name, stats in self._timings.items()
            },
            "memory": self.get_memory_stats(),
        }
    
    def get_bottlenecks(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Identify top-k slowest operations.
        
        Args:
            top_k: Number of bottlenecks to return
            
        Returns:
            List of slowest operations
        """
        sorted_timings = sorted(
            self._timings.values(),
            key=lambda t: t.avg_ms,
            reverse=True,
        )
        return [t.to_dict() for t in sorted_timings[:top_k]]
    
    def reset(self) -> None:
        """Reset all timing statistics."""
        self._timings.clear()
        self._active_timers.clear()
    
    def __repr__(self) -> str:
        return f"Profiler(operations={len(self._timings)})"


# =============================================================================
# SINGLETON
# =============================================================================

_profiler_instance: Optional[Profiler] = None


def get_profiler() -> Profiler:
    """Get or create the global profiler."""
    global _profiler_instance
    
    if _profiler_instance is None:
        _profiler_instance = Profiler()
    
    return _profiler_instance


# =============================================================================
# DECORATOR SHORTCUT
# =============================================================================

def profile(func: Callable) -> Callable:
    """Decorator shortcut for profiling."""
    return get_profiler().profile(func)
