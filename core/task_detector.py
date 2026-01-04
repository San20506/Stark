"""
STARK Task Detector
====================
Classify user queries into task categories using TF-IDF and cosine similarity.

Module 6 of 9 - Task Detection
"""

import logging
import re
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.constants import (
    TASK_CATEGORIES,
    TASK_DETECTION_THRESHOLD,
    DATA_DIR,
)

logger = logging.getLogger(__name__)


# =============================================================================
# TASK DEFINITIONS
# =============================================================================

# Keywords and example phrases for each task category
TASK_PATTERNS: Dict[str, Dict[str, Any]] = {
    "error_debugging": {
        "keywords": [
            "error", "bug", "fix", "crash", "exception", "traceback",
            "failed", "broken", "not working", "issue", "problem",
            "debug", "stack trace", "undefined", "null", "type error",
            "indexerror", "keyerror", "valueerror", "attributeerror",
        ],
        "examples": [
            "How do I fix this IndexError?",
            "Why is my code crashing?",
            "Debug this error message",
            "What does this exception mean?",
            "My function is not working",
            "I got a TypeError in my code",
            "Fix this bug for me",
            "Why am I getting this error?",
            "This code throws an exception",
            "Help me debug this problem",
            "There's a bug in my program",
            "The application crashed",
            "I see an error in the console",
            "Something is broken in my code",
            "How to solve this error?",
        ],
    },
    "code_explanation": {
        "keywords": [
            "explain", "what does", "how does", "understand", "meaning",
            "what is", "why does", "describe", "clarify", "walk through",
            "code", "function", "class", "method", "algorithm", "syntax",
        ],
        "examples": [
            "Explain this code to me",
            "What does this function do?",
            "How does this algorithm work?",
            "Walk me through this class",
            "What is a decorator?",
            "Can you explain this syntax?",
            "Help me understand this code",
            "What does this method return?",
            "Describe what this function does",
            "Explain the purpose of this class",
            "What is happening in this code?",
            "How does this work?",
            "Explain this to me",
            "Walk me through this code",
            "What does this line mean?",
        ],
    },
    "task_planning": {
        "keywords": [
            "plan", "schedule", "organize", "todo", "task", "project",
            "steps", "roadmap", "timeline", "milestone", "priority",
            "break down", "structure", "outline", "strategy",
        ],
        "examples": [
            "Plan my day",
            "Plan my project",
            "Create a project roadmap",
            "What steps should I take?",
            "Help me organize my tasks",
            "Break down this project",
            "Create a schedule for me",
            "Help me plan this feature",
            "What's my priority today?",
            "Organize my work",
            "Create a timeline",
            "Help me structure my project",
            "What should I do first?",
            "Make a plan for this",
            "How should I organize this?",
        ],
    },
    "research": {
        "keywords": [
            "research", "find", "search", "look up", "information",
            "learn", "discover", "explore", "investigate", "compare",
            "best", "options", "alternatives", "recommend",
        ],
        "examples": [
            "Research the best frameworks",
            "Find information about Python",
            "Compare these two libraries",
            "What are the alternatives?",
            "Learn about machine learning",
            "Find the best option",
            "Look up this topic",
            "What should I learn next?",
            "Explore this technology",
            "Research this for me",
            "Find out about AI",
            "What are my options?",
            "Recommend a library",
            "Search for best practices",
            "Investigate this issue",
        ],
    },
    "health_monitoring": {
        "keywords": [
            "health", "posture", "break", "rest", "tired", "strain",
            "ergonomic", "sitting", "standing", "exercise", "stretch",
            "eye", "back", "neck", "wellness", "remind",
        ],
        "examples": [
            "Remind me to take a break",
            "Check my posture",
            "I've been sitting too long",
            "My eyes are tired",
            "Suggest some stretches",
            "I need a break",
            "Time for a rest",
            "My back hurts",
            "I'm feeling tired",
            "Remind me to stand up",
            "Check my health",
            "I should stretch",
            "My neck is stiff",
            "Take a wellness break",
            "Eye strain reminder",
        ],
    },
    "system_control": {
        "keywords": [
            "open", "close", "launch", "start", "stop", "run",
            "application", "program", "window", "volume", "brightness",
            "settings", "control", "system", "computer", "shutdown",
            "chrome", "browser", "vscode", "notepad",
        ],
        "examples": [
            "Open Chrome",
            "Open Chrome browser",
            "Launch VS Code",
            "Close this window",
            "Turn up the volume",
            "Change brightness",
            "Open the browser",
            "Start the application",
            "Run this program",
            "Launch notepad",
            "Open settings",
            "Close the app",
            "Shut down the computer",
            "Start VS Code",
            "Open file explorer",
        ],
    },
    "conversation": {
        "keywords": [
            "hello", "hi", "hey", "good", "morning", "afternoon",
            "evening", "thanks", "thank", "help", "chat", "talk",
            "how are", "whats up", "nice", "bye", "goodbye",
        ],
        "examples": [
            "Hello!",
            "How are you?",
            "Hello, how are you?",
            "Thanks for your help",
            "Good morning",
            "What can you do?",
            "Hi there",
            "Hey, how's it going?",
            "Good afternoon",
            "Thanks!",
            "Nice to meet you",
            "Goodbye",
            "See you later",
            "What's up?",
            "Hello friend",
        ],
    },
    "math_reasoning": {
        "keywords": [
            "calculate", "compute", "math", "equation", "formula",
            "solve", "number", "add", "subtract", "multiply", "divide",
            "percentage", "average", "sum", "total", "convert", "percent",
        ],
        "examples": [
            "Calculate 15% of 200",
            "Solve this equation",
            "What is 123 times 456?",
            "Convert 5 miles to kilometers",
            "Find the average of these numbers",
            "Calculate this for me",
            "What's 20 percent of 500?",
            "Add these numbers",
            "Solve this math problem",
            "Compute the sum",
            "What is 100 divided by 4?",
            "Calculate the total",
            "Convert celsius to fahrenheit",
            "Multiply 12 by 8",
            "What's the percentage?",
        ],
    },
}


@dataclass
class DetectionResult:
    """Result of task detection."""
    task: str
    confidence: float
    scores: Dict[str, float] = field(default_factory=dict)
    method: str = "tfidf"  # "tfidf", "keyword", "hybrid", "emergent", "fallback"
    is_emergent: bool = False  # True if this is a low-confidence emergent task
    emergent_id: Optional[str] = None  # Unique ID for emergent task adapter
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "confidence": self.confidence,
            "scores": self.scores,
            "method": self.method,
            "is_emergent": self.is_emergent,
            "emergent_id": self.emergent_id,
        }


class TaskDetector:
    """
    Detect task category from user query using TF-IDF + cosine similarity.
    
    Features:
    - TF-IDF vectorization of task examples
    - Keyword matching as fallback
    - Hybrid scoring for better accuracy
    - Trainable with new examples
    
    Usage:
        detector = TaskDetector()
        result = detector.detect("How do I fix this bug?")
        print(f"Task: {result.task}, Confidence: {result.confidence}")
    """
    
    def __init__(
        self,
        threshold: float = TASK_DETECTION_THRESHOLD,
        use_hybrid: bool = True,
    ):
        """
        Initialize task detector.
        
        Args:
            threshold: Minimum confidence to assign a task
            use_hybrid: Use hybrid (TF-IDF + keyword) scoring
        """
        self.threshold = threshold
        self.use_hybrid = use_hybrid
        
        # Build training data from patterns
        self._examples: List[str] = []
        self._labels: List[str] = []
        self._build_training_data()
        
        # Initialize TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=1000,
        )
        
        # Fit vectorizer and create example vectors
        self._fit()
        
        # Keyword patterns for each task
        self._keyword_patterns = self._build_keyword_patterns()
        
        # Stats
        self._total_detections = 0
        self._task_counts: Dict[str, int] = defaultdict(int)
        self._emergent_count = 0
        self._task_correlations: List[Dict] = []  # Track low-confidence correlations
        
        logger.info(
            f"TaskDetector initialized: {len(self._examples)} examples, "
            f"{len(TASK_CATEGORIES)} categories"
        )
    
    # =========================================================================
    # INITIALIZATION
    # =========================================================================
    
    def _build_training_data(self) -> None:
        """Build training data from task patterns."""
        for task, patterns in TASK_PATTERNS.items():
            for example in patterns.get("examples", []):
                self._examples.append(example)
                self._labels.append(task)
    
    def _fit(self) -> None:
        """Fit TF-IDF vectorizer on examples."""
        if not self._examples:
            logger.warning("No examples to fit")
            return
        
        self.vectorizer.fit(self._examples)
        self._example_vectors = self.vectorizer.transform(self._examples)
        
        # Pre-compute task centroids (average vector per task)
        self._task_centroids: Dict[str, np.ndarray] = {}
        for task in TASK_CATEGORIES:
            indices = [i for i, l in enumerate(self._labels) if l == task]
            if indices:
                vectors = self._example_vectors[indices].toarray()
                self._task_centroids[task] = np.mean(vectors, axis=0)
    
    def _build_keyword_patterns(self) -> Dict[str, set]:
        """Build keyword sets for each task."""
        patterns = {}
        for task, data in TASK_PATTERNS.items():
            keywords = data.get("keywords", [])
            patterns[task] = set(kw.lower() for kw in keywords)
        return patterns
    
    # =========================================================================
    # DETECTION
    # =========================================================================
    
    def detect(self, query: str) -> DetectionResult:
        """
        Detect task category for a query.
        
        Enhanced with emergent task handling:
        - When confidence below threshold, flags as emergent
        - Provides unique ID for dynamic adapter creation
        - Logs task correlations for analysis
        
        Args:
            query: User query string
            
        Returns:
            DetectionResult with task, confidence, and emergent flags
        """
        if not query or not query.strip():
            return DetectionResult(
                task="conversation",
                confidence=0.5,
                method="default",
            )
        
        query_lower = query.lower().strip()
        
        # Get TF-IDF scores
        tfidf_scores = self._tfidf_score(query_lower)
        
        # Get keyword scores
        keyword_scores = self._keyword_score(query_lower)
        
        # Combine scores
        if self.use_hybrid:
            scores = self._hybrid_score(tfidf_scores, keyword_scores)
            method = "hybrid"
        else:
            scores = tfidf_scores
            method = "tfidf"
        
        # Get best task
        best_task = max(scores, key=scores.get)
        best_score = scores[best_task]
        
        # Check threshold - handle emergent vs fallback
        is_emergent = False
        emergent_id = None
        
        if best_score < self.threshold:
            # Low confidence: flag as emergent task for potential adapter creation
            self._emergent_count += 1
            is_emergent = True
            emergent_id = f"emergent_{int(time.time())}_{self._emergent_count}"
            method = "emergent"
            
            # Log correlation for analysis
            self._log_task_correlation(query, scores)
            
            logger.info(
                f"Emergent task detected: confidence={best_score:.3f}, "
                f"best_match={best_task}, id={emergent_id}"
            )
            
            # Keep best_task for routing, but flag as emergent
            # Downstream can decide to create new adapter or use best match
        
        # Update stats
        self._total_detections += 1
        self._task_counts[best_task] += 1
        
        return DetectionResult(
            task=best_task,
            confidence=best_score,
            scores=scores,
            method=method,
            is_emergent=is_emergent,
            emergent_id=emergent_id,
        )
    
    def _log_task_correlation(self, query: str, scores: Dict[str, float]) -> None:
        """
        Log task correlations for low-confidence queries.
        
        Useful for:
        - Analyzing which tasks are commonly confused
        - Identifying need for new task categories
        - Fine-tuning thresholds
        """
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        correlation = {
            "timestamp": time.time(),
            "query": query[:200],  # Truncate for storage
            "top_3": sorted_scores[:3],
            "max_score": sorted_scores[0][1] if sorted_scores else 0,
        }
        
        self._task_correlations.append(correlation)
        
        # Keep only last 1000 correlations
        if len(self._task_correlations) > 1000:
            self._task_correlations = self._task_correlations[-1000:]
    
    def _tfidf_score(self, query: str) -> Dict[str, float]:
        """Score query against task centroids using TF-IDF."""
        scores = {}
        
        try:
            query_vector = self.vectorizer.transform([query]).toarray()[0]
            
            for task, centroid in self._task_centroids.items():
                similarity = cosine_similarity(
                    query_vector.reshape(1, -1),
                    centroid.reshape(1, -1)
                )[0][0]
                scores[task] = float(max(0, similarity))
        except Exception as e:
            logger.warning(f"TF-IDF scoring failed: {e}")
            scores = {task: 0.0 for task in TASK_CATEGORIES}
        
        return scores
    
    def _keyword_score(self, query: str) -> Dict[str, float]:
        """Score query based on keyword matches."""
        scores = {}
        query_lower = query.lower()
        words = set(re.findall(r'\w+', query_lower))
        
        for task, keywords in self._keyword_patterns.items():
            matches = 0
            # Check both word matches and phrase matches
            for keyword in keywords:
                if ' ' in keyword:
                    # Multi-word phrase
                    if keyword in query_lower:
                        matches += 2  # Phrase matches worth more
                elif keyword in words:
                    matches += 1
            
            # Normalize by number of keywords
            score = matches / max(len(keywords), 1)
            scores[task] = min(1.0, score * 3)  # Scale up
        
        return scores
    
    def _hybrid_score(
        self,
        tfidf_scores: Dict[str, float],
        keyword_scores: Dict[str, float],
        tfidf_weight: float = 0.3,  # Favor keywords more
    ) -> Dict[str, float]:
        """Combine TF-IDF and keyword scores."""
        scores = {}
        keyword_weight = 1.0 - tfidf_weight
        
        for task in TASK_CATEGORIES:
            tfidf = tfidf_scores.get(task, 0)
            keyword = keyword_scores.get(task, 0)
            scores[task] = (tfidf * tfidf_weight) + (keyword * keyword_weight)
        
        return scores
    
    # =========================================================================
    # TRAINING
    # =========================================================================
    
    def add_example(self, query: str, task: str) -> None:
        """
        Add a new example for a task.
        
        Args:
            query: Example query
            task: Task category
        """
        if task not in TASK_CATEGORIES:
            logger.warning(f"Unknown task: {task}")
            return
        
        self._examples.append(query)
        self._labels.append(task)
        
        # Refit vectorizer
        self._fit()
        
        logger.debug(f"Added example for task '{task}': {query[:50]}...")
    
    def add_examples(self, examples: List[Tuple[str, str]]) -> None:
        """Add multiple examples."""
        for query, task in examples:
            self._examples.append(query)
            self._labels.append(task)
        
        self._fit()
        logger.info(f"Added {len(examples)} examples")
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics including emergent task tracking."""
        return {
            "total_detections": self._total_detections,
            "task_counts": dict(self._task_counts),
            "num_examples": len(self._examples),
            "categories": list(TASK_CATEGORIES),
            "threshold": self.threshold,
            "emergent_count": self._emergent_count,
            "correlation_buffer_size": len(self._task_correlations),
        }
    
    def get_top_tasks(
        self,
        query: str,
        top_k: int = 3,
    ) -> List[Tuple[str, float]]:
        """
        Get top k task predictions for a query.
        
        Args:
            query: User query
            top_k: Number of tasks to return
            
        Returns:
            List of (task, score) tuples
        """
        result = self.detect(query)
        sorted_tasks = sorted(
            result.scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_tasks[:top_k]
    
    def __repr__(self) -> str:
        return (
            f"TaskDetector(examples={len(self._examples)}, "
            f"detections={self._total_detections})"
        )


# =============================================================================
# SINGLETON
# =============================================================================

_detector_instance: Optional[TaskDetector] = None


def get_detector() -> TaskDetector:
    """Get or create the global task detector."""
    global _detector_instance
    
    if _detector_instance is None:
        _detector_instance = TaskDetector()
    
    return _detector_instance
