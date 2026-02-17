"""
Protocol-Aware Chunking for Medical Documents
Keeps protocol information (sessions, dosages, frequencies) together
Fixes the 48% confidence issue for protocol queries
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ProtocolInfo:
    """Structured protocol information"""
    sessions: Optional[str] = None  # "3-4 sessions"
    frequency: Optional[str] = None  # "every 2-3 weeks"
    dosage: Optional[str] = None  # "2ml intradermal"
    duration: Optional[str] = None  # "over 8-12 weeks"
    technique: Optional[str] = None  # "microdroplet technique"


class ProtocolAwareChunker:
    """
    Enhanced chunker that keeps protocol information together

    Key improvements over StepAwareChunker:
    1. Detects protocol sections explicitly (Treatment Protocol, Dosage, etc.)
    2. Keeps protocol info together even if section is long
    3. Extracts structured protocol data
    4. Adds protocol context to all chunks from that document
    """

    # Protocol section headers
    PROTOCOL_HEADERS = [
        r'treatment\s+protocol',
        r'dosage\s+(?:and\s+)?administration',
        r'treatment\s+(?:schedule|regimen|course)',
        r'recommended\s+(?:dosage|treatment)',
        r'injection\s+protocol',
        r'session\s+protocol',
        r'how\s+to\s+use',
        r'administration\s+guide',
    ]

    # Protocol information patterns
    PROTOCOL_PATTERNS = {
        'sessions': [
            r'\d+[-–]\d+\s+(?:total\s+)?sessions?',
            r'\d+\s+sessions?',
            r'total\s+(?:of\s+)?\d+\s+sessions?',
            r'\d+\s+treatment\s+sessions?',
            r'sessions?:\s*\d+[-–]\d+',
        ],
        'frequency': [
            r'every\s+(\d+[-–]\d+|\d+)\s+(day|week|month)s?',
            r'once\s+(?:per|a)\s+(week|month)',
            r'(\d+)\s+times?\s+(?:per|a)\s+(week|month)',
            r'at\s+(\d+[-–]\d+|\d+)\s+(day|week)-intervals?',
        ],
        'dosage': [
            r'(\d+(?:\.\d+)?)\s*ml',
            r'(\d+(?:\.\d+)?)\s*mg',
            r'(\d+(?:\.\d+)?)\s*g\b',
            r'(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*ml',
        ],
        'duration': [
            r'over\s+(\d+[-–]\d+|\d+)\s+(day|week|month)s?',
            r'for\s+(\d+[-–]\d+|\d+)\s+(day|week|month)s?',
            r'(?:within|in)\s+(\d+[-–]\d+|\d+)\s+(day|week|month)s?',
        ]
    }

    def __init__(
        self,
        chunk_size: int = 800,  # Larger for protocols
        min_chunk_size: int = 200,
        protocol_section_max: int = 1200,  # Keep protocol sections up to this size
        keep_protocol_together: bool = True
    ):
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.protocol_section_max = protocol_section_max
        self.keep_protocol_together = keep_protocol_together

    def chunk_document(
        self,
        text: str,
        doc_id: str,
        doc_type: str = "protocol",
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk document with protocol awareness

        Returns list of chunks with enhanced protocol metadata
        """
        metadata = metadata or {}

        # Extract protocol information from full document
        protocol_info = self._extract_protocol_info(text)

        # Add protocol info to metadata
        protocol_metadata = {
            **metadata,
            'has_protocol_info': any([
                protocol_info.sessions,
                protocol_info.frequency,
                protocol_info.dosage,
                protocol_info.duration
            ])
        }

        if protocol_info.sessions:
            protocol_metadata['protocol_sessions'] = protocol_info.sessions
        if protocol_info.frequency:
            protocol_metadata['protocol_frequency'] = protocol_info.frequency
        if protocol_info.dosage:
            protocol_metadata['protocol_dosage'] = protocol_info.dosage
        if protocol_info.duration:
            protocol_metadata['protocol_duration'] = protocol_info.duration

        # Detect protocol sections
        sections = self._detect_protocol_sections(text)

        chunks = []

        for section_name, section_text, is_protocol_section in sections:
            if is_protocol_section and len(section_text) <= self.protocol_section_max:
                # Keep entire protocol section together
                chunks.append({
                    'text': f"[{section_name}]\n{section_text}",
                    'metadata': {
                        **protocol_metadata,
                        'section': section_name,
                        'is_protocol_section': True
                    },
                    'doc_id': doc_id,
                    'doc_type': doc_type
                })
            else:
                # Split large sections but preserve protocol context
                sub_chunks = self._split_section_with_context(
                    section_text,
                    section_name,
                    protocol_info,
                    doc_id,
                    doc_type,
                    protocol_metadata
                )
                chunks.extend(sub_chunks)

        return chunks

    def _extract_protocol_info(self, text: str) -> ProtocolInfo:
        """Extract structured protocol information from text"""
        info = ProtocolInfo()
        text_lower = text.lower()

        # Extract sessions
        for pattern in self.PROTOCOL_PATTERNS['sessions']:
            match = re.search(pattern, text_lower)
            if match:
                info.sessions = match.group(0)
                break

        # Extract frequency
        for pattern in self.PROTOCOL_PATTERNS['frequency']:
            match = re.search(pattern, text_lower)
            if match:
                info.frequency = match.group(0)
                break

        # Extract dosage
        for pattern in self.PROTOCOL_PATTERNS['dosage']:
            match = re.search(pattern, text_lower)
            if match:
                info.dosage = match.group(0)
                break

        # Extract duration
        for pattern in self.PROTOCOL_PATTERNS['duration']:
            match = re.search(pattern, text_lower)
            if match:
                info.duration = match.group(0)
                break

        return info

    def _detect_protocol_sections(self, text: str) -> List[Tuple[str, str, bool]]:
        """
        Detect protocol sections in text

        Returns: List of (section_name, section_text, is_protocol_section)
        """
        sections = []
        lines = text.split('\n')

        current_section = "Introduction"
        current_text = []
        is_current_protocol = False

        for line in lines:
            line_stripped = line.strip()

            # Check if this is a protocol section header
            is_protocol_header = False
            for pattern in self.PROTOCOL_HEADERS:
                if re.search(pattern, line_stripped, re.IGNORECASE):
                    # Save previous section
                    if current_text:
                        sections.append((
                            current_section,
                            '\n'.join(current_text),
                            is_current_protocol
                        ))

                    # Start new protocol section
                    current_section = line_stripped
                    current_text = []
                    is_current_protocol = True
                    is_protocol_header = True
                    break

            if not is_protocol_header:
                # Check for other section headers
                if self._is_section_header(line_stripped) and current_text:
                    # Save previous section
                    sections.append((
                        current_section,
                        '\n'.join(current_text),
                        is_current_protocol
                    ))

                    # Start new section
                    current_section = line_stripped
                    current_text = []
                    is_current_protocol = False
                else:
                    current_text.append(line)

        # Add final section
        if current_text:
            sections.append((
                current_section,
                '\n'.join(current_text),
                is_current_protocol
            ))

        return sections

    def _is_section_header(self, line: str) -> bool:
        """Check if line is a section header"""
        if not line:
            return False

        # Common section header patterns
        patterns = [
            r'^[A-Z][A-Za-z\s]+:$',  # "Section Name:"
            r'^[A-Z][A-Z\s]+$',  # "SECTION NAME"
            r'^\d+\.\s+[A-Z]',  # "1. Section"
            r'^#{1,3}\s+',  # Markdown headers
        ]

        for pattern in patterns:
            if re.match(pattern, line):
                return True

        return False

    def _split_section_with_context(
        self,
        text: str,
        section_name: str,
        protocol_info: ProtocolInfo,
        doc_id: str,
        doc_type: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Split large section while preserving protocol context
        """
        chunks = []

        # Create protocol context string
        context_parts = []
        if protocol_info.sessions:
            context_parts.append(f"Sessions: {protocol_info.sessions}")
        if protocol_info.frequency:
            context_parts.append(f"Frequency: {protocol_info.frequency}")
        if protocol_info.dosage:
            context_parts.append(f"Dosage: {protocol_info.dosage}")

        protocol_context = " | ".join(context_parts) if context_parts else ""

        # Split by sentences
        sentences = self._split_sentences(text)

        current_chunk = []
        current_length = 0
        chunk_num = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            if current_length + sentence_len > self.chunk_size and current_chunk:
                # Save current chunk with protocol context
                chunk_text = ' '.join(current_chunk)

                # Prepend protocol context if available
                if protocol_context:
                    full_text = f"[{section_name}] ({protocol_context})\n{chunk_text}"
                else:
                    full_text = f"[{section_name}]\n{chunk_text}"

                chunks.append({
                    'text': full_text,
                    'metadata': {
                        **metadata,
                        'section': section_name,
                        'chunk_part': chunk_num
                    },
                    'doc_id': doc_id,
                    'doc_type': doc_type
                })

                current_chunk = []
                current_length = 0
                chunk_num += 1

            current_chunk.append(sentence)
            current_length += sentence_len + 1

        # Final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)

            if protocol_context:
                full_text = f"[{section_name}] ({protocol_context})\n{chunk_text}"
            else:
                full_text = f"[{section_name}]\n{chunk_text}"

            chunks.append({
                'text': full_text,
                'metadata': {
                    **metadata,
                    'section': section_name,
                    'chunk_part': chunk_num
                },
                'doc_id': doc_id,
                'doc_type': doc_type
            })

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences, handling abbreviations"""
        # Handle common medical abbreviations
        text = re.sub(r'(\d+)\s*ml\.', r'\1ml', text)
        text = re.sub(r'(\d+)\s*mg\.', r'\1mg', text)
        text = re.sub(r'Dr\.', 'Dr', text)
        text = re.sub(r'vs\.', 'vs', text)

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        return [s.strip() for s in sentences if s.strip()]


# Wrapper class to provide HierarchicalChunk-like interface
class ChunkWrapper:
    """
    Wrapper to provide .to_dict() method for protocol chunks
    Avoids circular imports with hierarchical_chunking.py
    """

    def __init__(self, chunk_dict: Dict[str, Any]):
        self.data = chunk_dict

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return self.data


# Adapter for hierarchical chunking system compatibility
class ProtocolAwareChunkerAdapter:
    """
    Adapter to make ProtocolAwareChunker compatible with BaseChunker interface
    Used by ChunkingStrategyFactory in hierarchical_chunking.py
    """

    def __init__(
        self,
        chunk_size: int = 800,
        min_chunk_size: int = 200,
        protocol_section_max: int = 1200
    ):
        self.chunker = ProtocolAwareChunker(
            chunk_size=chunk_size,
            min_chunk_size=min_chunk_size,
            protocol_section_max=protocol_section_max
        )

    def chunk(
        self,
        text: str,
        doc_id: str,
        doc_type: str,
        metadata: Dict[str, Any] = None
    ):
        """
        Chunk method compatible with BaseChunker interface

        Returns ChunkWrapper objects with .to_dict() method
        """
        # Use the protocol-aware chunker
        chunks = self.chunker.chunk_document(text, doc_id, doc_type, metadata)

        # Convert to format compatible with hierarchical chunking system
        wrapped_chunks = []
        for i, chunk in enumerate(chunks):
            # Ensure required fields
            if 'id' not in chunk:
                chunk['id'] = f"{doc_id}_protocol_{i}"
            if 'chunk_type' not in chunk:
                chunk['chunk_type'] = 'flat'
            if 'section' not in chunk.get('metadata', {}):
                if 'metadata' not in chunk:
                    chunk['metadata'] = {}
                chunk['metadata']['section'] = chunk.get('metadata', {}).get('section', 'Protocol')

            # Add optional fields expected by document processor
            chunk['parent_id'] = chunk.get('parent_id')
            chunk['children_ids'] = chunk.get('children_ids', [])
            chunk['section'] = chunk.get('metadata', {}).get('section', 'Protocol')
            chunk['char_start'] = chunk.get('char_start', 0)
            chunk['char_end'] = chunk.get('char_end', 0)

            wrapped_chunks.append(ChunkWrapper(chunk))

        return wrapped_chunks


# Integration helper
def chunk_protocol_document(
    text: str,
    doc_id: str,
    doc_type: str = "protocol",
    metadata: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function for protocol chunking

    Usage:
        chunks = chunk_protocol_document(
            text=pdf_text,
            doc_id="plinest_hair_protocol",
            doc_type="protocol"
        )
    """
    chunker = ProtocolAwareChunker()
    return chunker.chunk_document(text, doc_id, doc_type, metadata)
