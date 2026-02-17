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
    Special chunking for tabular data with markdown formatting
    """

    @staticmethod
    def table_to_markdown(
        headers: List[str],
        rows: List[List[str]],
        table_context: str = None
    ) -> str:
        """
        Convert table to markdown format

        Args:
            headers: Column headers
            rows: Table rows (list of lists)
            table_context: Optional context describing the table

        Returns:
            Markdown-formatted table string
        """
        if not headers or not rows:
            return ""

        # Clean and normalize cells
        def clean_cell(cell):
            if cell is None:
                return ""
            return str(cell).strip().replace("\n", " ")

        headers = [clean_cell(h) for h in headers]

        # Build markdown table
        markdown_parts = []

        # Add context if provided
        if table_context:
            markdown_parts.append(f"{table_context}\n")

        # Header row
        header_row = "| " + " | ".join(headers) + " |"
        markdown_parts.append(header_row)

        # Separator row
        separator = "|" + "|".join(["-" * (len(h) + 2) for h in headers]) + "|"
        markdown_parts.append(separator)

        # Data rows
        for row in rows:
            cleaned_row = [clean_cell(cell) for cell in row]
            # Pad row if it has fewer columns than headers
            while len(cleaned_row) < len(headers):
                cleaned_row.append("")
            row_text = "| " + " | ".join(cleaned_row[:len(headers)]) + " |"
            markdown_parts.append(row_text)

        return "\n".join(markdown_parts)

    @staticmethod
    def infer_table_type(headers: List[str], context: str = "") -> str:
        """
        Infer the semantic type of table from headers and context

        Args:
            headers: Column headers
            context: Surrounding text context

        Returns:
            Table type string (dosing, protocol, comparison, composition, etc.)
        """
        headers_lower = " ".join(h.lower() for h in headers if h)
        context_lower = context.lower()

        # Dosing/protocol table patterns
        if any(term in headers_lower for term in ["dose", "dosage", "volume", "frequency", "session"]):
            return "dosing"

        # Composition table patterns
        if any(term in headers_lower for term in ["composition", "ingredient", "component", "concentration"]):
            return "composition"

        # Comparison table patterns
        if any(term in headers_lower for term in ["product", "vs", "comparison", "versus"]):
            return "comparison"

        # Protocol/treatment table patterns
        if any(term in headers_lower for term in ["step", "phase", "treatment", "procedure"]):
            return "protocol"

        # Indication/contraindication patterns
        if any(term in headers_lower for term in ["indication", "contraindication", "condition"]):
            return "indication"

        # Results/outcomes table
        if any(term in headers_lower for term in ["result", "outcome", "improvement", "efficacy"]):
            return "results"

        return "general"

    @staticmethod
    def chunk_table(
        table_data: List[List[str]],
        headers: List[str],
        base_metadata: Dict[str, Any] = None,
        as_markdown: bool = True,
        table_context: str = None
    ) -> List[Chunk]:
        """
        Convert table into chunks (full table as markdown by default)

        Args:
            table_data: List of rows (each row is a list of cells)
            headers: Column headers
            base_metadata: Base metadata
            as_markdown: If True, create single markdown table chunk; if False, one chunk per row
            table_context: Optional context describing the table

        Returns:
            List of chunks
        """
        base_metadata = base_metadata or {}
        chunks = []

        # Infer table type
        table_type = TableChunker.infer_table_type(headers, table_context or "")

        if as_markdown:
            # Create single chunk with full markdown table
            markdown_table = TableChunker.table_to_markdown(headers, table_data, table_context)

            chunks.append(Chunk(
                text=markdown_table,
                chunk_id="table_markdown",
                metadata={
                    **base_metadata,
                    "is_table": True,
                    "table_type": table_type,
                    "num_rows": len(table_data),
                    "num_cols": len(headers),
                    "headers": headers
                },
                char_start=0,
                char_end=len(markdown_table)
            ))
        else:
            # Create one chunk per row (legacy format)
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
                        "is_table": True,
                        "table_type": table_type,
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
