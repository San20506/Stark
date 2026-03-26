import math
import random
import time
from typing import Dict, List, Optional

import numpy as np

from core.constants import (
    ACTIR_ACTIVATION_CEILING,
    ACTIR_ACTIVATION_FLOOR,
    ACTIR_DECAY_RATE,
    ACTIR_NOISE_STD,
    EPISODE_RETRIEVAL_SEM_WEIGHT,
    EPISODE_RETRIEVAL_TEMP_WEIGHT,
)


class ActivationScorer:
    """
    ACT-R based memory activation and retrieval scorer.

    Computes activation based on:
    - Base-level activation: log(sum(t_i ^ -d))
    - Contextual matching: W_j * S_ji
    - Stochastic noise: epsilon
    """

    def __init__(
        self,
        decay_rate: float = ACTIR_DECAY_RATE,
        noise_std: float = ACTIR_NOISE_STD,
        floor: float = ACTIR_ACTIVATION_FLOOR,
        ceiling: float = ACTIR_ACTIVATION_CEILING,
    ):
        self.d = decay_rate
        self.s = noise_std
        self.floor = floor
        self.ceiling = ceiling

    def compute_base_level(
        self, access_times: List[float], current_time: Optional[float] = None
    ) -> float:
        """
        Compute base-level activation: B_i = ln(sum_{j=1}^n t_j^{-d})

        Args:
            access_times: List of Unix timestamps when memory was accessed
            current_time: Current Unix timestamp (defaults to time.time())

        Returns:
            Base-level activation score
        """
        if not access_times:
            return self.floor

        now = current_time or time.time()

        deltas = [max(1.0, now - t) for t in access_times]

        summation = sum(math.pow(t, -self.d) for t in deltas)

        # ln(sum)
        activation = math.log(max(summation, 1e-10))

        return max(self.floor, min(self.ceiling, activation))

    def compute_retrieval_score(
        self,
        base_activation: float,
        semantic_similarity: float,
        context_weight_sem: float = EPISODE_RETRIEVAL_SEM_WEIGHT,
        context_weight_temp: float = EPISODE_RETRIEVAL_TEMP_WEIGHT,
        add_noise: bool = True,
    ) -> float:
        """
        Compute final retrieval score: A_i = B_i + sum(W_j * S_ji) + epsilon

        Args:
            base_activation: The computed base-level activation
            semantic_similarity: Cosine similarity [0, 1]
            context_weight_sem: Weight for semantic match
            context_weight_temp: Weight for temporal/base match
            add_noise: Whether to add stochastic noise

        Returns:
            Final activation score
        """
        # Contextual match (spreading activation equivalent)
        # We simplify sum(W_j * S_ji) to a weighted semantic similarity
        match_score = semantic_similarity * context_weight_sem

        # Base activation contribution (weighted by temporal weight)
        temporal_score = base_activation * context_weight_temp

        # Stochastic noise (Logistic distribution approximation via Gumbel or Normal)
        noise = 0.0
        if add_noise and self.s > 0:
            # ACT-R typically uses a logistic distribution noise
            # epsilon ~ Logistic(0, s)
            noise = random.gauss(0, self.s)

        total = temporal_score + match_score + noise

        return total

    def rank_memories(
        self,
        candidates: List[Dict],
        query_embedding: np.ndarray,
        current_time: Optional[float] = None,
    ) -> List[tuple]:
        """
        Rank candidate memories using ACT-R scoring.

        Args:
            candidates: List of dicts with 'id', 'access_times', 'embedding'
            query_embedding: Vector to compare against
            current_time: Reference time for decay

        Returns:
            Sorted list of (node_id, score) tuples
        """
        now = current_time or time.time()
        results = []

        for cand in candidates:
            # 1. Base activation
            base = self.compute_base_level(cand.get("access_times", []), now)

            # 2. Semantic similarity
            node_emb = cand.get("embedding")
            if node_emb is None:
                sim = 0.0
            else:
                # Assuming node_emb is already a numpy array
                norm_c = np.linalg.norm(node_emb)
                norm_q = np.linalg.norm(query_embedding)
                if norm_c == 0 or norm_q == 0:
                    sim = 0.0
                else:
                    sim = float(np.dot(node_emb, query_embedding) / (norm_c * norm_q))

            # 3. Final score
            score = self.compute_retrieval_score(base, (sim + 1.0) / 2.0)
            results.append((cand["id"], score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results
