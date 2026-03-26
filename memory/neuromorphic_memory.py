"""
Neuromorphic Memory - Main Implementation
==========================================
Brain-inspired distributed memory with synaptic connections,
activation spreading, and natural decay.

Module 3 - Neuromorphic Memory
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

import numpy as np
from sentence_transformers import SentenceTransformer

from memory.memory_node import MemoryNode
from memory.episodic_schema import ensure_episodic_schema
from memory.diary_store import DiaryEntry, DiaryStore
from memory.activation_scorer import ActivationScorer
from memory.episode_manager import EpisodeManager
from core.constants import (
    MEMORY_MAX_NODES,
    MEMORY_RAM_LIMIT_GB,
    ACTIVATION_INITIAL,
    ACTIVATION_THRESHOLD,
    ACTIVATION_SPREAD_FACTOR,
    CONNECTION_SIMILARITY_THRESHOLD,
    CONNECTION_HEBBIAN_RATE,
    GC_INTERVAL_SECONDS,
    GC_BATCH_SIZE,
    PROJECT_ROOT,
    MEMORY_V2_ENABLED,
)

logger = logging.getLogger(__name__)


class NeuromorphicMemory:
    """
    Distributed neuromorphic memory system with:
    - Synaptic connections between related memories
    - Activation spreading for associative recall
    - Natural decay for forgetting unimportant memories
    - Hebbian learning to strengthen used pathways
    - Task-based clustering for efficient retrieval

    Usage:
        memory = NeuromorphicMemory()
        memory.store("how to fix null error?", "Check for None before accessing", "error_debugging")
        results = memory.recall("null pointer exception")
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        persist_path: Optional[Path] = None,
        lazy_load: bool = True,
    ):
        """
        Initialize neuromorphic memory.

        Args:
            model_name: Sentence transformer model for embeddings
            persist_path: Path to save/load memory state
            lazy_load: If True, defer embedding model loading
        """
        self.model_name = model_name
        self.persist_path = persist_path or (PROJECT_ROOT / "data" / "memory.json")
        self.episodic_db_path = ensure_episodic_schema()
        self.diary_store = DiaryStore(db_path=self.episodic_db_path)
        self.scorer = ActivationScorer()
        self.episode_manager = EpisodeManager()

        # Memory storage
        self.nodes: Dict[str, MemoryNode] = {}
        self.task_hubs: Dict[str, str] = {}  # task -> hub node id

        # Indices for fast lookup
        self._task_index: Dict[str, List[str]] = defaultdict(list)

        # Embedding model (lazy loaded)
        self._encoder: Optional[SentenceTransformer] = None
        if not lazy_load:
            self._load_encoder()

        # Background GC
        self._gc_lock = threading.RLock()
        self._last_gc = time.time()
        self._last_decay = time.time()

        # Stats
        self._stats = {
            "stores": 0,
            "recalls": 0,
            "gc_runs": 0,
            "pruned_nodes": 0,
        }

        logger.info(f"NeuromorphicMemory initialized (max_nodes={MEMORY_MAX_NODES})")

    # =========================================================================
    # CORE OPERATIONS
    # =========================================================================

    def store(
        self,
        query: str,
        response: str,
        task: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a new memory in the network.

        Args:
            query: User query
            response: System response
            task: Task category
            metadata: Additional context

        Returns:
            Node ID of stored memory
        """
        # Generate embedding
        embedding = self._encode(f"{query} {response}")

        # Create node
        node = MemoryNode(
            query=query,
            response=response,
            task=task,
            embedding=embedding,
            activation=ACTIVATION_INITIAL,
            metadata=metadata or {},
        )

        # Store node
        with self._gc_lock:
            self.nodes[node.node_id] = node
            self._task_index[task].append(node.node_id)

            # Connect to similar existing memories
            self._form_connections(node)

            # Ensure task hub exists
            self._ensure_task_hub(task)

        self._stats["stores"] += 1

        try:
            self.diary_store.write(
                DiaryEntry(
                    content=f"{query}\n{response}",
                    metadata={"task": task, **(metadata or {})},
                )
            )
        except Exception as e:
            logger.warning(f"Diary write failed (non-fatal): {e}")

        logger.debug(f"Stored memory {node.node_id} for task '{task}'")

        # Check if GC needed
        self._maybe_gc()

        return node.node_id

    def recall_v2(
        self,
        query: str,
        task: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Tuple[MemoryNode, float]]:
        if not self.nodes:
            return []

        query_embedding = self._encode(query)
        candidates = []
        node_ids = self._task_index.get(task, []) if task else list(self.nodes.keys())

        for nid in node_ids:
            node = self.nodes.get(nid)
            if node and node.is_alive():
                candidates.append(
                    {
                        "id": nid,
                        "embedding": node.embedding,
                        "access_times": [node.last_accessed],
                    }
                )

        if not candidates:
            return []

        ranked = self.scorer.rank_memories(candidates, query_embedding)

        results = []
        for nid, score in ranked[:top_k]:
            results.append((self.nodes[nid], score))
        return results

    def recall(
        self,
        query: str,
        task: Optional[str] = None,
        top_k: int = 5,
        min_activation: float = 0.0,
    ) -> List[Tuple[MemoryNode, float]]:
        if MEMORY_V2_ENABLED:
            return self.recall_v2(query, task=task, top_k=top_k)

        if not self.nodes:
            return []

        # Apply time-based decay first
        self._apply_decay()

        # Encode query
        query_embedding = self._encode(query)

        # Find matching nodes
        candidates = self._find_similar_nodes(query_embedding, task)

        # Activate matching nodes and spread activation
        activated = self._activate_and_spread(candidates, query_embedding)

        # Filter and sort by relevance
        results = []
        for node_id, score in activated.items():
            node = self.nodes.get(node_id)
            if node and node.activation >= min_activation:
                results.append((node, score))

        results.sort(key=lambda x: x[1], reverse=True)

        self._stats["recalls"] += 1

        return results[:top_k]

    def recall_by_task(self, task: str, top_k: int = 10) -> List[MemoryNode]:
        """
        Recall top memories for a specific task.

        Args:
            task: Task category
            top_k: Maximum results

        Returns:
            List of MemoryNode objects
        """
        node_ids = self._task_index.get(task, [])

        nodes = []
        for nid in node_ids:
            node = self.nodes.get(nid)
            if node and node.is_alive():
                nodes.append(node)

        # Sort by importance
        nodes.sort(key=lambda n: n.importance, reverse=True)

        return nodes[:top_k]

    # =========================================================================
    # ACTIVATION SPREADING
    # =========================================================================

    def _activate_and_spread(
        self, initial_nodes: List[Tuple[str, float]], query_embedding: np.ndarray
    ) -> Dict[str, float]:
        """
        Activate initial nodes and spread activation through network.

        Args:
            initial_nodes: List of (node_id, similarity) to start from
            query_embedding: Query embedding for relevance scoring

        Returns:
            Dict of node_id -> combined relevance score
        """
        relevance: Dict[str, float] = {}

        # Activate initial matches
        for node_id, similarity in initial_nodes:
            node = self.nodes.get(node_id)
            if node:
                node.activate(amount=0.3)
                relevance[node_id] = similarity

        # Spread activation (one hop)
        spread_activation: Dict[str, float] = {}

        for node_id, _ in initial_nodes:
            node = self.nodes.get(node_id)
            if node:
                spread = node.spread_activation()
                for target_id, amount in spread.items():
                    if target_id in self.nodes:
                        spread_activation[target_id] = (
                            spread_activation.get(target_id, 0) + amount
                        )

        # Apply spread activation
        for node_id, amount in spread_activation.items():
            if node_id not in relevance:
                node = self.nodes.get(node_id)
                if node:
                    node.activate(amount=amount)
                    # Calculate relevance based on similarity + spread
                    similarity = node.similarity(query_embedding)
                    relevance[node_id] = similarity * 0.5 + amount * 0.5

        # Hebbian learning - strengthen co-activated connections
        self._hebbian_update(list(relevance.keys()))

        return relevance

    def _hebbian_update(self, activated_nodes: List[str]) -> None:
        """
        Strengthen connections between co-activated nodes (Hebbian learning).

        Args:
            activated_nodes: List of node IDs that were activated together
        """
        for i, node_id in enumerate(activated_nodes):
            node = self.nodes.get(node_id)
            if not node:
                continue

            # Strengthen connections to other activated nodes
            for other_id in activated_nodes[i + 1 :]:
                if other_id in node.connections:
                    node.connections[other_id] = min(
                        1.0, node.connections[other_id] + CONNECTION_HEBBIAN_RATE
                    )

    # =========================================================================
    # CONNECTION FORMATION
    # =========================================================================

    def _form_connections(self, new_node: MemoryNode) -> None:
        """
        Form synaptic connections to similar existing memories.

        Args:
            new_node: Newly stored memory node
        """
        # Find similar nodes
        similar = self._find_similar_nodes(
            new_node.embedding, task=new_node.task, exclude_id=new_node.node_id
        )

        # Create bidirectional connections
        for node_id, similarity in similar[:10]:  # Max 10 connections
            if similarity >= CONNECTION_SIMILARITY_THRESHOLD:
                new_node.add_connection(node_id, similarity)

                # Bidirectional
                other = self.nodes.get(node_id)
                if other:
                    other.add_connection(new_node.node_id, similarity)

    def _find_similar_nodes(
        self,
        embedding: np.ndarray,
        task: Optional[str] = None,
        exclude_id: Optional[str] = None,
    ) -> List[Tuple[str, float]]:
        """
        Find nodes similar to given embedding.

        Args:
            embedding: Query embedding
            task: Optional task filter
            exclude_id: Node ID to exclude

        Returns:
            List of (node_id, similarity) sorted by similarity
        """
        candidates = []

        # Determine which nodes to search
        if task:
            node_ids = self._task_index.get(task, [])
        else:
            node_ids = list(self.nodes.keys())

        for node_id in node_ids:
            if node_id == exclude_id:
                continue

            node = self.nodes.get(node_id)
            if node and node.is_alive():
                similarity = node.similarity(embedding)
                candidates.append((node_id, similarity))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    # =========================================================================
    # TASK HUBS
    # =========================================================================

    def _ensure_task_hub(self, task: str) -> None:
        """Create task hub node if it doesn't exist."""
        if task in self.task_hubs:
            return

        # Create a hub node that connects to all task memories
        hub_embedding = np.zeros(384)  # Placeholder embedding
        hub = MemoryNode(
            query=f"[TASK_HUB:{task}]",
            response="",
            task=task,
            embedding=hub_embedding,
            decay_rate=0.0,  # Hubs don't decay
        )
        hub.importance = 1.0

        self.nodes[hub.node_id] = hub
        self.task_hubs[task] = hub.node_id

    # =========================================================================
    # DECAY & GARBAGE COLLECTION
    # =========================================================================

    def _apply_decay(self) -> None:
        """Apply time-based decay to all nodes."""
        now = time.time()
        hours_elapsed = (now - self._last_decay) / 3600

        if hours_elapsed < 0.1:  # Minimum 6 minutes between decays
            return

        with self._gc_lock:
            for node in self.nodes.values():
                if node.decay_rate > 0:
                    node.decay(hours_elapsed)

            self._last_decay = now

    def _maybe_gc(self) -> None:
        """Run garbage collection if needed."""
        now = time.time()

        # Time-based trigger
        if now - self._last_gc < GC_INTERVAL_SECONDS:
            return

        # Capacity-based trigger
        if len(self.nodes) < MEMORY_MAX_NODES:
            return

        self._run_gc()

    def _run_gc(self) -> None:
        """Remove dead memories and prune weak connections."""
        with self._gc_lock:
            nodes_to_remove = []

            # Find dead nodes
            for node_id, node in self.nodes.items():
                if not node.is_alive() and node.decay_rate > 0:  # Don't remove hubs
                    nodes_to_remove.append(node_id)

                    if len(nodes_to_remove) >= GC_BATCH_SIZE:
                        break

            # Remove dead nodes
            for node_id in nodes_to_remove:
                self._remove_node(node_id)

            self._last_gc = time.time()
            self._stats["gc_runs"] += 1
            self._stats["pruned_nodes"] += len(nodes_to_remove)

            if nodes_to_remove:
                logger.info(f"GC removed {len(nodes_to_remove)} dead memories")

    def _remove_node(self, node_id: str) -> None:
        """Remove a node and clean up references."""
        node = self.nodes.pop(node_id, None)
        if not node:
            return

        # Remove from task index
        if node.task in self._task_index:
            try:
                self._task_index[node.task].remove(node_id)
            except ValueError:
                pass

        # Remove connections from other nodes
        for other in self.nodes.values():
            other.connections.pop(node_id, None)

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def save(self, path: Optional[Path] = None) -> None:
        """Save memory network to disk."""
        save_path = path or self.persist_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with self._gc_lock:
            data = {
                "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
                "task_hubs": self.task_hubs,
                "stats": self._stats,
            }

        # Atomic write
        temp_path = save_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(data, f)
        temp_path.replace(save_path)

        logger.info(f"Saved {len(self.nodes)} memories to {save_path}")

    def load(self, path: Optional[Path] = None) -> bool:
        """
        Load memory network from disk.

        Returns:
            True if loaded successfully
        """
        load_path = path or self.persist_path

        if not load_path.exists():
            logger.info("No saved memory found")
            return False

        try:
            with open(load_path, "r") as f:
                data = json.load(f)

            with self._gc_lock:
                self.nodes = {
                    nid: MemoryNode.from_dict(ndata)
                    for nid, ndata in data["nodes"].items()
                }
                self.task_hubs = data.get("task_hubs", {})
                self._stats = data.get("stats", self._stats)

                # Rebuild task index
                self._task_index.clear()
                for nid, node in self.nodes.items():
                    self._task_index[node.task].append(nid)

            logger.info(f"Loaded {len(self.nodes)} memories from {load_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            return False

    # =========================================================================
    # EMBEDDING
    # =========================================================================

    def _load_encoder(self) -> None:
        """Load the sentence transformer model."""
        if self._encoder is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._encoder = SentenceTransformer(self.model_name)

    def _encode(self, text: str) -> np.ndarray:
        """Encode text to embedding vector."""
        self._load_encoder()
        return self._encoder.encode(text, convert_to_numpy=True)

    # =========================================================================
    # STATS & UTILITIES
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            **self._stats,
            "total_nodes": len(self.nodes),
            "alive_nodes": sum(1 for n in self.nodes.values() if n.is_alive()),
            "task_distribution": {
                task: len(nodes) for task, nodes in self._task_index.items()
            },
            "total_connections": sum(len(n.connections) for n in self.nodes.values()),
        }

    def __len__(self) -> int:
        return len(self.nodes)

    def __repr__(self) -> str:
        return f"NeuromorphicMemory(nodes={len(self.nodes)}, tasks={len(self._task_index)})"


# =============================================================================
# SINGLETON
# =============================================================================

_memory_instance: Optional[NeuromorphicMemory] = None


def get_memory() -> NeuromorphicMemory:
    """Get or create the global memory instance."""
    global _memory_instance

    if _memory_instance is None:
        _memory_instance = NeuromorphicMemory()
        _memory_instance.load()  # Try to load existing

    return _memory_instance
