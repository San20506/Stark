"""
STARK Learning Optimizer
========================
AdamW optimizer with gradient clipping, warmup, and loss tracking.

Module 5 of 9 - Continuous Learning
"""

import logging
import math
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime

from core.constants import (
    LEARNING_RATE,
    WEIGHT_DECAY,
    WARMUP_STEPS,
    MAX_GRAD_NORM,
    CHECKPOINT_INTERVAL_STEPS,
)

logger = logging.getLogger(__name__)

# Optional PyTorch imports
try:
    import torch
    from torch.optim import AdamW
    from torch.optim.lr_scheduler import LambdaLR
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available, optimizer will be in mock mode")


@dataclass
class LossStats:
    """Track loss history and detect anomalies."""
    history: deque = field(default_factory=lambda: deque(maxlen=100))
    best_loss: float = float("inf")
    best_loss_step: int = 0
    spike_count: int = 0
    total_steps: int = 0
    
    def record(self, loss: float, step: int) -> bool:
        """
        Record a loss value.
        
        Args:
            loss: Loss value to record
            step: Current training step
            
        Returns:
            True if this is the best loss so far
        """
        self.history.append(loss)
        self.total_steps = step
        
        is_best = loss < self.best_loss
        if is_best:
            self.best_loss = loss
            self.best_loss_step = step
        
        return is_best
    
    def detect_spike(self, loss: float, threshold: float = 2.0) -> bool:
        """
        Detect if current loss is a spike.
        
        Args:
            loss: Current loss value
            threshold: Multiplier over mean to consider a spike
            
        Returns:
            True if this is a loss spike
        """
        if len(self.history) < 5:
            return False
        
        recent_mean = sum(list(self.history)[-10:]) / min(len(self.history), 10)
        
        is_spike = loss > recent_mean * threshold
        if is_spike:
            self.spike_count += 1
            logger.warning(f"Loss spike detected: {loss:.4f} > {recent_mean:.4f} * {threshold}")
        
        return is_spike
    
    def get_improvement(self, window: int = 100) -> float:
        """
        Calculate loss improvement percentage over window.
        
        Args:
            window: Number of steps to compare
            
        Returns:
            Percentage improvement (positive = getting better)
        """
        if len(self.history) < window:
            return 0.0
        
        history_list = list(self.history)
        early = sum(history_list[:window//2]) / (window//2)
        late = sum(history_list[-window//2:]) / (window//2)
        
        if early == 0:
            return 0.0
        
        return (early - late) / early * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_loss": self.history[-1] if self.history else 0,
            "best_loss": self.best_loss if self.best_loss != float("inf") else 0,
            "best_loss_step": self.best_loss_step,
            "spike_count": self.spike_count,
            "total_steps": self.total_steps,
            "improvement_percent": self.get_improvement(),
            "recent_losses": list(self.history)[-10:],
        }


class STARKOptimizer:
    """
    AdamW optimizer with gradient clipping and warmup for LoRA training.
    
    Features:
    - AdamW with configurable lr and weight decay
    - Gradient clipping to prevent explosion
    - Linear warmup schedule
    - Loss spike detection and LR reduction
    - Automatic checkpointing on improvement
    
    Usage:
        optimizer = STARKOptimizer(model.parameters())
        
        for batch in data:
            loss = model(batch)
            optimizer.step(loss)
            
        if optimizer.should_checkpoint():
            save_model()
    """
    
    def __init__(
        self,
        parameters=None,
        lr: float = LEARNING_RATE,
        weight_decay: float = WEIGHT_DECAY,
        warmup_steps: int = WARMUP_STEPS,
        max_grad_norm: float = MAX_GRAD_NORM,
        checkpoint_interval: int = CHECKPOINT_INTERVAL_STEPS,
    ):
        """
        Initialize optimizer.
        
        Args:
            parameters: Model parameters to optimize
            lr: Learning rate
            weight_decay: Weight decay for regularization
            warmup_steps: Steps for linear warmup
            max_grad_norm: Maximum gradient norm for clipping
            checkpoint_interval: Steps between checkpoints
        """
        self.base_lr = lr
        self.weight_decay = weight_decay
        self.warmup_steps = warmup_steps
        self.max_grad_norm = max_grad_norm
        self.checkpoint_interval = checkpoint_interval
        
        # Training state
        self.global_step = 0
        self.current_lr = 0.0
        self.loss_stats = LossStats()
        self._last_checkpoint_step = 0
        self._lr_reduced = False
        
        # PyTorch optimizer (if available)
        self._optimizer = None
        self._scheduler = None
        
        if TORCH_AVAILABLE and parameters is not None:
            self._init_torch_optimizer(parameters)
        
        logger.info(
            f"STARKOptimizer initialized: lr={lr}, warmup={warmup_steps}, "
            f"grad_clip={max_grad_norm}"
        )
    
    def _init_torch_optimizer(self, parameters) -> None:
        """Initialize PyTorch optimizer and scheduler."""
        self._optimizer = AdamW(
            parameters,
            lr=self.base_lr,
            weight_decay=self.weight_decay,
        )
        
        # Linear warmup then constant LR
        def lr_lambda(step):
            if step < self.warmup_steps:
                return float(step) / float(max(1, self.warmup_steps))
            return 1.0
        
        self._scheduler = LambdaLR(self._optimizer, lr_lambda)
        logger.info("PyTorch AdamW optimizer initialized")
    
    # =========================================================================
    # TRAINING STEP
    # =========================================================================
    
    def step(
        self,
        loss: 'torch.Tensor' = None,
        loss_value: float = None,
    ) -> Dict[str, Any]:
        """
        Perform optimization step.
        
        Args:
            loss: PyTorch loss tensor (will backward and step)
            loss_value: Just the loss value (for tracking only)
            
        Returns:
            Step info dict
        """
        self.global_step += 1
        
        # Track loss
        if loss is not None and TORCH_AVAILABLE:
            loss_value = loss.item()
        
        if loss_value is not None:
            is_best = self.loss_stats.record(loss_value, self.global_step)
            
            # Check for spike
            if self.loss_stats.detect_spike(loss_value):
                self._handle_loss_spike()
        
        # PyTorch optimization
        if loss is not None and self._optimizer is not None:
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            if self.max_grad_norm > 0:
                torch.nn.utils.clip_grad_norm_(
                    self._optimizer.param_groups[0]['params'],
                    self.max_grad_norm,
                )
            
            # Optimizer step
            self._optimizer.step()
            self._optimizer.zero_grad()
            
            # Update LR
            if self._scheduler:
                self._scheduler.step()
                self.current_lr = self._scheduler.get_last_lr()[0]
        else:
            # Simulated warmup for non-PyTorch mode
            self.current_lr = self._get_warmup_lr()
        
        return {
            "step": self.global_step,
            "loss": loss_value,
            "lr": self.current_lr,
            "is_best": is_best if loss_value else False,
        }
    
    def _get_warmup_lr(self) -> float:
        """Calculate LR with warmup."""
        if self.global_step < self.warmup_steps:
            return self.base_lr * (self.global_step / max(1, self.warmup_steps))
        return self.base_lr
    
    def _handle_loss_spike(self) -> None:
        """Handle loss spike by reducing LR."""
        if self._optimizer and not self._lr_reduced:
            # Reduce LR by half
            for param_group in self._optimizer.param_groups:
                param_group['lr'] *= 0.5
            
            self.current_lr *= 0.5
            self._lr_reduced = True
            
            logger.warning(f"LR reduced to {self.current_lr:.2e} due to loss spike")
    
    # =========================================================================
    # CHECKPOINTING
    # =========================================================================
    
    def should_checkpoint(self) -> bool:
        """Check if we should save a checkpoint."""
        steps_since_last = self.global_step - self._last_checkpoint_step
        return steps_since_last >= self.checkpoint_interval
    
    def mark_checkpoint_saved(self) -> None:
        """Mark that a checkpoint was saved."""
        self._last_checkpoint_step = self.global_step
    
    def is_improvement(self) -> bool:
        """Check if current loss is best so far."""
        return self.loss_stats.best_loss_step == self.global_step
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        return {
            "global_step": self.global_step,
            "current_lr": self.current_lr,
            "base_lr": self.base_lr,
            "warmup_steps": self.warmup_steps,
            "max_grad_norm": self.max_grad_norm,
            "lr_reduced": self._lr_reduced,
            "loss": self.loss_stats.to_dict(),
        }
    
    def get_loss_history(self) -> List[float]:
        """Get recent loss history."""
        return list(self.loss_stats.history)
    
    def __repr__(self) -> str:
        return (
            f"STARKOptimizer(step={self.global_step}, "
            f"lr={self.current_lr:.2e}, best_loss={self.loss_stats.best_loss:.4f})"
        )


class RetentionTester:
    """
    Test knowledge retention after training.
    
    Stores baseline performance on held-out examples and compares
    after training to detect catastrophic forgetting.
    
    Usage:
        tester = RetentionTester()
        tester.set_baseline(old_examples, model)
        
        # ... training ...
        
        retention = tester.test_retention(model)
        print(f"Retention: {retention:.1%}")
    """
    
    def __init__(self, threshold: float = 0.95):
        """
        Initialize retention tester.
        
        Args:
            threshold: Minimum retention to consider acceptable
        """
        self.threshold = threshold
        self._baseline_examples: List[Dict] = []
        self._baseline_scores: Dict[str, float] = {}
        self._test_results: List[Dict] = []
    
    def set_baseline(
        self,
        examples: List[Dict],
        model_fn=None,
    ) -> Dict[str, float]:
        """
        Set baseline performance on examples.
        
        Args:
            examples: List of {"query": str, "expected": str, "task": str}
            model_fn: Function(query) -> response
            
        Returns:
            Baseline scores by task
        """
        self._baseline_examples = examples
        
        if model_fn is None:
            # Mock baseline
            self._baseline_scores = {"overall": 1.0}
            return self._baseline_scores
        
        # Evaluate each example
        task_correct = {}
        task_total = {}
        
        for ex in examples:
            task = ex.get("task", "general")
            if task not in task_correct:
                task_correct[task] = 0
                task_total[task] = 0
            
            response = model_fn(ex["query"])
            correct = self._is_correct(response, ex["expected"])
            
            task_correct[task] += int(correct)
            task_total[task] += 1
        
        # Calculate accuracy per task
        self._baseline_scores = {
            task: task_correct[task] / task_total[task]
            for task in task_total
        }
        
        # Overall
        total_correct = sum(task_correct.values())
        total_examples = sum(task_total.values())
        self._baseline_scores["overall"] = total_correct / total_examples
        
        logger.info(f"Retention baseline set: {self._baseline_scores}")
        return self._baseline_scores
    
    def test_retention(
        self,
        model_fn=None,
    ) -> float:
        """
        Test retention compared to baseline.
        
        Args:
            model_fn: Function(query) -> response
            
        Returns:
            Retention ratio (1.0 = perfect, 0.0 = total forgetting)
        """
        if not self._baseline_examples:
            logger.warning("No baseline set, returning 100% retention")
            return 1.0
        
        if model_fn is None:
            # Mock test
            return 0.95
        
        # Evaluate current performance
        task_correct = {}
        task_total = {}
        
        for ex in self._baseline_examples:
            task = ex.get("task", "general")
            if task not in task_correct:
                task_correct[task] = 0
                task_total[task] = 0
            
            response = model_fn(ex["query"])
            correct = self._is_correct(response, ex["expected"])
            
            task_correct[task] += int(correct)
            task_total[task] += 1
        
        # Calculate current accuracy
        current_scores = {
            task: task_correct[task] / task_total[task]
            for task in task_total
        }
        
        total_correct = sum(task_correct.values())
        total_examples = sum(task_total.values())
        current_overall = total_correct / total_examples
        
        # Retention = current / baseline
        baseline_overall = self._baseline_scores.get("overall", 1.0)
        retention = current_overall / baseline_overall if baseline_overall > 0 else 1.0
        
        # Store result
        self._test_results.append({
            "timestamp": datetime.now().isoformat(),
            "retention": retention,
            "baseline": baseline_overall,
            "current": current_overall,
            "passed": retention >= self.threshold,
        })
        
        logger.info(
            f"Retention test: {retention:.1%} "
            f"({'PASS' if retention >= self.threshold else 'FAIL'})"
        )
        
        return retention
    
    def _is_correct(self, response: str, expected: str) -> bool:
        """Check if response matches expected (simple overlap check)."""
        if not response or not expected:
            return False
        
        # Normalize
        response_lower = response.lower()
        expected_lower = expected.lower()
        
        # Check key phrase overlap
        expected_words = set(expected_lower.split())
        response_words = set(response_lower.split())
        
        overlap = len(expected_words & response_words) / len(expected_words)
        return overlap > 0.5
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retention test statistics."""
        return {
            "baseline_examples": len(self._baseline_examples),
            "baseline_scores": self._baseline_scores,
            "test_count": len(self._test_results),
            "threshold": self.threshold,
            "latest_result": self._test_results[-1] if self._test_results else None,
        }


# =============================================================================
# FACTORY
# =============================================================================

def create_optimizer(
    parameters=None,
    **kwargs,
) -> STARKOptimizer:
    """Create a configured optimizer."""
    return STARKOptimizer(parameters=parameters, **kwargs)


def create_retention_tester(
    threshold: float = 0.95,
) -> RetentionTester:
    """Create a retention tester."""
    return RetentionTester(threshold=threshold)
