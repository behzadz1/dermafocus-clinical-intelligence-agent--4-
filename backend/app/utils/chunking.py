"""
Text Chunking Utilities for RAG
Intelligent text splitting with context preservation
"""

from typing import List, Dict, Any
import re
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    text: str
    chunk_id: str
    metadata: Dict[str, Any]
    char_start: int
    char_end: int


class TextChunker:
    """
    Smart text chunking for RAG with sentence awareness and context preservation
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        """
        Args:
            chunk_size: Target size for each chunk (characters)
            chunk_overlap: Number of overlapping characters between chunks
            min_chunk_size: Minimum chunk size (avoid tiny chunks)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        # Sentence boundary regex (matches . ! ? followed by space/newline)
        self.sentence_endings = re.compile(r'([.!?])\s+')
    
    def chunk_text(
        self,
        text: str,
        base_metadata: Dict[str, Any] = None
    ) -> List[Chunk]:
        """
        Split text into overlapping chunks with sentence awareness
        
        Args:
            text: Input text to chunk
            base_metadata: Base metadata to include in all chunks
            
        Returns:
            List of Chunk objects
        """
        if not text or len(text.strip()) == 0:
            return []
        
        base_metadata = base_metadata or {}
        
        # Split into sentences first
        sentences = self._split_into_sentences(text)
        
        # Build chunks from sentences
        chunks = []
        current_chunk = []
        current_length = 0
        char_position = 0
        actual_chunk_start = 0  # Track actual position in original text

        for sentence in sentences:
            sentence_length = len(sentence)

            # If adding this sentence exceeds chunk_size, finalize current chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)

                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_id=f"chunk_{len(chunks)}",
                    metadata={
                        **base_metadata,
                        "chunk_index": len(chunks),
                        "chunk_length": len(chunk_text)
                    },
                    char_start=actual_chunk_start,  # Use tracked position
                    char_end=actual_chunk_start + len(chunk_text)
                ))

                # Update position tracker
                actual_chunk_start += len(chunk_text) + 1  # +1 for space

                # Keep overlap sentences for context
                overlap_text = chunk_text[-self.chunk_overlap:]
                overlap_sentences = self._split_into_sentences(overlap_text)
                current_chunk = overlap_sentences
                current_length = sum(len(s) + 1 for s in overlap_sentences)

            current_chunk.append(sentence)
            current_length += sentence_length + 1  # +1 for space
            char_position += sentence_length + 1

        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:

                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_id=f"chunk_{len(chunks)}",
                    metadata={
                        **base_metadata,
                        "chunk_index": len(chunks),
                        "chunk_length": len(chunk_text)
                    },
                    char_start=actual_chunk_start,  # Use tracked position
                    char_end=actual_chunk_start + len(chunk_text)
                ))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Split on sentence boundaries
        sentences = self.sentence_endings.split(text)
        
        # Recombine sentence endings with their sentences
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
                sentence = sentence.strip()
                if sentence:
                    result.append(sentence)
        
        # Handle last sentence if no ending punctuation
        if sentences and sentences[-1].strip():
            result.append(sentences[-1].strip())
        
        return result
    
    def chunk_by_sections(
        self,
        text: str,
        section_pattern: str = r'\n#{1,3}\s+(.+)\n',
        base_metadata: Dict[str, Any] = None
    ) -> List[Chunk]:
        """
        Chunk text by sections (e.g., markdown headers)
        
        Args:
            text: Input text
            section_pattern: Regex pattern for section headers
            base_metadata: Base metadata
            
        Returns:
            List of chunks
        """
        base_metadata = base_metadata or {}
        
        # Find all section headers
        sections = re.split(section_pattern, text)
        
        chunks = []
        current_section = None
        
        for i, section in enumerate(sections):
            if i % 2 == 1:  # Section header
                current_section = section.strip()
            else:  # Section content
                content = section.strip()
                if content:
                    # Chunk this section's content
                    section_chunks = self.chunk_text(
                        content,
                        base_metadata={
                            **base_metadata,
                            "section": current_section or "Introduction"
                        }
                    )
                    chunks.extend(section_chunks)
        
        return chunks


class TableChunker:
    """
    Special chunking for tabular data
    """
    
    @staticmethod
    def chunk_table(
        table_data: List[List[str]],
        headers: List[str],
        base_metadata: Dict[str, Any] = None
    ) -> List[Chunk]:
        """
        Convert table rows into chunks
        
        Args:
            table_data: List of rows (each row is a list of cells)
            headers: Column headers
            base_metadata: Base metadata
            
        Returns:
            List of chunks (one per row)
        """
        base_metadata = base_metadata or {}
        chunks = []
        
        for row_idx, row in enumerate(table_data):
            # Create text representation of row
            row_text = " | ".join(
                f"{header}: {cell}"
                for header, cell in zip(headers, row)
            )
            
            chunks.append(Chunk(
                text=row_text,
                chunk_id=f"table_row_{row_idx}",
                metadata={
                    **base_metadata,
                    "type": "table_row",
                    "row_index": row_idx,
                    "headers": headers
                },
                char_start=0,
                char_end=len(row_text)
            ))
        
        return chunks


def merge_chunks(chunks: List[Chunk], max_size: int = 2000) -> List[Chunk]:
    """
    Merge small chunks together to reach target size
    
    Args:
        chunks: List of chunks to merge
        max_size: Maximum size for merged chunks
        
    Returns:
        List of merged chunks
    """
    if not chunks:
        return []
    
    merged = []
    current_batch = []
    current_size = 0
    
    for chunk in chunks:
        chunk_size = len(chunk.text)
        
        if current_size + chunk_size > max_size and current_batch:
            # Merge current batch
            merged_text = '\n\n'.join(c.text for c in current_batch)
            merged_metadata = current_batch[0].metadata.copy()
            merged_metadata["merged_from"] = len(current_batch)
            
            merged.append(Chunk(
                text=merged_text,
                chunk_id=f"merged_{len(merged)}",
                metadata=merged_metadata,
                char_start=current_batch[0].char_start,
                char_end=current_batch[-1].char_end
            ))
            
            current_batch = [chunk]
            current_size = chunk_size
        else:
            current_batch.append(chunk)
            current_size += chunk_size
    
    # Merge final batch
    if current_batch:
        merged_text = '\n\n'.join(c.text for c in current_batch)
        merged_metadata = current_batch[0].metadata.copy()
        merged_metadata["merged_from"] = len(current_batch)
        
        merged.append(Chunk(
            text=merged_text,
            chunk_id=f"merged_{len(merged)}",
            metadata=merged_metadata,
            char_start=current_batch[0].char_start,
            char_end=current_batch[-1].char_end
        ))
    
    return merged


# Convenience function
def chunk_text_simple(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    metadata: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Simple text chunking - returns list of dicts
    
    Args:
        text: Input text
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
        metadata: Base metadata
        
    Returns:
        List of chunk dictionaries
    """
    chunker = TextChunker(chunk_size, chunk_overlap)
    chunks = chunker.chunk_text(text, metadata)
    
    return [
        {
            "text": chunk.text,
            "chunk_id": chunk.chunk_id,
            "metadata": chunk.metadata
        }
        for chunk in chunks
    ]
