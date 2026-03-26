"""Tests for memory/knowledge_graph.py — KnowledgeGraph and ConceptNode."""
import threading
import time
import uuid
from typing import List

import numpy as np
import pytest

from memory.knowledge_graph import ConceptNode, KnowledgeGraph
from core.constants import (
    AMEM_LINK_SIMILARITY_THRESH,
    AMEM_PROMOTION_QUORUM,
    AMEM_PROMOTION_SESSION_MIN,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_node(
    *,
    content: str = "test content",
    embedding: np.ndarray = None,
    node_type: str = "episodic",
    access_count: int = 0,
    promotion_count: int = 0,
    metadata: dict = None,
) -> ConceptNode:
    if embedding is None:
        embedding = np.random.rand(8).astype(np.float32)
    return ConceptNode(
        id=str(uuid.uuid4()),
        content=content,
        embedding=embedding,
        node_type=node_type,
        created_at=time.time(),
        access_count=access_count,
        promotion_count=promotion_count,
        metadata=metadata or {},
    )


def _unit_vec(dim: int, index: int) -> np.ndarray:
    """Return a unit vector with 1.0 at *index* and 0.0 elsewhere."""
    v = np.zeros(dim, dtype=np.float32)
    v[index] = 1.0
    return v


# ---------------------------------------------------------------------------
# count / __len__
# ---------------------------------------------------------------------------

def test_add_concept_and_count():
    g = KnowledgeGraph()
    for _ in range(3):
        g.add_concept(_make_node())
    assert g.count() == 3
    assert len(g) == 3


# ---------------------------------------------------------------------------
# Link formation
# ---------------------------------------------------------------------------

def test_link_formation():
    """Two nodes with cosine similarity >= threshold must be linked."""
    g = KnowledgeGraph()
    base = np.ones(8, dtype=np.float32)
    similar = base + np.random.rand(8).astype(np.float32) * 0.01  # nearly identical

    node_a = _make_node(embedding=base.copy())
    node_b = _make_node(embedding=similar.copy())

    g.add_concept(node_a)
    g.add_concept(node_b)

    # Cosine of two nearly-identical vectors is > 0.75
    assert node_b.id in g._adjacency[node_a.id] or node_a.id in g._adjacency[node_b.id]


def test_no_link_dissimilar():
    """Two orthogonal vectors must NOT be linked."""
    g = KnowledgeGraph()
    node_a = _make_node(embedding=_unit_vec(8, 0))
    node_b = _make_node(embedding=_unit_vec(8, 1))

    g.add_concept(node_a)
    g.add_concept(node_b)

    assert node_b.id not in g._adjacency.get(node_a.id, [])
    assert node_a.id not in g._adjacency.get(node_b.id, [])


# ---------------------------------------------------------------------------
# promote()
# ---------------------------------------------------------------------------

def test_promote_success():
    """Node meeting all quorum requirements is promoted to semantic."""
    g = KnowledgeGraph()
    node = _make_node(
        node_type="episodic",
        access_count=AMEM_PROMOTION_QUORUM,
        promotion_count=AMEM_PROMOTION_SESSION_MIN,
    )
    g.add_concept(node)
    result = g.promote(node.id)
    assert result is True
    assert g._nodes[node.id].node_type == "semantic"


def test_promote_fails_low_access():
    """access_count below quorum → promote returns False."""
    g = KnowledgeGraph()
    node = _make_node(
        node_type="episodic",
        access_count=AMEM_PROMOTION_QUORUM - 1,
        promotion_count=AMEM_PROMOTION_SESSION_MIN,
    )
    g.add_concept(node)
    assert g.promote(node.id) is False
    assert g._nodes[node.id].node_type == "episodic"


def test_promote_fails_wrong_type():
    """Node already of type 'semantic' cannot be promoted again."""
    g = KnowledgeGraph()
    node = _make_node(
        node_type="semantic",
        access_count=AMEM_PROMOTION_QUORUM,
        promotion_count=AMEM_PROMOTION_SESSION_MIN,
    )
    g.add_concept(node)
    assert g.promote(node.id) is False


# ---------------------------------------------------------------------------
# query_associative()
# ---------------------------------------------------------------------------

def test_query_associative_empty():
    g = KnowledgeGraph()
    result = g.query_associative(np.ones(8, dtype=np.float32))
    assert result == []


def test_query_associative_returns_sorted():
    """Closest node should appear first in the result."""
    g = KnowledgeGraph()
    query_vec = _unit_vec(8, 0)

    # Node that is perfectly aligned with the query
    best_node = _make_node(embedding=_unit_vec(8, 0).copy())
    # Four nodes that are orthogonal
    for i in range(1, 5):
        g.add_concept(_make_node(embedding=_unit_vec(8, i).copy()))
    g.add_concept(best_node)

    results = g.query_associative(query_vec, top_k=5)
    assert len(results) > 0
    # The top result's node_id must be best_node
    top_id, top_score = results[0]
    assert top_id == best_node.id
    # Scores must be in descending order
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# get_promotable()
# ---------------------------------------------------------------------------

def test_get_promotable():
    """Only episodic nodes meeting both thresholds appear in get_promotable()."""
    g = KnowledgeGraph()

    # Qualifies
    qualifying = _make_node(
        node_type="episodic",
        access_count=AMEM_PROMOTION_QUORUM,
        promotion_count=AMEM_PROMOTION_SESSION_MIN,
    )
    # Low access count — should not qualify
    low_access = _make_node(
        node_type="episodic",
        access_count=AMEM_PROMOTION_QUORUM - 1,
        promotion_count=AMEM_PROMOTION_SESSION_MIN,
    )
    # Low promotion count — should not qualify
    low_promo = _make_node(
        node_type="episodic",
        access_count=AMEM_PROMOTION_QUORUM,
        promotion_count=AMEM_PROMOTION_SESSION_MIN - 1,
    )
    # Already semantic — should not appear
    already_semantic = _make_node(
        node_type="semantic",
        access_count=AMEM_PROMOTION_QUORUM,
        promotion_count=AMEM_PROMOTION_SESSION_MIN,
    )

    for node in (qualifying, low_access, low_promo, already_semantic):
        g.add_concept(node)

    promotable = g.get_promotable()
    assert qualifying.id in promotable
    assert low_access.id not in promotable
    assert low_promo.id not in promotable
    assert already_semantic.id not in promotable


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

def test_thread_safety():
    """Concurrent add_concept from 10 threads → all 10 nodes present."""
    g = KnowledgeGraph()
    nodes: List[ConceptNode] = [_make_node() for _ in range(10)]
    threads = [threading.Thread(target=g.add_concept, args=(n,)) for n in nodes]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert g.count() == 10
    for node in nodes:
        assert node.id in g._nodes
