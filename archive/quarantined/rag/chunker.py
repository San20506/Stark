"""
STARK RAG - Document Chunker
=============================
Smart text chunking that preserves semantic boundaries.

Handles:
- Code files (preserve functions/classes)
- Markdown (preserve sections)
- Plain text (sentence boundaries)
"""

import logging
import re
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A chunk of text with metadata."""
    text: str
    source: str
    chunk_index: int
    chunk_type: str = "text"  # text, code, markdown
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DocumentChunker:
    """
    Chunk documents intelligently.
    
    Strategies:
    - Code: Split by function/class boundaries
    - Markdown: Split by headers
    - Text: Split by paragraphs/sentences
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target chunk size (characters)
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_document(self, text: str, source: str, file_type: str = "text") -> List[Chunk]:
        """
        Chunk a document.
        
        Args:
            text: Document text
            source: Source path/URL
            file_type: File type (python, markdown, text)
            
        Returns:
            List of Chunk objects
        """
        if file_type == "python":
            return self._chunk_python(text, source)
        elif file_type in ["markdown", "md"]:
            return self._chunk_markdown(text, source)
        else:
            return self._chunk_text(text, source)
    
    def _chunk_python(self, text: str, source: str) -> List[Chunk]:
        """Chunk Python code by function/class."""
        chunks = []
        
        # Try to split by top-level definitions
        pattern = r'^(class |def |async def )'
        lines = text.split('\n')
        
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for line in lines:
            line_with_newline = line + '\n'
            line_size = len(line_with_newline)
            
            # Check if this is a new function/class
            if re.match(pattern, line) and current_size > 0:
                # Save current chunk
                chunks.append(Chunk(
                    text=''.join(current_chunk),
                    source=source,
                    chunk_index=chunk_index,
                    chunk_type="code",
                ))
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_lines = current_chunk[-5:] if len(current_chunk) > 5 else current_chunk
                current_chunk = overlap_lines + [line_with_newline]
                current_size = sum(len(l) for l in current_chunk)
            else:
                current_chunk.append(line_with_newline)
                current_size += line_size
                
                # Check if chunk is too large
                if current_size >= self.chunk_size:
                    chunks.append(Chunk(
                        text=''.join(current_chunk),
                        source=source,
                        chunk_index=chunk_index,
                        chunk_type="code",
                    ))
                    chunk_index += 1
                    
                    # Keep overlap
                    overlap_lines = current_chunk[-5:]
                    current_chunk = overlap_lines
                    current_size = sum(len(l) for l in current_chunk)
        
        # Add remaining
        if current_chunk:
            chunks.append(Chunk(
                text=''.join(current_chunk),
                source=source,
                chunk_index=chunk_index,
                chunk_type="code",
            ))
        
        return chunks if chunks else [Chunk(text=text, source=source, chunk_index=0, chunk_type="code")]
    
    def _chunk_markdown(self, text: str, source: str) -> List[Chunk]:
        """Chunk markdown by headers."""
        chunks = []
        
        # Split by headers (# ## ###)
        sections = re.split(r'^(#{1,6}\s+.+)$', text, flags=re.MULTILINE)
        
        current_chunk = ""
        chunk_index = 0
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            # Check if this is a header
            if re.match(r'^#{1,6}\s+', section):
                # Save previous chunk
                if current_chunk and len(current_chunk) > self.overlap_size:
                    chunks.append(Chunk(
                        text=current_chunk.strip(),
                        source=source,
                        chunk_index=chunk_index,
                        chunk_type="markdown",
                    ))
                    chunk_index += 1
                    current_chunk = ""
                
                current_chunk += section + "\n"
            else:
                current_chunk += section
                
                # Check size
                if len(current_chunk) >= self.chunk_size:
                    chunks.append(Chunk(
                        text=current_chunk.strip(),
                        source=source,
                        chunk_index=chunk_index,
                        chunk_type="markdown",
                    ))
                    chunk_index += 1
                    current_chunk = ""
        
        # Add remaining
        if current_chunk.strip():
            chunks.append(Chunk(
                text=current_chunk.strip(),
                source=source,
                chunk_index=chunk_index,
                chunk_type="markdown",
            ))
        
        return chunks if chunks else [Chunk(text=text, source=source, chunk_index=0, chunk_type="markdown")]
    
    def _chunk_text(self, text: str, source: str) -> List[Chunk]:
        """Chunk plain text by paragraphs/sentences."""
        chunks = []
        
        # Split by double newline (paragraphs)
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check if adding this paragraph would exceed chunk size
            if current_chunk and len(current_chunk) + len(para) > self.chunk_size:
                # Save current chunk
                chunks.append(Chunk(
                    text=current_chunk.strip(),
                    source=source,
                    chunk_index=chunk_index,
                    chunk_type="text",
                ))
                chunk_index += 1
                
                # Start new chunk with overlap (last sentence)
                sentences = current_chunk.split('. ')
                overlap = sentences[-1] if sentences else ""
                current_chunk = overlap + " " + para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        # Add remaining
        if current_chunk.strip():
            chunks.append(Chunk(
                text=current_chunk.strip(),
                source=source,
                chunk_index=chunk_index,
                chunk_type="text",
            ))
        
        return chunks if chunks else [Chunk(text=text, source=source, chunk_index=0, chunk_type="text")]
    
    @property
    def overlap_size(self) -> int:
        """Get overlap size in characters."""
        return min(self.chunk_overlap, self.chunk_size // 4)
