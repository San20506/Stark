"""
STARK RAG - Document Indexer
=============================
Index documents for semantic search using ChromaDB.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from rag.chunker import DocumentChunker, Chunk

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """
    Index documents using ChromaDB and sentence-transformers.
    
    Features:
    - Incremental indexing (track mtimes)
    - Multiple file types (Python, Markdown, text)
    - Persistent storage
    """
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        '.py': 'python',
        '.md': 'markdown',
        '.txt': 'text',
        '.rst': 'text',
        '.json': 'text',
    }
    
    def __init__(
        self,
        collection_name: str = "stark_docs",
        persist_directory: str = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize document indexer.
        
        Args:
            collection_name: ChromaDB collection name
            persist_directory: Where to store index
            embedding_model: Sentence transformer model
        """
        if persist_directory is None:
            persist_directory = os.path.join(
                os.path.dirname(__file__),
                "../.stark/rag_index"
            )
        
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Chunker
        self.chunker = DocumentChunker(chunk_size=500, chunk_overlap=50)
        
        # Track indexed files
        self._indexed_files: Dict[str, float] ={}  # path -> mtime
        
        logger.info(f"DocumentIndexer initialized (collection: {collection_name})")
    
    def index_directory(
        self,
        directory: str,
        recursive: bool = True,
        extensions: List[str] = None,
    ) -> int:
        """
        Index all documents in a directory.
        
        Args:
            directory: Directory path
            recursive: Search subdirectories
            extensions: File extensions to index (None = all supported)
            
        Returns:
            Number of files indexed
        """
        if extensions is None:
            extensions = list(self.SUPPORTED_EXTENSIONS.keys())
        
        directory = Path(directory)
        files_indexed = 0
        
        # Find files
        if recursive:
            files = []
            for ext in extensions:
                files.extend(directory.rglob(f"*{ext}"))
        else:
            files = []
            for ext in extensions:
                files.extend(directory.glob(f"*{ext}"))
        
        logger.info(f"Found {len(files)} files to index in {directory}")
        
        # Index each file
        for file_path in files:
            try:
                # Check if already indexed and unchanged
                mtime = file_path.stat().st_mtime
                if str(file_path) in self._indexed_files:
                    if self._indexed_files[str(file_path)] >= mtime:
                        continue  # Skip unchanged file
                
                # Index file
                if self.index_file(str(file_path)):
                    files_indexed += 1
                    self._indexed_files[str(file_path)] = mtime
                    
            except Exception as e:
                logger.error(f"Failed to index {file_path}: {e}")
        
        logger.info(f"Indexed {files_indexed} files")
        return files_indexed
    
    def index_file(self, file_path: str) -> bool:
        """
        Index a single file.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if successful
        """
        try:
            # Determine file type
            ext = Path(file_path).suffix.lower()
            file_type = self.SUPPORTED_EXTENSIONS.get(ext, "text")
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Chunk document
            chunks = self.chunker.chunk_document(content, file_path, file_type)
            
            if not chunks:
                return False
            
            # Generate embeddings
            texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_model.encode(texts).tolist()
            
            # Create IDs
            ids = [f"{file_path}::{i}" for i in range(len(chunks))]
            
            # Create metadata
            metadatas = [
                {
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "chunk_type": chunk.chunk_type,
                }
                for chunk in chunks
            ]
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            
            logger.debug(f"Indexed {file_path}: {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get indexer statistics."""
        return {
            "collection_name": self.collection.name,
            "total_chunks": self.collection.count(),
            "indexed_files": len(self._indexed_files),
            "persist_directory": self.persist_directory,
        }
    
    def clear(self) -> None:
        """Clear all indexed documents."""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(
            name=self.collection.name,
            metadata={"hnsw:space": "cosine"}
        )
        self._indexed_files.clear()
        logger.info("Index cleared")


# =============================================================================
# SINGLETON
# =============================================================================

_indexer_instance: Optional[DocumentIndexer] = None


def get_indexer() -> DocumentIndexer:
    """Get or create the global document indexer."""
    global _indexer_instance
    
    if _indexer_instance is None:
        _indexer_instance = DocumentIndexer()
    
    return _indexer_instance
