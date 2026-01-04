#!/usr/bin/env python3
"""
SemanticMemory - Vector database for intelligent context retrieval

Uses ChromaDB and sentence-transformers to enable semantic search across
conversation history, allowing ALFRED to recall relevant information based
on meaning rather than just recency.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger("SemanticMemory")

# Lazy imports to handle missing dependencies gracefully
chromadb = None
SentenceTransformer = None

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    logger.warning("chromadb not installed. Semantic memory disabled.")

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    logger.warning("sentence-transformers not installed. Semantic memory disabled.")


class SemanticMemory:
    """
    Semantic memory system using vector embeddings for intelligent retrieval.
    
    Features:
    - Automatic embedding generation from text
    - Semantic similarity search
    - Persistent vector storage
    - Context-aware retrieval
    """
    
    DEFAULT_CHROMA_DIR = Path.home() / ".alfred" / "chroma_db"
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 80MB, fast, accurate
    COLLECTION_NAME = "conversation_memory"
    
    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize semantic memory system.
        
        Args:
            persist_directory: Directory for ChromaDB storage. If None, uses ~/.alfred/chroma_db
        """
        if chromadb is None or SentenceTransformer is None:
            raise RuntimeError(
                "Semantic memory requires chromadb and sentence-transformers. "
                "Install with: pip install chromadb sentence-transformers"
            )
        
        # Setup persistence directory
        if persist_directory is None:
            persist_directory = str(self.DEFAULT_CHROMA_DIR)
        
        self.persist_dir = Path(persist_directory)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(
                anonymized_telemetry=False,  # Privacy: disable telemetry
                allow_reset=True
            )
        )
        
        # Load embedding model
        logger.info(f"Loading embedding model: {self.EMBEDDING_MODEL}")
        self.embedding_model = SentenceTransformer(self.EMBEDDING_MODEL)
        logger.info(f"✅ Embedding model loaded ({self.embedding_model.get_sentence_embedding_dimension()} dimensions)")
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "ALFRED conversation memory with semantic search"}
        )
        
        logger.info(f"✅ SemanticMemory initialized: {self.persist_dir}")
        logger.info(f"   Collection: {self.COLLECTION_NAME} ({self.collection.count()} embeddings)")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector from text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.exception(f"Failed to generate embedding: {e}")
            return []
    
    def add_exchange(self, user_msg: str, assistant_msg: str, metadata: Optional[Dict] = None):
        """
        Add a conversation exchange to semantic memory.
        
        Args:
            user_msg: User's message
            assistant_msg: Assistant's response
            metadata: Optional metadata (timestamp, tags, etc.)
        """
        try:
            # Combine user and assistant messages for richer context
            combined_text = f"User: {user_msg}\nAssistant: {assistant_msg}"
            
            # Generate embedding
            embedding = self._generate_embedding(combined_text)
            if not embedding:
                logger.warning("Empty embedding generated, skipping")
                return
            
            # Prepare metadata
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "user_message": user_msg,
                "assistant_message": assistant_msg,
                "indexed_at": datetime.now().isoformat()
            })
            
            # Generate unique ID
            doc_id = f"exchange_{int(datetime.now().timestamp() * 1000)}"
            
            # Add to collection
            self.collection.add(
                embeddings=[embedding],
                documents=[combined_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            logger.debug(f"Added exchange to semantic memory: {doc_id}")
            
        except Exception as e:
            logger.exception(f"Failed to add exchange: {e}")
    
    def search_similar(self, query: str, top_k: int = 3, min_similarity: float = 0.5) -> List[Dict[str, str]]:
        """
        Search for semantically similar exchanges.
        
        Args:
            query: Search query
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of similar exchanges with metadata
        """
        try:
            if self.collection.count() == 0:
                logger.debug("Collection is empty, no results")
                return []
            
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            if not query_embedding:
                logger.warning("Could not generate query embedding")
                return []
            
            # Perform similarity search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.collection.count())
            )
            
            # Format results
            similar_exchanges = []
            
            if results and results['metadatas'] and len(results['metadatas'][0]) > 0:
                for i, metadata in enumerate(results['metadatas'][0]):
                    # Calculate similarity score (ChromaDB returns distance, convert to similarity)
                    distance = results['distances'][0][i] if 'distances' in results else 1.0
                    similarity = 1.0 - min(distance, 1.0)  # Convert distance to similarity
                    
                    if similarity >= min_similarity:
                        similar_exchanges.append({
                            "user": metadata.get("user_message", ""),
                            "assistant": metadata.get("assistant_message", ""),
                            "timestamp": metadata.get("timestamp", metadata.get("indexed_at", "")),
                            "similarity": round(similarity, 3)
                        })
            
            logger.debug(f"Found {len(similar_exchanges)} similar exchanges for query: {query[:50]}...")
            return similar_exchanges
            
        except Exception as e:
            logger.exception(f"Semantic search failed: {e}")
            return []
    
    def get_relevant_context(self, query: str, exclude_recent_n: int = 5, top_k: int = 3) -> List[Dict[str, str]]:
        """
        Get semantically relevant context, excluding recent exchanges.
        
        This prevents duplication with recency-based context already in memory.
        
        Args:
            query: Current user query
            exclude_recent_n: Number of recent exchanges to exclude
            top_k: Number of relevant exchanges to return
            
        Returns:
            List of relevant exchanges
        """
        try:
            # Get more results than needed to account for exclusions
            candidate_count = top_k + exclude_recent_n + 5
            
            all_results = self.search_similar(query, top_k=candidate_count, min_similarity=0.6)
            
            # Exclude most recent N exchanges
            # Sort by timestamp descending to identify recent ones
            sorted_results = sorted(
                all_results,
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )
            
            # Skip the most recent N, return the next top_k
            relevant = sorted_results[exclude_recent_n:exclude_recent_n + top_k]
            
            if relevant:
                logger.debug(f"Retrieved {len(relevant)} relevant exchanges (excluded {exclude_recent_n} recent)")
            
            return relevant
            
        except Exception as e:
            logger.exception(f"Failed to get relevant context: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get statistics about the semantic memory."""
        return {
            "total_embeddings": self.collection.count(),
            "embedding_dimensions": self.embedding_model.get_sentence_embedding_dimension(),
            "model": self.EMBEDDING_MODEL,
            "persist_directory": str(self.persist_dir)
        }
    
    def clear(self):
        """Clear all semantic memory (use with caution)."""
        try:
            self.client.delete_collection(self.COLLECTION_NAME)
            self.collection = self.client.create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "ALFRED conversation memory with semantic search"}
            )
            logger.info("Semantic memory cleared")
        except Exception as e:
            logger.exception(f"Failed to clear semantic memory: {e}")


# Note for future enhancements:
# - Add support for multi-query fusion (multiple similar queries)
# - Implement memory decay (older memories have lower weight)
# - Add category/topic clustering
# - Support for image embeddings (CLIP model)
# - User feedback loop to improve relevance
