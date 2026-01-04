"""
Neuromorphic Memory - Memory Node
=================================
Data structure for individual memory nodes with synaptic properties.

Part of Module 3 - Neuromorphic Memory
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np


@dataclass
class MemoryNode:
    """
    A single memory node in the neuromorphic network.
    
    Represents one stored experience with:
    - Content: The actual query/response data
    - Embedding: Vector representation for similarity
    - Activation: Current activation level (decays over time)
    - Connections: Synaptic links to related memories
    
    Attributes:
        node_id: Unique identifier for this node
        query: The user query that created this memory
        response: The system response
        task: Task category (e.g., "error_debugging")
        embedding: Vector embedding of the content
        activation: Current activation level [0, 1]
        decay_rate: How fast this memory decays per hour
        access_count: Number of times this memory was retrieved
        connections: Dict of connected node_ids -> weights
        created_at: Unix timestamp of creation
        last_accessed: Unix timestamp of last access
        importance: Computed importance score
        metadata: Additional context
    """
    
    # Core content
    query: str
    response: str
    task: str
    embedding: np.ndarray
    
    # Neuromorphic properties
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    activation: float = 1.0
    decay_rate: float = 0.05  # Default decay per hour
    access_count: int = 0
    connections: Dict[str, float] = field(default_factory=dict)
    
    # Timestamps
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    
    # Derived properties
    importance: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure embedding is numpy array."""
        if not isinstance(self.embedding, np.ndarray):
            self.embedding = np.array(self.embedding)
    
    def activate(self, amount: float = 0.5) -> float:
        """
        Increase activation level and update access stats.
        
        Args:
            amount: How much to increase activation
            
        Returns:
            New activation level
        """
        self.activation = min(1.0, self.activation + amount)
        self.access_count += 1
        self.last_accessed = time.time()
        
        # Update importance based on access pattern
        self._update_importance()
        
        return self.activation
    
    def decay(self, hours_elapsed: float) -> float:
        """
        Apply time-based decay to activation.
        
        Args:
            hours_elapsed: Time since last decay calculation
            
        Returns:
            New activation level
        """
        decay_amount = self.decay_rate * hours_elapsed
        self.activation = max(0.0, self.activation - decay_amount)
        return self.activation
    
    def add_connection(self, target_id: str, weight: float) -> None:
        """
        Create or strengthen connection to another node.
        
        Args:
            target_id: ID of the target node
            weight: Connection weight [0, 1]
        """
        from core.constants import CONNECTION_MAX_WEIGHT
        
        if target_id in self.connections:
            # Strengthen existing connection
            self.connections[target_id] = min(
                CONNECTION_MAX_WEIGHT,
                self.connections[target_id] + weight * 0.1
            )
        else:
            # Create new connection
            self.connections[target_id] = min(CONNECTION_MAX_WEIGHT, weight)
    
    def weaken_connection(self, target_id: str, amount: float = 0.1) -> bool:
        """
        Weaken a connection (Hebbian unlearning).
        
        Args:
            target_id: ID of target node
            amount: How much to weaken
            
        Returns:
            True if connection still exists, False if pruned
        """
        from core.constants import CONNECTION_PRUNE_THRESHOLD
        
        if target_id not in self.connections:
            return False
            
        self.connections[target_id] -= amount
        
        if self.connections[target_id] < CONNECTION_PRUNE_THRESHOLD:
            del self.connections[target_id]
            return False
            
        return True
    
    def consolidate(self) -> None:
        """
        Consolidate memory - reduce decay rate for important memories.
        
        Called when memory is accessed multiple times.
        """
        from core.constants import (
            CONSOLIDATION_ACCESS_COUNT,
            CONSOLIDATION_DECAY_REDUCTION
        )
        
        if self.access_count >= CONSOLIDATION_ACCESS_COUNT:
            self.decay_rate *= CONSOLIDATION_DECAY_REDUCTION
            self.importance = min(1.0, self.importance + 0.2)
    
    def _update_importance(self) -> None:
        """Update importance score based on access patterns."""
        # Recency factor (higher if accessed recently)
        hours_since_access = (time.time() - self.last_accessed) / 3600
        recency = max(0.0, 1.0 - hours_since_access * 0.1)
        
        # Frequency factor (higher if accessed often)
        frequency = min(1.0, self.access_count / 10.0)
        
        # Combined importance
        self.importance = 0.4 * recency + 0.4 * frequency + 0.2 * self.activation
    
    def spread_activation(self) -> Dict[str, float]:
        """
        Calculate activation to spread to connected nodes.
        
        Returns:
            Dict of node_id -> activation amount to spread
        """
        from core.constants import ACTIVATION_SPREAD_FACTOR
        
        spread = {}
        for target_id, weight in self.connections.items():
            spread[target_id] = self.activation * weight * ACTIVATION_SPREAD_FACTOR
        
        return spread
    
    def is_alive(self) -> bool:
        """Check if memory should still exist."""
        from core.constants import ACTIVATION_THRESHOLD
        return self.activation >= ACTIVATION_THRESHOLD
    
    def similarity(self, other_embedding: np.ndarray) -> float:
        """
        Compute cosine similarity to another embedding.
        
        Args:
            other_embedding: Embedding to compare against
            
        Returns:
            Similarity score [-1, 1]
        """
        norm_self = np.linalg.norm(self.embedding)
        norm_other = np.linalg.norm(other_embedding)
        
        if norm_self == 0 or norm_other == 0:
            return 0.0
            
        return float(np.dot(self.embedding, other_embedding) / (norm_self * norm_other))
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize node for persistence."""
        return {
            "node_id": self.node_id,
            "query": self.query,
            "response": self.response,
            "task": self.task,
            "embedding": self.embedding.tolist(),
            "activation": self.activation,
            "decay_rate": self.decay_rate,
            "access_count": self.access_count,
            "connections": self.connections,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "importance": self.importance,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryNode":
        """Deserialize node from dict."""
        return cls(
            node_id=data["node_id"],
            query=data["query"],
            response=data["response"],
            task=data["task"],
            embedding=np.array(data["embedding"]),
            activation=data["activation"],
            decay_rate=data["decay_rate"],
            access_count=data["access_count"],
            connections=data["connections"],
            created_at=data["created_at"],
            last_accessed=data["last_accessed"],
            importance=data["importance"],
            metadata=data.get("metadata", {}),
        )
    
    def __repr__(self) -> str:
        return (
            f"MemoryNode(id={self.node_id}, task={self.task}, "
            f"activation={self.activation:.2f}, connections={len(self.connections)})"
        )
