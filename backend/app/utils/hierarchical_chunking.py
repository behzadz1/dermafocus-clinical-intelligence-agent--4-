"""
Hierarchical and Adaptive Chunking Strategies for RAG
Implements document-type specific chunking for optimal retrieval
"""

import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class ChunkType(Enum):
    """Types of chunks in the hierarchy"""
    DOCUMENT = "document"      # Full document summary
    SECTION = "section"        # Section/parent level
    DETAIL = "detail"          # Detail/child level
    FLAT = "flat"              # Non-hierarchical chunk


class DocumentType(Enum):
    """Document types with specific chunking strategies"""
    CLINICAL_PAPER = "clinical_paper"
    CASE_STUDY = "case_study"
    PROTOCOL = "protocol"
    FACTSHEET = "factsheet"
    BROCHURE = "brochure"
    PRODUCT = "product"
    UNKNOWN = "unknown"


@dataclass
class HierarchicalChunk:
    """Represents a chunk with hierarchical relationships"""
    id: str
    text: str
    chunk_type: ChunkType
    doc_id: str
    doc_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    section: Optional[str] = None
    char_start: int = 0
    char_end: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "text": self.text,
            "chunk_type": self.chunk_type.value,
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "section": self.section,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "metadata": self.metadata
        }


class BaseChunker(ABC):
    """Base class for all chunking strategies"""

    @abstractmethod
    def chunk(self, text: str, doc_id: str, doc_type: str,
              metadata: Dict[str, Any] = None) -> List[HierarchicalChunk]:
        """Chunk text into hierarchical chunks"""
        pass

    def _generate_chunk_id(self, doc_id: str, prefix: str = "chunk") -> str:
        """Generate unique chunk ID"""
        short_uuid = str(uuid.uuid4())[:8]
        safe_doc_id = re.sub(r'[^a-zA-Z0-9]', '_', doc_id)[:50]
        return f"{safe_doc_id}_{prefix}_{short_uuid}"

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Handle common abbreviations in medical text
        text = re.sub(r'(\d+)\.\s*(\d+)', r'\1<DECIMAL>\2', text)
        text = re.sub(r'(Dr|Mr|Mrs|Ms|Prof|etc|vs|i\.e|e\.g)\.\s', r'\1<ABBR> ', text, flags=re.IGNORECASE)

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Restore abbreviations
        sentences = [s.replace('<DECIMAL>', '.').replace('<ABBR>', '.') for s in sentences]

        return [s.strip() for s in sentences if s.strip()]

    def _clean_text(self, text: str) -> str:
        """Clean text for chunking"""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text


class HierarchicalChunker(BaseChunker):
    """
    Hierarchical chunking for complex documents (clinical papers)
    Creates parent (section) and child (detail) chunks
    """

    # Common section headers in clinical/medical papers
    SECTION_PATTERNS = [
        r'^(?:ABSTRACT|Abstract)\s*$',
        r'^(?:INTRODUCTION|Introduction)\s*$',
        r'^(?:BACKGROUND|Background)\s*$',
        r'^(?:METHODS?|Methods?|MATERIALS?\s+AND\s+METHODS?)\s*$',
        r'^(?:RESULTS?|Results?)\s*$',
        r'^(?:DISCUSSION|Discussion)\s*$',
        r'^(?:CONCLUSION|Conclusion|CONCLUSIONS?|Conclusions?)\s*$',
        r'^(?:REFERENCES?|References?)\s*$',
        r'^(?:ACKNOWLEDGMENTS?|Acknowledgments?)\s*$',
        r'^\d+\.\s+[A-Z][A-Za-z\s]+$',  # Numbered sections
        r'^[A-Z][A-Z\s]{2,50}$',  # ALL CAPS headers
    ]

    def __init__(
        self,
        parent_chunk_size: int = 2000,
        child_chunk_size: int = 500,
        child_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.child_overlap = child_overlap
        self.min_chunk_size = min_chunk_size

    def chunk(self, text: str, doc_id: str, doc_type: str,
              metadata: Dict[str, Any] = None) -> List[HierarchicalChunk]:
        """Create hierarchical chunks from text"""
        metadata = metadata or {}
        all_chunks = []

        # Detect and split by sections
        sections = self._detect_sections(text)

        for section_name, section_text in sections:
            if len(section_text.strip()) < self.min_chunk_size:
                continue

            # Create parent chunk for section
            parent_id = self._generate_chunk_id(doc_id, f"section_{section_name[:20]}")
            parent_text = self._create_section_summary(section_name, section_text)

            parent_chunk = HierarchicalChunk(
                id=parent_id,
                text=parent_text,
                chunk_type=ChunkType.SECTION,
                doc_id=doc_id,
                doc_type=doc_type,
                section=section_name,
                metadata={**metadata, "section": section_name},
                char_start=text.find(section_text[:50]) if section_text else 0,
                char_end=text.find(section_text[:50]) + len(section_text) if section_text else 0
            )

            # Create child chunks for details
            child_chunks = self._create_child_chunks(
                section_text, doc_id, doc_type, parent_id, section_name, metadata
            )

            # Link parent to children
            parent_chunk.children_ids = [c.id for c in child_chunks]

            all_chunks.append(parent_chunk)
            all_chunks.extend(child_chunks)

        return all_chunks

    def _detect_sections(self, text: str) -> List[Tuple[str, str]]:
        """Detect sections in text based on headers"""
        sections = []
        current_section = "Introduction"
        current_text = []

        lines = text.split('\n')

        for line in lines:
            line_stripped = line.strip()

            # Check if this line is a section header
            is_header = False
            for pattern in self.SECTION_PATTERNS:
                if re.match(pattern, line_stripped):
                    # Save previous section
                    if current_text:
                        sections.append((current_section, '\n'.join(current_text)))

                    # Start new section
                    current_section = line_stripped.title()
                    current_text = []
                    is_header = True
                    break

            if not is_header:
                current_text.append(line)

        # Add final section
        if current_text:
            sections.append((current_section, '\n'.join(current_text)))

        # If no sections detected, treat entire text as one section
        if not sections:
            sections = [("Content", text)]

        return sections

    def _create_section_summary(self, section_name: str, section_text: str) -> str:
        """Create a summary text for the parent chunk"""
        # Take first few sentences as summary (up to parent_chunk_size)
        sentences = self._split_into_sentences(section_text)

        summary_text = f"[{section_name}] "
        for sentence in sentences:
            if len(summary_text) + len(sentence) > self.parent_chunk_size:
                break
            summary_text += sentence + " "

        return summary_text.strip()

    def _create_child_chunks(
        self,
        text: str,
        doc_id: str,
        doc_type: str,
        parent_id: str,
        section_name: str,
        metadata: Dict[str, Any]
    ) -> List[HierarchicalChunk]:
        """Create child chunks with overlap"""
        chunks = []
        sentences = self._split_into_sentences(text)

        current_chunk = []
        current_length = 0
        char_position = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length > self.child_chunk_size and current_chunk:
                # Create chunk
                chunk_text = ' '.join(current_chunk)
                chunk_id = self._generate_chunk_id(doc_id, "detail")

                chunks.append(HierarchicalChunk(
                    id=chunk_id,
                    text=f"[{section_name}] {chunk_text}",  # Prepend section context
                    chunk_type=ChunkType.DETAIL,
                    doc_id=doc_id,
                    doc_type=doc_type,
                    parent_id=parent_id,
                    section=section_name,
                    metadata={**metadata, "section": section_name},
                    char_start=char_position - current_length,
                    char_end=char_position
                ))

                # Keep overlap
                overlap_text = chunk_text[-self.child_overlap:] if len(chunk_text) > self.child_overlap else chunk_text
                overlap_sentences = self._split_into_sentences(overlap_text)
                current_chunk = overlap_sentences
                current_length = sum(len(s) + 1 for s in overlap_sentences)

            current_chunk.append(sentence)
            current_length += sentence_length + 1
            char_position += sentence_length + 1

        # Final chunk
        if current_chunk and current_length >= self.min_chunk_size:
            chunk_text = ' '.join(current_chunk)
            chunk_id = self._generate_chunk_id(doc_id, "detail")

            chunks.append(HierarchicalChunk(
                id=chunk_id,
                text=f"[{section_name}] {chunk_text}",
                chunk_type=ChunkType.DETAIL,
                doc_id=doc_id,
                doc_type=doc_type,
                parent_id=parent_id,
                section=section_name,
                metadata={**metadata, "section": section_name},
                char_start=char_position - current_length,
                char_end=char_position
            ))

        return chunks


class AdaptiveChunker(BaseChunker):
    """
    Adaptive chunking based on semantic boundaries
    Best for case studies and narrative documents
    """

    def __init__(
        self,
        chunk_size: int = 800,
        min_chunk_size: int = 200,
        overlap: int = 100,
        similarity_threshold: float = 0.75
    ):
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
        self.similarity_threshold = similarity_threshold

    def chunk(self, text: str, doc_id: str, doc_type: str,
              metadata: Dict[str, Any] = None) -> List[HierarchicalChunk]:
        """Create adaptive chunks based on content boundaries"""
        metadata = metadata or {}
        chunks = []

        # Split into paragraphs first
        paragraphs = self._split_into_paragraphs(text)

        current_chunk = []
        current_length = 0
        char_position = 0

        for i, paragraph in enumerate(paragraphs):
            para_length = len(paragraph)

            # Check for semantic break (topic change indicators)
            is_break = self._detect_semantic_break(
                current_chunk, paragraph
            ) if current_chunk else False

            # Create chunk if size exceeded or semantic break
            if (current_length + para_length > self.chunk_size or is_break) and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)

                if len(chunk_text) >= self.min_chunk_size:
                    chunk_id = self._generate_chunk_id(doc_id, "adaptive")

                    # Detect section from content
                    section = self._detect_section_from_content(chunk_text)

                    chunks.append(HierarchicalChunk(
                        id=chunk_id,
                        text=chunk_text,
                        chunk_type=ChunkType.FLAT,
                        doc_id=doc_id,
                        doc_type=doc_type,
                        section=section,
                        metadata={**metadata, "section": section},
                        char_start=char_position - current_length,
                        char_end=char_position
                    ))

                # Start new chunk with overlap
                if self.overlap > 0 and current_chunk:
                    overlap_text = chunk_text[-self.overlap:]
                    current_chunk = [overlap_text]
                    current_length = len(overlap_text)
                else:
                    current_chunk = []
                    current_length = 0

            current_chunk.append(paragraph)
            current_length += para_length + 2  # +2 for paragraph separator
            char_position += para_length + 2

        # Final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunk_id = self._generate_chunk_id(doc_id, "adaptive")
                section = self._detect_section_from_content(chunk_text)

                chunks.append(HierarchicalChunk(
                    id=chunk_id,
                    text=chunk_text,
                    chunk_type=ChunkType.FLAT,
                    doc_id=doc_id,
                    doc_type=doc_type,
                    section=section,
                    metadata={**metadata, "section": section},
                    char_start=char_position - current_length,
                    char_end=char_position
                ))

        return chunks

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _detect_semantic_break(self, current_chunks: List[str], next_paragraph: str) -> bool:
        """Detect if there's a semantic break between chunks"""
        # Simple heuristic-based detection
        break_indicators = [
            r'^(?:However|Nevertheless|In contrast|On the other hand)',
            r'^(?:Furthermore|Moreover|Additionally|In addition)',
            r'^(?:Case \d+|Patient \d+|Example \d+)',
            r'^(?:Results|Discussion|Conclusion|Summary)',
            r'^\d+\.',  # Numbered items
        ]

        for pattern in break_indicators:
            if re.match(pattern, next_paragraph, re.IGNORECASE):
                return True

        return False

    def _detect_section_from_content(self, text: str) -> str:
        """Detect section type from content"""
        text_lower = text.lower()

        if any(word in text_lower for word in ['patient', 'case', 'presented', 'history']):
            return "Case Presentation"
        elif any(word in text_lower for word in ['result', 'outcome', 'improvement', 'showed']):
            return "Results"
        elif any(word in text_lower for word in ['method', 'technique', 'procedure', 'treatment']):
            return "Methods"
        elif any(word in text_lower for word in ['conclusion', 'summary', 'therefore']):
            return "Conclusion"

        return "Content"


class StepAwareChunker(BaseChunker):
    """
    Step-aware chunking for protocol documents
    Keeps procedural steps together
    """

    STEP_PATTERNS = [
        r'^(?:Step\s+\d+|Phase\s+\d+|\d+\.\s+\w)',
        r'^(?:First|Second|Third|Fourth|Fifth|Finally)',
        r'^(?:Session\s+\d+|Week\s+\d+|Day\s+\d+)',
        r'^(?:\d+\)|[a-z]\)|•|→|-)\s+',
    ]

    def __init__(
        self,
        chunk_size: int = 600,
        min_chunk_size: int = 150,
        overlap: int = 50,
        keep_steps_together: bool = True
    ):
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
        self.keep_steps_together = keep_steps_together

    def chunk(self, text: str, doc_id: str, doc_type: str,
              metadata: Dict[str, Any] = None) -> List[HierarchicalChunk]:
        """Create step-aware chunks"""
        metadata = metadata or {}
        chunks = []

        # Detect steps/procedures
        steps = self._detect_steps(text)

        current_chunk = []
        current_length = 0
        step_number = 0

        for step_text in steps:
            step_length = len(step_text)

            # If keeping steps together and this is a new step
            if self.keep_steps_together and self._is_step_start(step_text):
                if current_chunk and current_length >= self.min_chunk_size:
                    # Save current chunk
                    chunk_text = '\n'.join(current_chunk)
                    chunk_id = self._generate_chunk_id(doc_id, f"step_{step_number}")

                    chunks.append(HierarchicalChunk(
                        id=chunk_id,
                        text=chunk_text,
                        chunk_type=ChunkType.FLAT,
                        doc_id=doc_id,
                        doc_type=doc_type,
                        section=f"Step {step_number}" if step_number > 0 else "Protocol",
                        metadata={**metadata, "step_number": step_number}
                    ))
                    step_number += 1

                current_chunk = [step_text]
                current_length = step_length

            # Regular size-based chunking
            elif current_length + step_length > self.chunk_size and current_chunk:
                chunk_text = '\n'.join(current_chunk)

                if len(chunk_text) >= self.min_chunk_size:
                    chunk_id = self._generate_chunk_id(doc_id, f"step_{step_number}")

                    chunks.append(HierarchicalChunk(
                        id=chunk_id,
                        text=chunk_text,
                        chunk_type=ChunkType.FLAT,
                        doc_id=doc_id,
                        doc_type=doc_type,
                        section=f"Step {step_number}" if step_number > 0 else "Protocol",
                        metadata={**metadata, "step_number": step_number}
                    ))

                current_chunk = [step_text]
                current_length = step_length
            else:
                current_chunk.append(step_text)
                current_length += step_length + 1

        # Final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunk_id = self._generate_chunk_id(doc_id, f"step_{step_number}")

                chunks.append(HierarchicalChunk(
                    id=chunk_id,
                    text=chunk_text,
                    chunk_type=ChunkType.FLAT,
                    doc_id=doc_id,
                    doc_type=doc_type,
                    section=f"Step {step_number}" if step_number > 0 else "Protocol",
                    metadata={**metadata, "step_number": step_number}
                ))

        return chunks

    def _detect_steps(self, text: str) -> List[str]:
        """Split text into logical steps"""
        lines = text.split('\n')
        steps = []
        current_step = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if self._is_step_start(line) and current_step:
                steps.append('\n'.join(current_step))
                current_step = [line]
            else:
                current_step.append(line)

        if current_step:
            steps.append('\n'.join(current_step))

        return steps if steps else [text]

    def _is_step_start(self, text: str) -> bool:
        """Check if text starts a new step"""
        for pattern in self.STEP_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False


class SectionBasedChunker(BaseChunker):
    """
    Section-based chunking for structured documents (factsheets, brochures)
    One chunk per logical section
    """

    # Common sections in medical product documents
    DEFAULT_SECTIONS = [
        "Product Name", "Composition", "Mechanism of Action",
        "Indications", "Contraindications", "Warnings",
        "Dosage", "Administration", "Storage", "Packaging",
        "Expected Results", "Aftercare", "Treatment Protocol"
    ]

    def __init__(
        self,
        chunk_size: int = 400,
        min_chunk_size: int = 100,
        section_headers: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.section_headers = section_headers or self.DEFAULT_SECTIONS

    def chunk(self, text: str, doc_id: str, doc_type: str,
              metadata: Dict[str, Any] = None) -> List[HierarchicalChunk]:
        """Create section-based chunks"""
        metadata = metadata or {}
        chunks = []

        # Build section pattern
        section_pattern = '|'.join(
            re.escape(header) for header in self.section_headers
        )
        pattern = rf'(?i)({section_pattern})\s*[:.]?\s*'

        # Split by sections
        parts = re.split(pattern, text)

        current_section = "Overview"

        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            # Check if this is a section header
            if any(header.lower() in part.lower() for header in self.section_headers):
                current_section = part.title()
                continue

            # Create chunk for section content
            if len(part) >= self.min_chunk_size:
                # If section is too large, split it
                if len(part) > self.chunk_size:
                    sub_chunks = self._split_large_section(
                        part, doc_id, doc_type, current_section, metadata
                    )
                    chunks.extend(sub_chunks)
                else:
                    chunk_id = self._generate_chunk_id(doc_id, f"section_{current_section[:15]}")

                    chunks.append(HierarchicalChunk(
                        id=chunk_id,
                        text=f"[{current_section}] {part}",
                        chunk_type=ChunkType.FLAT,
                        doc_id=doc_id,
                        doc_type=doc_type,
                        section=current_section,
                        metadata={**metadata, "section": current_section}
                    ))

        # If no sections detected, fall back to simple chunking
        if not chunks:
            return self._fallback_chunk(text, doc_id, doc_type, metadata)

        return chunks

    def _split_large_section(
        self,
        text: str,
        doc_id: str,
        doc_type: str,
        section: str,
        metadata: Dict[str, Any]
    ) -> List[HierarchicalChunk]:
        """Split a large section into multiple chunks"""
        chunks = []
        sentences = self._split_into_sentences(text)

        current_chunk = []
        current_length = 0

        for sentence in sentences:
            if current_length + len(sentence) > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunk_id = self._generate_chunk_id(doc_id, f"section_{section[:15]}")

                chunks.append(HierarchicalChunk(
                    id=chunk_id,
                    text=f"[{section}] {chunk_text}",
                    chunk_type=ChunkType.FLAT,
                    doc_id=doc_id,
                    doc_type=doc_type,
                    section=section,
                    metadata={**metadata, "section": section}
                ))

                current_chunk = []
                current_length = 0

            current_chunk.append(sentence)
            current_length += len(sentence) + 1

        # Final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunk_id = self._generate_chunk_id(doc_id, f"section_{section[:15]}")

                chunks.append(HierarchicalChunk(
                    id=chunk_id,
                    text=f"[{section}] {chunk_text}",
                    chunk_type=ChunkType.FLAT,
                    doc_id=doc_id,
                    doc_type=doc_type,
                    section=section,
                    metadata={**metadata, "section": section}
                ))

        return chunks

    def _fallback_chunk(
        self,
        text: str,
        doc_id: str,
        doc_type: str,
        metadata: Dict[str, Any]
    ) -> List[HierarchicalChunk]:
        """Fallback to simple sentence-based chunking"""
        chunks = []
        sentences = self._split_into_sentences(text)

        current_chunk = []
        current_length = 0

        for sentence in sentences:
            if current_length + len(sentence) > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunk_id = self._generate_chunk_id(doc_id, "content")

                chunks.append(HierarchicalChunk(
                    id=chunk_id,
                    text=chunk_text,
                    chunk_type=ChunkType.FLAT,
                    doc_id=doc_id,
                    doc_type=doc_type,
                    section="Content",
                    metadata=metadata
                ))

                current_chunk = []
                current_length = 0

            current_chunk.append(sentence)
            current_length += len(sentence) + 1

        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunk_id = self._generate_chunk_id(doc_id, "content")

                chunks.append(HierarchicalChunk(
                    id=chunk_id,
                    text=chunk_text,
                    chunk_type=ChunkType.FLAT,
                    doc_id=doc_id,
                    doc_type=doc_type,
                    section="Content",
                    metadata=metadata
                ))

        return chunks


class ChunkingStrategyFactory:
    """
    Factory to select appropriate chunking strategy based on document type
    """

    # Document type detection patterns
    DOC_TYPE_PATTERNS = {
        DocumentType.CLINICAL_PAPER: [
            r'(?i)abstract.*introduction.*method',
            r'(?i)clinical\s+(trial|study|paper)',
            r'(?i)(pubmed|doi|journal)',
            r'(?i)materials?\s+and\s+methods?',
        ],
        DocumentType.CASE_STUDY: [
            r'(?i)case\s+(study|report|series)',
            r'(?i)patient\s+(presented|history)',
        ],
        DocumentType.PROTOCOL: [
            r'(?i)treatment\s+protocol',
            r'(?i)injection\s+technique',
            r'(?i)(step|phase)\s+\d+',
            r'(?i)session\s+\d+.*week',
        ],
        DocumentType.FACTSHEET: [
            r'(?i)fact\s*sheet',
            r'(?i)(composition|indications|contraindications)',
            r'(?i)product\s+(name|information)',
        ],
        DocumentType.BROCHURE: [
            r'(?i)brochure',
            r'(?i)dermafocus\.co\.uk',
        ],
    }

    # Folder name to document type mapping
    FOLDER_TYPE_MAP = {
        "clinical papers": DocumentType.CLINICAL_PAPER,
        "clinical_papers": DocumentType.CLINICAL_PAPER,
        "case studies": DocumentType.CASE_STUDY,
        "case_studies": DocumentType.CASE_STUDY,
        "fact sheets": DocumentType.FACTSHEET,
        "fact_sheets": DocumentType.FACTSHEET,
        "factsheets": DocumentType.FACTSHEET,
        "brochures": DocumentType.BROCHURE,
        "brochures ": DocumentType.BROCHURE,  # Handle trailing space
        "protocols": DocumentType.PROTOCOL,
        "treatment techniques & protocols": DocumentType.PROTOCOL,
        "injection techniques": DocumentType.PROTOCOL,
    }

    # Chunking configurations per document type
    CHUNK_CONFIGS = {
        DocumentType.CLINICAL_PAPER: {
            "chunker": HierarchicalChunker,
            "params": {
                "parent_chunk_size": 2000,
                "child_chunk_size": 500,
                "child_overlap": 50,
                "min_chunk_size": 100
            }
        },
        DocumentType.CASE_STUDY: {
            "chunker": AdaptiveChunker,
            "params": {
                "chunk_size": 800,
                "min_chunk_size": 200,
                "overlap": 100
            }
        },
        DocumentType.PROTOCOL: {
            "chunker": StepAwareChunker,
            "params": {
                "chunk_size": 600,
                "min_chunk_size": 150,
                "overlap": 50,
                "keep_steps_together": True
            }
        },
        DocumentType.FACTSHEET: {
            "chunker": SectionBasedChunker,
            "params": {
                "chunk_size": 400,
                "min_chunk_size": 100
            }
        },
        DocumentType.BROCHURE: {
            "chunker": SectionBasedChunker,
            "params": {
                "chunk_size": 500,
                "min_chunk_size": 100
            }
        },
        DocumentType.PRODUCT: {
            "chunker": SectionBasedChunker,
            "params": {
                "chunk_size": 400,
                "min_chunk_size": 100
            }
        },
        DocumentType.UNKNOWN: {
            "chunker": AdaptiveChunker,
            "params": {
                "chunk_size": 800,
                "min_chunk_size": 150,
                "overlap": 100
            }
        }
    }

    @classmethod
    def detect_document_type(
        cls,
        text: str = None,
        file_path: str = None,
        folder_name: str = None
    ) -> DocumentType:
        """
        Detect document type from content, file path, or folder name
        """
        # First try folder name (most reliable)
        if folder_name:
            folder_lower = folder_name.lower().strip()
            if folder_lower in cls.FOLDER_TYPE_MAP:
                return cls.FOLDER_TYPE_MAP[folder_lower]

        # Try file path
        if file_path:
            path_lower = file_path.lower()
            for folder_key, doc_type in cls.FOLDER_TYPE_MAP.items():
                if folder_key in path_lower:
                    return doc_type

        # Try content patterns
        if text:
            for doc_type, patterns in cls.DOC_TYPE_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, text[:5000]):  # Check first 5000 chars
                        return doc_type

        return DocumentType.UNKNOWN

    @classmethod
    def get_chunker(cls, doc_type: DocumentType) -> BaseChunker:
        """
        Get appropriate chunker instance for document type
        """
        config = cls.CHUNK_CONFIGS.get(doc_type, cls.CHUNK_CONFIGS[DocumentType.UNKNOWN])
        chunker_class = config["chunker"]
        params = config["params"]

        return chunker_class(**params)

    @classmethod
    def chunk_document(
        cls,
        text: str,
        doc_id: str,
        file_path: str = None,
        folder_name: str = None,
        metadata: Dict[str, Any] = None
    ) -> Tuple[List[HierarchicalChunk], DocumentType]:
        """
        Chunk document using appropriate strategy

        Returns:
            Tuple of (chunks, detected_doc_type)
        """
        # Detect document type
        doc_type = cls.detect_document_type(text, file_path, folder_name)

        # Get chunker
        chunker = cls.get_chunker(doc_type)

        # Chunk document
        chunks = chunker.chunk(
            text=text,
            doc_id=doc_id,
            doc_type=doc_type.value,
            metadata=metadata
        )

        return chunks, doc_type


# Convenience function for easy use
def chunk_document_hybrid(
    text: str,
    doc_id: str,
    file_path: str = None,
    folder_name: str = None,
    metadata: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Chunk document using hybrid strategy - returns list of dicts

    Args:
        text: Document text
        doc_id: Unique document identifier
        file_path: Optional file path for type detection
        folder_name: Optional folder name for type detection
        metadata: Additional metadata

    Returns:
        List of chunk dictionaries ready for embedding
    """
    chunks, doc_type = ChunkingStrategyFactory.chunk_document(
        text=text,
        doc_id=doc_id,
        file_path=file_path,
        folder_name=folder_name,
        metadata=metadata
    )

    return [chunk.to_dict() for chunk in chunks]
