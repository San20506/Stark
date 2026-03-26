import numpy as np
import pytest
from memory.activation_scorer import ActivationScorer


def test_base_level_decay_over_time():
    scorer = ActivationScorer(decay_rate=0.5)
    t1 = 1000.0
    t2 = 2000.0

    # Same access times, but current_time shifts forward
    score_early = scorer.compute_base_level([t1, t2], current_time=2001.0)
    score_late = scorer.compute_base_level([t1, t2], current_time=2010.0)

    assert score_late < score_early


def test_base_level_increases_with_frequency():
    scorer = ActivationScorer(decay_rate=0.5)
    now = 1201.0

    score_1 = scorer.compute_base_level([1200.0], current_time=now)
    score_2 = scorer.compute_base_level([1100.0, 1150.0, 1200.0], current_time=now)

    assert score_2 > score_1


def test_retrieval_score_combines_factors():
    scorer = ActivationScorer(noise_std=0.0)  # No noise for deterministic test

    # High base, low semantic
    s1 = scorer.compute_retrieval_score(base_activation=2.0, semantic_similarity=0.1)
    # Low base, high semantic
    s2 = scorer.compute_retrieval_score(base_activation=0.1, semantic_similarity=0.9)

    assert s1 != s2


def test_rank_memories_ordering():
    scorer = ActivationScorer(noise_std=0.0)
    query_emb = np.array([1.0, 0.0])

    candidates = [
        {"id": "low_sim", "access_times": [1000.0], "embedding": np.array([0.0, 1.0])},
        {"id": "high_sim", "access_times": [1000.0], "embedding": np.array([1.0, 0.0])},
    ]

    results = scorer.rank_memories(candidates, query_emb, current_time=1100.0)

    assert results[0][0] == "high_sim"
    assert results[0][1] > results[1][1]
