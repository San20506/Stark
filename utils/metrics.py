"""
STARK Metrics Logger
====================
TensorBoard integration for tracking system performance.

Module 9 of 9 - Utilities (Partial)
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from core.constants import (
    LOGS_DIR,
    TENSORBOARD_ENABLED,
    METRICS_FLUSH_INTERVAL_SECONDS,
)

logger = logging.getLogger(__name__)

# TensorBoard is optional
try:
    from torch.utils.tensorboard import SummaryWriter
    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False
    logger.warning("TensorBoard not available, metrics will be logged only")


class MetricsLogger:
    """
    Centralized metrics logging with TensorBoard integration.
    
    Hooks into get_stats() from all modules to track:
    - Memory node count and activation levels
    - Learning loss and feedback scores  
    - Inference latency
    - Emergent task detection rates
    
    Usage:
        metrics = MetricsLogger()
        metrics.log_memory_stats(memory.get_stats())
        metrics.log_learning_stats(learner.get_stats())
        metrics.log_detection_stats(detector.get_stats())
    """
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        run_name: Optional[str] = None,
    ):
        """
        Initialize metrics logger.
        
        Args:
            log_dir: Directory for TensorBoard logs
            run_name: Name for this run (default: timestamp)
        """
        self.log_dir = log_dir or LOGS_DIR / "tensorboard"
        self.run_name = run_name or f"stark_{datetime.now():%Y%m%d_%H%M%S}"
        
        # TensorBoard writer
        self._writer: Optional['SummaryWriter'] = None
        if TENSORBOARD_ENABLED and TENSORBOARD_AVAILABLE:
            run_path = self.log_dir / self.run_name
            run_path.mkdir(parents=True, exist_ok=True)
            self._writer = SummaryWriter(log_dir=str(run_path))
            logger.info(f"TensorBoard logging to {run_path}")
        
        # Global step counter
        self._step = 0
        self._last_flush = time.time()
        
        logger.info(f"MetricsLogger initialized: tensorboard={self._writer is not None}")
    
    # =========================================================================
    # MEMORY METRICS
    # =========================================================================
    
    def log_memory_stats(self, stats: Dict[str, Any]) -> None:
        """Log neuromorphic memory statistics."""
        if not self._writer:
            return
        
        self._writer.add_scalar("memory/total_nodes", stats.get("total_nodes", 0), self._step)
        self._writer.add_scalar("memory/alive_nodes", stats.get("alive_nodes", 0), self._step)
        self._writer.add_scalar("memory/total_connections", stats.get("total_connections", 0), self._step)
        self._writer.add_scalar("memory/stores", stats.get("stores", 0), self._step)
        self._writer.add_scalar("memory/recalls", stats.get("recalls", 0), self._step)
        
        # Task distribution as histogram
        task_dist = stats.get("task_distribution", {})
        if task_dist:
            for task, count in task_dist.items():
                self._writer.add_scalar(f"memory/task_{task}", count, self._step)
        
        self._maybe_flush()
    
    # =========================================================================
    # LEARNING METRICS
    # =========================================================================
    
    def log_learning_stats(self, stats: Dict[str, Any]) -> None:
        """Log continuous learning statistics."""
        if not self._writer:
            return
        
        self._writer.add_scalar("learning/total_samples", stats.get("total_samples", 0), self._step)
        self._writer.add_scalar("learning/total_batches", stats.get("total_batches", 0), self._step)
        self._writer.add_scalar("learning/total_updates", stats.get("total_updates", 0), self._step)
        self._writer.add_scalar("learning/avg_feedback_score", stats.get("avg_feedback_score", 0), self._step)
        self._writer.add_scalar("learning/pending_feedback", stats.get("pending_feedback", 0), self._step)
        
        # Loss history as line plot
        recent_losses = stats.get("recent_losses", [])
        if recent_losses:
            for i, loss in enumerate(recent_losses):
                self._writer.add_scalar("learning/recent_loss", loss, self._step - len(recent_losses) + i)
        
        self._maybe_flush()
    
    # =========================================================================
    # DETECTION METRICS
    # =========================================================================
    
    def log_detection_stats(self, stats: Dict[str, Any]) -> None:
        """Log task detection statistics."""
        if not self._writer:
            return
        
        self._writer.add_scalar("detection/total_detections", stats.get("total_detections", 0), self._step)
        self._writer.add_scalar("detection/emergent_count", stats.get("emergent_count", 0), self._step)
        
        # Task counts
        task_counts = stats.get("task_counts", {})
        for task, count in task_counts.items():
            self._writer.add_scalar(f"detection/task_{task}", count, self._step)
        
        # Emergent ratio
        total = stats.get("total_detections", 0)
        emergent = stats.get("emergent_count", 0)
        if total > 0:
            self._writer.add_scalar("detection/emergent_ratio", emergent / total, self._step)
        
        self._maybe_flush()
    
    # =========================================================================
    # INFERENCE METRICS
    # =========================================================================
    
    def log_inference(
        self,
        latency_ms: float,
        task: str,
        confidence: float,
        is_emergent: bool = False,
    ) -> None:
        """Log single inference metrics."""
        if not self._writer:
            return
        
        self._writer.add_scalar("inference/latency_ms", latency_ms, self._step)
        self._writer.add_scalar("inference/confidence", confidence, self._step)
        self._writer.add_scalar("inference/is_emergent", int(is_emergent), self._step)
        
        self._step += 1
        self._maybe_flush()
    
    # =========================================================================
    # SYSTEM METRICS  
    # =========================================================================
    
    def log_system_stats(
        self,
        vram_mb: Optional[float] = None,
        ram_mb: Optional[float] = None,
    ) -> None:
        """Log system resource usage."""
        if not self._writer:
            return
        
        if vram_mb is not None:
            self._writer.add_scalar("system/vram_mb", vram_mb, self._step)
        if ram_mb is not None:
            self._writer.add_scalar("system/ram_mb", ram_mb, self._step)
        
        self._maybe_flush()
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _maybe_flush(self) -> None:
        """Flush writer if interval elapsed."""
        now = time.time()
        if now - self._last_flush > METRICS_FLUSH_INTERVAL_SECONDS:
            self.flush()
            self._last_flush = now
    
    def flush(self) -> None:
        """Force flush all pending metrics."""
        if self._writer:
            self._writer.flush()
    
    def close(self) -> None:
        """Close the writer."""
        if self._writer:
            self._writer.close()
            self._writer = None
    
    def step(self) -> None:
        """Increment global step counter."""
        self._step += 1
    
    @property
    def current_step(self) -> int:
        """Get current step."""
        return self._step
    
    def __repr__(self) -> str:
        status = "active" if self._writer else "disabled"
        return f"MetricsLogger({status}, step={self._step})"


# =============================================================================
# SINGLETON
# =============================================================================

_metrics_instance: Optional[MetricsLogger] = None


def get_metrics() -> MetricsLogger:
    """Get or create the global metrics logger."""
    global _metrics_instance
    
    if _metrics_instance is None:
        _metrics_instance = MetricsLogger()
    
    return _metrics_instance
