"""
ALFRED Fast NLU - Ultra-Fast Intent Classification
Uses Sentence Transformers + Semantic Search for sub-10ms latency.

Features:
- No retraining needed - add intents via JSON
- Unknown intent clustering for continuous improvement
- Zero-shot fallback for edge cases
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

# Lazy load to avoid slow imports
_model = None
_intent_embeddings = None


@dataclass
class FastNLUResult:
    """Result from Fast NLU classification."""
    intent: str
    confidence: float
    raw_query: str
    method: str  # "semantic", "zero_shot", "unknown"
    processing_time_ms: float


class FastNLU:
    """
    Ultra-fast intent classifier using Sentence Transformers.
    
    Architecture:
    1. Embed query using MiniLM-L6-v2 (384-dim, ~5ms)
    2. Cosine similarity against intent library (~1ms)
    3. Return best match if confidence > threshold
    4. Log unknown queries for clustering
    """
    
    def __init__(
        self, 
        model_name: str = "all-MiniLM-L6-v2",
        intent_library_path: str = "data/intent_library.json",
        unknown_log_path: str = "data/unknown_queries.json",
        confidence_threshold: float = 0.65
    ):
        """
        Initialize Fast NLU.
        
        Args:
            model_name: Sentence Transformer model name
            intent_library_path: Path to intent examples JSON
            unknown_log_path: Path to log unknown queries
            confidence_threshold: Minimum confidence to accept match
        """
        self.model_name = model_name
        self.intent_library_path = intent_library_path
        self.unknown_log_path = unknown_log_path
        self.confidence_threshold = confidence_threshold
        
        self.model = None
        self.intent_library: Dict[str, List[str]] = {}
        self.intent_embeddings: Dict[str, np.ndarray] = {}
        self.loaded = False
    
    def load(self) -> bool:
        """Load model and intent library."""
        try:
            start = time.time()
            
            # Load Sentence Transformer
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            
            # Load intent library
            if os.path.exists(self.intent_library_path):
                with open(self.intent_library_path, 'r', encoding='utf-8') as f:
                    self.intent_library = json.load(f)
            else:
                logger.warning(f"Intent library not found: {self.intent_library_path}")
                self._create_default_library()
            
            # Pre-compute embeddings for all intents
            self._compute_intent_embeddings()
            
            load_time = (time.time() - start) * 1000
            logger.info(f"✅ FastNLU loaded in {load_time:.0f}ms")
            logger.info(f"   Intents: {len(self.intent_library)}")
            logger.info(f"   Model: {self.model_name}")
            
            self.loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to load FastNLU: {e}")
            return False
    
    def _create_default_library(self):
        """Create default intent library."""
        self.intent_library = {
            # Core utility intents
            "time": [
                "what time is it",
                "current time",
                "tell me the time",
                "what's the time now",
                "time please"
            ],
            "date": [
                "what's the date",
                "today's date",
                "what day is it",
                "current date",
                "what is today"
            ],
            "weather": [
                "what's the weather",
                "weather forecast",
                "is it going to rain",
                "how's the weather in",
                "temperature outside"
            ],
            "calculator": [
                "calculate",
                "what is 5 times 7",
                "solve this math",
                "add 10 and 20",
                "divide 100 by 5"
            ],
            "alarm": [
                "set an alarm",
                "wake me up at",
                "alarm for 7am",
                "set timer for",
                "remind me in 5 minutes"
            ],
            "reminder": [
                "remind me to",
                "set a reminder",
                "don't let me forget",
                "remember to",
                "create reminder"
            ],
            "search_web": [
                "search for",
                "google",
                "look up",
                "find information about",
                "search the web for"
            ],
            "open_app": [
                "open",
                "launch",
                "start",
                "run application",
                "open program"
            ],
            "greeting": [
                "hello",
                "hi",
                "hey there",
                "good morning",
                "good afternoon"
            ],
            "goodbye": [
                "goodbye",
                "bye",
                "see you later",
                "talk to you later",
                "exit"
            ],
            "thank_you": [
                "thank you",
                "thanks",
                "appreciate it",
                "thanks a lot",
                "thank you so much"
            ],
            "general_conversation": [
                "how are you",
                "tell me a joke",
                "what can you do",
                "help me",
                "I have a question"
            ]
        }
        
        # Save default library
        os.makedirs(os.path.dirname(self.intent_library_path), exist_ok=True)
        with open(self.intent_library_path, 'w', encoding='utf-8') as f:
            json.dump(self.intent_library, f, indent=2)
        
        logger.info(f"Created default intent library with {len(self.intent_library)} intents")
    
    def _compute_intent_embeddings(self):
        """Pre-compute embeddings for all intent examples."""
        self.intent_embeddings = {}
        
        for intent, examples in self.intent_library.items():
            embeddings = self.model.encode(examples, convert_to_numpy=True)
            # Average embedding for the intent
            self.intent_embeddings[intent] = np.mean(embeddings, axis=0)
    
    def classify(self, query: str) -> FastNLUResult:
        """
        Classify query intent.
        
        Args:
            query: User query string
            
        Returns:
            FastNLUResult with intent and confidence
        """
        start = time.time()
        
        if not self.loaded:
            self.load()
        
        # Embed query
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        
        # Find best matching intent using cosine similarity
        best_intent = None
        best_score = -1
        
        for intent, intent_embedding in self.intent_embeddings.items():
            score = self._cosine_similarity(query_embedding, intent_embedding)
            if score > best_score:
                best_score = score
                best_intent = intent
        
        processing_time = (time.time() - start) * 1000
        
        # Check confidence threshold
        if best_score >= self.confidence_threshold:
            return FastNLUResult(
                intent=best_intent,
                confidence=float(best_score),
                raw_query=query,
                method="semantic",
                processing_time_ms=processing_time
            )
        
        # Low confidence - log as unknown
        self._log_unknown_query(query, best_intent, best_score)
        
        return FastNLUResult(
            intent="unknown",
            confidence=float(best_score),
            raw_query=query,
            method="unknown",
            processing_time_ms=processing_time
        )
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    def _log_unknown_query(self, query: str, closest_intent: str, score: float):
        """Log unknown query for later clustering."""
        try:
            # Load existing unknown queries
            unknown_queries = []
            if os.path.exists(self.unknown_log_path):
                with open(self.unknown_log_path, 'r', encoding='utf-8') as f:
                    unknown_queries = json.load(f)
            
            # Add new query
            unknown_queries.append({
                "query": query,
                "closest_intent": closest_intent,
                "score": score,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep only last 1000 queries
            if len(unknown_queries) > 1000:
                unknown_queries = unknown_queries[-1000:]
            
            # Save
            os.makedirs(os.path.dirname(self.unknown_log_path), exist_ok=True)
            with open(self.unknown_log_path, 'w', encoding='utf-8') as f:
                json.dump(unknown_queries, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to log unknown query: {e}")
    
    def add_intent(self, intent_name: str, examples: List[str]):
        """
        Add a new intent dynamically.
        
        Args:
            intent_name: Name of the intent
            examples: List of example queries
        """
        self.intent_library[intent_name] = examples
        
        # Compute embedding for new intent
        embeddings = self.model.encode(examples, convert_to_numpy=True)
        self.intent_embeddings[intent_name] = np.mean(embeddings, axis=0)
        
        # Save updated library
        with open(self.intent_library_path, 'w', encoding='utf-8') as f:
            json.dump(self.intent_library, f, indent=2)
        
        logger.info(f"Added intent '{intent_name}' with {len(examples)} examples")
    
    def add_example(self, intent_name: str, example: str):
        """Add a single example to an existing intent."""
        if intent_name not in self.intent_library:
            self.intent_library[intent_name] = []
        
        self.intent_library[intent_name].append(example)
        
        # Recompute embedding for this intent
        embeddings = self.model.encode(self.intent_library[intent_name], convert_to_numpy=True)
        self.intent_embeddings[intent_name] = np.mean(embeddings, axis=0)
        
        # Save
        with open(self.intent_library_path, 'w', encoding='utf-8') as f:
            json.dump(self.intent_library, f, indent=2)
    
    def get_unknown_queries(self) -> List[Dict]:
        """Get logged unknown queries for review."""
        if os.path.exists(self.unknown_log_path):
            with open(self.unknown_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def cluster_unknown_queries(self) -> Dict[str, List[str]]:
        """
        Cluster unknown queries to discover new intents.
        Uses K-means on embeddings.
        
        Returns:
            Dict mapping cluster ID to list of queries
        """
        unknown_queries = self.get_unknown_queries()
        
        if len(unknown_queries) < 10:
            return {"message": "Not enough unknown queries for clustering (need 10+)"}
        
        try:
            from sklearn.cluster import KMeans
            
            # Get query texts
            queries = [q["query"] for q in unknown_queries]
            
            # Embed all queries
            embeddings = self.model.encode(queries, convert_to_numpy=True)
            
            # Determine number of clusters (1 per 20 queries, max 10)
            n_clusters = min(10, max(2, len(queries) // 20))
            
            # Cluster
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)
            
            # Group queries by cluster
            clusters = {}
            for i, label in enumerate(labels):
                cluster_name = f"cluster_{label}"
                if cluster_name not in clusters:
                    clusters[cluster_name] = []
                clusters[cluster_name].append(queries[i])
            
            return clusters
            
        except ImportError:
            return {"error": "sklearn not installed. Run: pip install scikit-learn"}
        except Exception as e:
            return {"error": str(e)}
    
    def suggest_new_intents(self) -> List[Dict[str, Any]]:
        """
        Analyze unknown queries and suggest new intents.
        Call this weekly to improve coverage.
        
        Returns:
            List of suggested intents with example queries
        """
        clusters = self.cluster_unknown_queries()
        
        if "error" in clusters or "message" in clusters:
            return [clusters]
        
        suggestions = []
        for cluster_name, queries in clusters.items():
            if len(queries) >= 3:  # Only suggest if 3+ similar queries
                suggestions.append({
                    "suggested_intent": f"new_intent_{cluster_name}",
                    "example_queries": queries[:10],
                    "count": len(queries),
                    "action": f"Review and name this intent, then call: fast_nlu.add_intent('your_intent_name', {queries[:5]})"
                })
        
        return suggestions


# Singleton instance
_fast_nlu = None

def get_fast_nlu() -> FastNLU:
    """Get or create FastNLU singleton."""
    global _fast_nlu
    if _fast_nlu is None:
        _fast_nlu = FastNLU()
        _fast_nlu.load()
    return _fast_nlu


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("FastNLU - Ultra-Fast Intent Classification")
    print("=" * 60)
    
    nlu = FastNLU()
    nlu.load()
    
    test_queries = [
        "what time is it",
        "what's the weather in Tokyo",
        "calculate 5 times 7",
        "set an alarm for 7am",
        "remind me to call mom",
        "open notepad",
        "hello there",
        "search for python tutorials",
        "what's the date today",
        "some random gibberish query that makes no sense"
    ]
    
    print("\nTesting queries:")
    print("-" * 60)
    
    total_time = 0
    for query in test_queries:
        result = nlu.classify(query)
        total_time += result.processing_time_ms
        status = "OK" if result.confidence >= 0.65 else "LOW"
        print(f"[{status}] {query[:35]:35} -> {result.intent:20} ({result.confidence:.0%}) [{result.processing_time_ms:.1f}ms]")
    
    avg_time = total_time / len(test_queries)
    print("-" * 60)
    print(f"Average processing time: {avg_time:.1f}ms")
    print(f"Total intents: {len(nlu.intent_library)}")
