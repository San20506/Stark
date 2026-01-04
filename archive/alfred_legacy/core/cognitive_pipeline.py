"""
ALFRED Cognitive Pipeline
2-Step Workflow: Intent Classification → Memory Recall

Step 1: FastNLU - Understand WHAT the user wants (sub-10ms)
Step 2: Memory  - Recall relevant context (sub-50ms)

Total latency target: <60ms
"""

import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger("CognitivePipeline")


@dataclass
class CognitiveResult:
    """Result from the 2-step cognitive pipeline."""
    # Step 1: Intent
    intent: str
    intent_confidence: float
    intent_method: str  # "semantic", "fallback", "unknown"
    
    # Step 2: Memory
    context: str
    related_memories: list
    
    # Metadata
    raw_query: str
    total_latency_ms: float
    step1_latency_ms: float
    step2_latency_ms: float


class CognitivePipeline:
    """
    ALFRED's 2-Step Cognitive Pipeline.
    
    Combines:
    - FastNLU: Ultra-fast semantic intent classification
    - NeuromorphicMemory: 3-tier context retrieval
    
    Usage:
        pipeline = CognitivePipeline()
        result = pipeline.process("What's the weather in Tokyo?")
        print(f"Intent: {result.intent}")
        print(f"Context: {result.context}")
    """
    
    def __init__(self):
        self.fast_nlu = None
        self.memory = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Lazy initialization of components."""
        if self._initialized:
            return True
        
        start = time.time()
        
        # Step 1: Load FastNLU
        try:
            from core.fast_nlu import get_fast_nlu
            self.fast_nlu = get_fast_nlu()
            logger.info("✅ FastNLU loaded")
        except Exception as e:
            logger.error(f"FastNLU failed: {e}")
            return False
        
        # Step 2: Load Neuromorphic Memory
        try:
            from memory.neuromorphic_memory import get_neuromorphic_memory
            self.memory = get_neuromorphic_memory()
            logger.info("✅ NeuromorphicMemory loaded")
        except Exception as e:
            logger.error(f"Memory failed: {e}")
            return False
        
        load_time = (time.time() - start) * 1000
        logger.info(f"🧠 Cognitive Pipeline ready ({load_time:.0f}ms)")
        
        self._initialized = True
        return True
    
    def process(self, query: str) -> CognitiveResult:
        """
        Process query through 2-step workflow.
        
        Step 1: Intent Classification (FastNLU)
        Step 2: Memory Recall (Neuromorphic)
        
        Args:
            query: User's natural language query
            
        Returns:
            CognitiveResult with intent and context
        """
        if not self._initialized:
            self.initialize()
        
        total_start = time.time()
        
        # ═══════════════════════════════════════════════════════════
        # STEP 1: Intent Classification (Target: <10ms)
        # ═══════════════════════════════════════════════════════════
        step1_start = time.time()
        
        nlu_result = self.fast_nlu.classify(query)
        
        step1_time = (time.time() - step1_start) * 1000
        
        logger.debug(f"Step 1: {nlu_result.intent} ({nlu_result.confidence:.0%}) [{step1_time:.1f}ms]")
        
        # ═══════════════════════════════════════════════════════════
        # STEP 2: Memory Recall (Target: <50ms)
        # ═══════════════════════════════════════════════════════════
        step2_start = time.time()
        
        # Unified recall from all memory tiers
        recall = self.memory.recall(query, top_k=3)
        
        # Build context string
        context_parts = []
        
        # HOT: Recent conversation
        if recall.get("hot_context"):
            hot_items = recall["hot_context"]
            if hot_items:
                context_parts.append("Recent:\n" + "\n".join(hot_items[:3]))
        
        # SEMANTIC: Related memories
        if recall.get("semantic_related"):
            related = recall["semantic_related"]
            if related:
                rel_strs = [f"- {m['user']}: {m['assistant']}" for m in related[:2]]
                context_parts.append("Related:\n" + "\n".join(rel_strs))
        
        # COLD: Historical if triggered
        if recall.get("cold_matches"):
            cold = recall["cold_matches"]
            if cold:
                cold_strs = [f"- {m['content']}" for m in cold[:2]]
                context_parts.append("Archives:\n" + "\n".join(cold_strs))
        
        context = "\n\n".join(context_parts) if context_parts else ""
        
        step2_time = (time.time() - step2_start) * 1000
        
        logger.debug(f"Step 2: Context ({len(context)} chars) [{step2_time:.1f}ms]")
        
        # ═══════════════════════════════════════════════════════════
        # RESULT
        # ═══════════════════════════════════════════════════════════
        total_time = (time.time() - total_start) * 1000
        
        return CognitiveResult(
            intent=nlu_result.intent,
            intent_confidence=nlu_result.confidence,
            intent_method=nlu_result.method,
            context=context,
            related_memories=recall.get("semantic_related", []),
            raw_query=query,
            total_latency_ms=total_time,
            step1_latency_ms=step1_time,
            step2_latency_ms=step2_time
        )
    
    def store_interaction(self, user_query: str, ai_response: str):
        """Store interaction in memory for future recall."""
        if self.memory:
            self.memory.store_interaction(user_query, ai_response)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        stats = {
            "initialized": self._initialized,
            "fast_nlu": self.fast_nlu is not None,
            "memory": self.memory is not None
        }
        
        if self.fast_nlu:
            stats["intents"] = len(self.fast_nlu.intent_library)
        
        if self.memory:
            stats.update(self.memory.get_stats())
        
        return stats


# Singleton
_pipeline = None

def get_cognitive_pipeline() -> CognitivePipeline:
    """Get or create singleton pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = CognitivePipeline()
        _pipeline.initialize()
    return _pipeline


# Quick test
if __name__ == "__main__":
    import sys
    
    print("=" * 70)
    print("   ALFRED Cognitive Pipeline - 2-Step Workflow Test")
    print("=" * 70)
    
    pipeline = CognitivePipeline()
    pipeline.initialize()
    
    test_queries = [
        "What time is it?",
        "What's the weather in Tokyo?",
        "Remind me to call mom",
        "Calculate 25 times 4",
        "Tell me about machine learning",
    ]
    
    print("\n" + "=" * 70)
    print("   Processing Queries")
    print("=" * 70)
    
    for query in test_queries:
        result = pipeline.process(query)
        
        print(f"\n🔹 Query: '{query}'")
        print(f"   Step 1 (Intent):  {result.intent} ({result.intent_confidence:.0%}) [{result.step1_latency_ms:.1f}ms]")
        print(f"   Step 2 (Memory):  {len(result.context)} chars context [{result.step2_latency_ms:.1f}ms]")
        print(f"   Total Latency:    {result.total_latency_ms:.1f}ms")
    
    print("\n" + "=" * 70)
    print("   Pipeline Stats")
    print("=" * 70)
    
    stats = pipeline.get_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    print("\n✅ Pipeline test complete!")
