"""
STARK Continuous Learning
=========================
Background thread for continuous improvement via memory sampling.

Module 5 of 9 - Continuous Learning
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from core.constants import (
    TRAIN_INTERVAL_SECONDS,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    BATCH_SIZE,
    LEARNING_RATE,
    CONNECTION_SIMILARITY_THRESHOLD,
    CONNECTION_HEBBIAN_RATE,
    DATA_DIR,
)

logger = logging.getLogger(__name__)

# Queue depth thresholds for backpressure
QUEUE_WARNING_THRESHOLD = 100
QUEUE_CRITICAL_THRESHOLD = 500


@dataclass
class TrainingStats:
    """Statistics for training progress."""
    total_samples: int = 0
    total_batches: int = 0
    total_updates: int = 0
    avg_feedback_score: float = 0.0
    last_update_time: Optional[datetime] = None
    loss_history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_samples": self.total_samples,
            "total_batches": self.total_batches,
            "total_updates": self.total_updates,
            "avg_feedback_score": self.avg_feedback_score,
            "last_update_time": str(self.last_update_time) if self.last_update_time else None,
            "recent_losses": list(self.loss_history)[-10:] if self.loss_history else [],
        }


@dataclass 
class FeedbackEntry:
    """User feedback for a response."""
    query: str
    response: str
    task: str
    score: float  # -1 to 1 (negative = bad, positive = good)
    timestamp: datetime = field(default_factory=datetime.now)


class ContinualLearner:
    """
    Background thread for continuous learning from user interactions.
    
    Collects user feedback and stores high-quality examples for future
    fine-tuning. Since we use Ollama for inference, actual weight updates
    happen when we export data for model fine-tuning.
    
    Usage:
        learner = ContinualLearner(memory, adapter_manager)
        learner.start()
        
        # Add feedback when user corrects/approves responses
        learner.add_feedback(query, response, task, score=0.8)
        
        learner.stop()
    """
    
    def __init__(
        self,
        memory=None,  # NeuromorphicMemory
        adapter_manager=None,  # AdapterManager
        ollama_url: str = OLLAMA_BASE_URL,
        train_interval: int = TRAIN_INTERVAL_SECONDS,
        min_samples: int = 10,
    ):
        """
        Initialize continuous learner.
        
        Args:
            memory: NeuromorphicMemory for storing experiences
            adapter_manager: AdapterManager for tracking adapters
            ollama_url: Ollama API URL for inference
            train_interval: Seconds between training cycles
            min_samples: Minimum samples needed before processing
        """
        self.memory = memory
        self.adapter_manager = adapter_manager
        self.ollama_url = ollama_url
        self.train_interval = train_interval
        self.min_samples = min_samples
        
        # Feedback buffer
        self._feedback_buffer: deque = deque(maxlen=10000)
        self._pending_feedback: List[FeedbackEntry] = []
        
        # Thread control
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = TrainingStats()
        
        # Callbacks for events
        self._on_feedback_processed: Optional[Callable] = None
        
        logger.info(
            f"ContinualLearner initialized: interval={train_interval}s, "
            f"min_samples={min_samples}"
        )
    
    # =========================================================================
    # THREAD CONTROL
    # =========================================================================
    
    def start(self) -> None:
        """Start the background learning thread."""
        if self._running:
            logger.warning("ContinualLearner already running")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._learning_loop,
            name="ContinualLearner",
            daemon=True,
        )
        self._thread.start()
        logger.info("ContinualLearner started")
    
    def stop(self, timeout: float = 5.0) -> None:
        """
        Stop the background learning thread.
        
        Args:
            timeout: Seconds to wait for thread to stop
        """
        if not self._running:
            return
        
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("ContinualLearner thread did not stop cleanly")
        
        self._thread = None
        logger.info("ContinualLearner stopped")
    
    def is_running(self) -> bool:
        """Check if learning thread is running."""
        return self._running and self._thread is not None and self._thread.is_alive()
    
    @property
    def is_backpressured(self) -> bool:
        """Check if queue depth exceeds warning threshold (for external backpressure)."""
        return len(self._pending_feedback) > QUEUE_WARNING_THRESHOLD
    
    @property
    def queue_depth(self) -> int:
        """Get current pending feedback count."""
        return len(self._pending_feedback)
    
    # =========================================================================
    # FEEDBACK COLLECTION
    # =========================================================================
    
    def add_feedback(
        self,
        query: str,
        response: str,
        task: str,
        score: float,
    ) -> None:
        """
        Add user feedback for a response.
        
        Args:
            query: Original query
            response: Model's response
            task: Task category
            score: Feedback score (-1 to 1)
        """
        score = max(-1.0, min(1.0, score))  # Clamp to [-1, 1]
        
        entry = FeedbackEntry(
            query=query,
            response=response,
            task=task,
            score=score,
        )
        
        with self._lock:
            self._pending_feedback.append(entry)
            self._feedback_buffer.append(entry)
            self.stats.total_samples += 1
        
        # Store positive feedback in memory for future retrieval
        if score > 0.5 and self.memory:
            self.memory.store(query, response, task)
            logger.debug(f"Stored positive feedback in memory: {task}")
        
        logger.debug(f"Feedback added: task={task}, score={score:.2f}")
    
    def add_positive_example(self, query: str, response: str, task: str) -> None:
        """Shorthand for adding strong positive feedback."""
        self.add_feedback(query, response, task, score=1.0)
    
    def add_negative_example(self, query: str, response: str, task: str) -> None:
        """Shorthand for adding strong negative feedback."""
        self.add_feedback(query, response, task, score=-1.0)
    
    # =========================================================================
    # LEARNING LOOP
    # =========================================================================
    
    def _learning_loop(self) -> None:
        """Main background learning loop."""
        logger.info("Learning loop started")
        
        while self._running:
            try:
                # Wait for interval
                time.sleep(self.train_interval)
                
                if not self._running:
                    break
                
                # Process pending feedback
                self._process_feedback()
                
            except Exception as e:
                logger.error(f"Error in learning loop: {e}")
                time.sleep(5)  # Back off on error
        
        logger.info("Learning loop stopped")
    
    def _process_feedback(self) -> None:
        """
        Process accumulated feedback with Hebbian learning and auto-export.
        
        Enhanced to:
        - Filter high-quality feedback (score > 0.5)
        - Trigger Hebbian updates for memory strengthening
        - Auto-export to JSONL when batch threshold met
        - Monitor queue depth for backpressure
        """
        # Check queue depth for backpressure warning
        queue_size = len(self._pending_feedback)
        if queue_size > QUEUE_CRITICAL_THRESHOLD:
            logger.warning(
                f"Feedback queue critical: {queue_size} items, "
                "consider pausing inference"
            )
        elif queue_size > QUEUE_WARNING_THRESHOLD:
            logger.warning(f"Feedback queue depth high: {queue_size} items")
        
        with self._lock:
            if len(self._pending_feedback) < self.min_samples:
                return
            
            # Get pending feedback
            pending = self._pending_feedback.copy()
            self._pending_feedback.clear()
        
        if not pending:
            return
        
        logger.info(f"Processing {len(pending)} feedback entries")
        
        # Filter high-quality feedback
        high_quality = [e for e in pending if e.score > 0.5]
        low_quality = [e for e in pending if e.score <= 0.5]
        
        logger.debug(
            f"Quality split: {len(high_quality)} high, {len(low_quality)} low"
        )
        
        # Group by task
        by_task: Dict[str, List[FeedbackEntry]] = {}
        for entry in pending:
            if entry.task not in by_task:
                by_task[entry.task] = []
            by_task[entry.task].append(entry)
        
        # Process each task's feedback with Hebbian hooks
        for task, entries in by_task.items():
            self._process_task_feedback(task, entries)
        
        # Auto-export when batch threshold met
        if len(high_quality) >= BATCH_SIZE:
            export_path = DATA_DIR / f"feedback_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
            export_path.parent.mkdir(parents=True, exist_ok=True)
            count = self.export_to_jsonl(str(export_path), min_score=0.5)
            logger.info(f"Auto-exported {count} high-quality examples to {export_path}")
        
        # Update statistics
        avg_score = sum(e.score for e in pending) / len(pending)
        self.stats.avg_feedback_score = (
            self.stats.avg_feedback_score * 0.9 + avg_score * 0.1
        )
        self.stats.total_batches += 1
        self.stats.last_update_time = datetime.now()
        
        # Call callback if set
        if self._on_feedback_processed:
            self._on_feedback_processed(len(pending), avg_score)
        
        logger.info(
            f"Processed feedback: {len(pending)} entries, "
            f"avg_score={avg_score:.2f}, high_quality={len(high_quality)}"
        )
    
    def _process_task_feedback(
        self,
        task: str,
        entries: List[FeedbackEntry],
    ) -> None:
        """
        Process feedback for a specific task with Hebbian learning.
        
        Args:
            task: Task name
            entries: Feedback entries for this task
        """
        positive = [e for e in entries if e.score > 0]
        negative = [e for e in entries if e.score < 0]
        high_quality = [e for e in positive if e.score > 0.7]
        
        logger.debug(
            f"Task '{task}': {len(positive)} positive, {len(negative)} negative, "
            f"{len(high_quality)} high-quality"
        )
        
        # Store and strengthen high-quality positives in memory
        stored_node_ids = []
        for entry in high_quality:
            if self.memory:
                # Store in memory
                node_id = self.memory.store(
                    query=entry.query,
                    response=entry.response,
                    task=task,
                )
                stored_node_ids.append(node_id)
                
                # Find similar nodes and strengthen connections (Hebbian hook)
                if hasattr(self.memory, '_find_similar_nodes') and hasattr(self.memory, '_encode'):
                    embedding = self.memory._encode(entry.query)
                    similar = self.memory._find_similar_nodes(
                        embedding, task=task, exclude_id=node_id
                    )
                    
                    # Trigger Hebbian update for similar high-quality nodes
                    hebbian_targets = [
                        node_id,  # Include the new node
                        *[nid for nid, score in similar[:5] 
                          if score > CONNECTION_SIMILARITY_THRESHOLD]
                    ]
                    
                    if len(hebbian_targets) > 1 and hasattr(self.memory, '_hebbian_update'):
                        self.memory._hebbian_update(hebbian_targets)
                        logger.debug(
                            f"Hebbian update: strengthened {len(hebbian_targets)} connections"
                        )
        
        # Track adapter stats if available
        if self.adapter_manager:
            adapter = self.adapter_manager.get_adapter(task)
            if adapter:
                adapter._training_steps += len(high_quality)
                self.stats.total_updates += len(high_quality)
    
    # =========================================================================
    # EXPORT FOR FINE-TUNING
    # =========================================================================
    
    def export_training_data(self, min_score: float = 0.5) -> List[Dict]:
        """
        Export high-quality feedback for external fine-tuning.
        
        Args:
            min_score: Minimum score to include
            
        Returns:
            List of training examples in standard format
        """
        with self._lock:
            filtered = [
                {
                    "query": e.query,
                    "response": e.response,
                    "task": e.task,
                    "score": e.score,
                }
                for e in self._feedback_buffer
                if e.score >= min_score
            ]
        
        logger.info(f"Exported {len(filtered)} training examples")
        return filtered
    
    def export_to_jsonl(self, path: str, min_score: float = 0.5) -> int:
        """
        Export training data to JSONL file.
        
        Args:
            path: Output file path
            min_score: Minimum score to include
            
        Returns:
            Number of examples exported
        """
        import json
        
        data = self.export_training_data(min_score)
        
        with open(path, "w") as f:
            for example in data:
                f.write(json.dumps(example) + "\n")
        
        logger.info(f"Exported {len(data)} examples to {path}")
        return len(data)
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        with self._lock:
            return {
                "is_running": self.is_running(),
                "pending_feedback": len(self._pending_feedback),
                "total_buffer": len(self._feedback_buffer),
                **self.stats.to_dict(),
            }
    
    def get_task_breakdown(self) -> Dict[str, Dict[str, int]]:
        """Get feedback breakdown by task."""
        with self._lock:
            breakdown: Dict[str, Dict[str, int]] = {}
            
            for entry in self._feedback_buffer:
                if entry.task not in breakdown:
                    breakdown[entry.task] = {"positive": 0, "negative": 0, "total": 0}
                
                breakdown[entry.task]["total"] += 1
                if entry.score > 0:
                    breakdown[entry.task]["positive"] += 1
                else:
                    breakdown[entry.task]["negative"] += 1
            
            return breakdown
    
    # =========================================================================
    # CALLBACKS
    # =========================================================================
    
    def on_feedback_processed(self, callback: Callable) -> None:
        """
        Set callback for when feedback is processed.
        
        Args:
            callback: Function(count, avg_score)
        """
        self._on_feedback_processed = callback
    
    def __repr__(self) -> str:
        status = "running" if self.is_running() else "stopped"
        return f"ContinualLearner({status}, samples={self.stats.total_samples})"


# =============================================================================
# SINGLETON
# =============================================================================

_learner_instance: Optional[ContinualLearner] = None


def get_learner(
    memory=None,
    adapter_manager=None,
) -> ContinualLearner:
    """
    Get or create the global continual learner.
    
    Args:
        memory: NeuromorphicMemory instance
        adapter_manager: AdapterManager instance
        
    Returns:
        ContinualLearner instance
    """
    global _learner_instance
    
    if _learner_instance is None:
        _learner_instance = ContinualLearner(
            memory=memory,
            adapter_manager=adapter_manager,
        )
    
    return _learner_instance
