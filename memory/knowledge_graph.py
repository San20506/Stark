import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from core.constants import (
    AMEM_LINK_SIMILARITY_THRESH,
    AMEM_PROMOTION_QUORUM,
    AMEM_PROMOTION_SESSION_MIN,
)


@dataclass(frozen=True)
class ConceptNode:
    id: str
    content: str
    embedding: np.ndarray
    node_type: str
    created_at: float
    access_count: int
    promotion_count: int
    metadata: Dict[str, Any]

    def __post_init__(self):
        if not isinstance(self.embedding, np.ndarray):
            object.__setattr__(self, "embedding", np.array(self.embedding))


class KnowledgeGraph:
    def __init__(self):
        self._nodes: Dict[str, ConceptNode] = {}
        self._adjacency: Dict[str, List[str]] = {}
        self._reverse_adj: Dict[str, Dict[str, float]] = {}
        self._lock = threading.RLock()

    def add_concept(self, node: ConceptNode) -> None:
        with self._lock:
            self._nodes[node.id] = node
            self._adjacency[node.id] = []

            for existing_id, existing_node in self._nodes.items():
                if existing_id == node.id:
                    continue
                sim = self._compute_similarity(node.embedding, existing_node.embedding)
                if sim >= AMEM_LINK_SIMILARITY_THRESH:
                    self._adjacency[node.id].append(existing_id)
                    if existing_id not in self._reverse_adj:
                        self._reverse_adj[existing_id] = {}
                    self._reverse_adj[existing_id][node.id] = sim

                    self._adjacency[existing_id].append(node.id)
                    if node.id not in self._reverse_adj:
                        self._reverse_adj[node.id] = {}
                    self._reverse_adj[node.id][existing_id] = sim

    def promote(self, node_id: str) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return False
            if node.node_type != "episodic":
                return False
            if node.access_count < AMEM_PROMOTION_QUORUM:
                return False
            if node.promotion_count < AMEM_PROMOTION_SESSION_MIN:
                return False

            promoted_node = ConceptNode(
                id=node.id,
                content=node.content,
                embedding=node.embedding,
                node_type="semantic",
                created_at=node.created_at,
                access_count=node.access_count,
                promotion_count=node.promotion_count,
                metadata=node.metadata,
            )
            self._nodes[node_id] = promoted_node
            return True

    def query_associative(
        self, embedding: np.ndarray, top_k: int = 5
    ) -> List[Tuple[str, float]]:
        with self._lock:
            if not self._nodes:
                return []

            scored: List[Tuple[str, float]] = []
            for node_id, node in self._nodes.items():
                sim = self._compute_similarity(embedding, node.embedding)
                visited: set = set()
                queue: List[Tuple[str, float]] = [(node_id, sim)]
                visited.add(node_id)

                while queue:
                    current_id, current_sim = queue.pop(0)
                    if current_id in self._adjacency:
                        for neighbor_id in self._adjacency[current_id]:
                            if neighbor_id not in visited:
                                visited.add(neighbor_id)
                                neighbor_node = self._nodes.get(neighbor_id)
                                if neighbor_node:
                                    neighbor_sim = self._compute_similarity(
                                        embedding, neighbor_node.embedding
                                    )
                                    boosted_sim = current_sim * 0.7 + neighbor_sim * 0.3
                                    queue.append((neighbor_id, boosted_sim))

                best_score = 0.0
                for vid in visited:
                    n = self._nodes.get(vid)
                    if n:
                        s = self._compute_similarity(embedding, n.embedding)
                        if s > best_score:
                            best_score = s
                scored.append((node_id, best_score))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]

    def get_promotable(self) -> List[str]:
        with self._lock:
            promotable: List[str] = []
            for node_id, node in self._nodes.items():
                if node.node_type == "episodic":
                    if node.access_count >= AMEM_PROMOTION_QUORUM:
                        if node.promotion_count >= AMEM_PROMOTION_SESSION_MIN:
                            promotable.append(node_id)
            return promotable

    def count(self) -> int:
        return len(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)

    def _compute_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
