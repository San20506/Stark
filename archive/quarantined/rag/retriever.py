"""
STARK RAG - Retriever
=====================
Semantic search and document retrieval.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from rag.document_indexer import get_indexer

logger = logging.getLogger(__name__)


@dataclass
class RetrievedDocument:
    """A retrieved document with relevance score."""
    text: str
    source: str
    score: float
    metadata: Dict
    
    def __repr__(self) -> str:
        return f"<Doc: {self.source[:50]}... (score={self.score:.3f})>"


class DocumentRetriever:
    """
    Retrieve relevant documents using semantic search.
    
    Features:
    - Top-K retrieval
    - Similarity threshold filtering
    - Source deduplication
    """
    
    def __init__(self, indexer=None):
        """
        Initialize retriever.
        
        Args:
            indexer: DocumentIndexer instance (uses singleton if None)
        """
        self.indexer = indexer or get_indexer()
        self._queries_processed = 0
        
        logger.info("DocumentRetriever initialized")
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
        deduplicate: bool = True,
    ) -> List[RetrievedDocument]:
        """
        Search for relevant documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1)
            deduplicate: Remove duplicate sources
            
        Returns:
            List of RetrievedDocument objects
        """
        self._queries_processed += 1
        
        try:
            # Generate query embedding
            query_embedding = self.indexer.embedding_model.encode([query])[0].tolist()
            
            # Search collection
            results = self.indexer.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2 if deduplicate else top_k,  # Get more for dedup
            )
            
            # Parse results
            documents = []
            seen_sources = set()
            
            for i in range(len(results['ids'][0])):
                doc_id = results['ids'][0][i]
                text = results['documents'][0][i]
                distance = results['distances'][0][i]
                metadata = results['metadatas'][0][i]
                
                # Convert distance to similarity score (cosine distance → similarity)
                score = 1.0 - distance
                
                # Filter by score
                if score < min_score:
                    continue
                
                # Deduplicate by source
                source = metadata.get('source', 'unknown')
                if deduplicate and source in seen_sources:
                    continue
                
                seen_sources.add(source)
                
                documents.append(RetrievedDocument(
                    text=text,
                    source=source,
                    score=score,
                    metadata=metadata,
                ))
                
                # Stop if we have enough
                if len(documents) >= top_k:
                    break
            
            logger.debug(f"Retrieved {len(documents)} documents for query: {query[:50]}")
            return documents
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_context(
        self,
        query: str,
        top_k: int = 3,
        max_context_length: int = 2000,
    ) -> str:
        """
        Get formatted context for LLM prompt.
        
        Args:
            query: Search query
            top_k: Number of documents
            max_context_length: Max total context length
            
        Returns:
            Formatted context string
        """
        documents = self.search(query, top_k=top_k)
        
        if not documents:
            return ""
        
        # Format context
        context_parts = ["# RELEVANT CONTEXT\n"]
        current_length = len(context_parts[0])
        
        for i, doc in enumerate(documents, 1):
            header = f"\n## Source {i}: {doc.source}\n"
            content = doc.text[:500] + "..." if len(doc.text) > 500 else doc.text
            
            section = header + content + "\n"
            
            # Check length
            if current_length + len(section) > max_context_length:
                break
            
            context_parts.append(section)
            current_length += len(section)
        
        return ''.join(context_parts)
    
    def get_stats(self) -> Dict:
        """Get retriever statistics."""
        return {
            "queries_processed": self._queries_processed,
            "indexed_chunks": self.indexer.collection.count(),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_retriever_instance: Optional[DocumentRetriever] = None


def get_retriever() -> DocumentRetriever:
    """Get or create the global document retriever."""
    global _retriever_instance
    
    if _retriever_instance is None:
        _retriever_instance = DocumentRetriever()
    
    return _retriever_instance
