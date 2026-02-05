"""
Citation Service for DermaFocus

Generates clickable citations that link to source PDFs with page numbers.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from urllib.parse import quote
import structlog

logger = structlog.get_logger()


@dataclass
class Citation:
    """A citation reference to a source document"""
    citation_id: int
    doc_id: str
    doc_title: str
    doc_type: str
    page_number: Optional[int]
    section: Optional[str]
    relevance_score: float
    file_path: str
    chunk_text: str  # The actual text that was retrieved

    def to_markdown_link(self, base_url: str = "/api/documents/view") -> str:
        """Generate markdown link for citation"""
        params = f"?doc_id={quote(self.doc_id)}"
        if self.page_number:
            params += f"&page={self.page_number}"

        label = self.doc_title
        if self.section:
            label += f" - {self.section}"
        if self.page_number:
            label += f" (p.{self.page_number})"

        return f"[{label}]({base_url}{params})"

    def to_inline_reference(self) -> str:
        """Generate inline reference marker like [1]"""
        return f"[{self.citation_id}]"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "citation_id": self.citation_id,
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "doc_type": self.doc_type,
            "page_number": self.page_number,
            "section": self.section,
            "relevance_score": self.relevance_score,
            "file_path": self.file_path,
            "preview_text": self.chunk_text[:200] + "..." if len(self.chunk_text) > 200 else self.chunk_text,
            "view_url": f"/api/documents/view?doc_id={quote(self.doc_id)}" + (f"&page={self.page_number}" if self.page_number else "")
        }


class CitationService:
    """
    Service for generating and managing citations in responses
    """

    def __init__(self, uploads_dir: str = "data/uploads"):
        self.uploads_dir = Path(uploads_dir)
        self._doc_path_cache: Dict[str, str] = {}
        self._build_doc_path_cache()

    def _build_doc_path_cache(self):
        """Build cache of doc_id to file path mappings"""
        if not self.uploads_dir.exists():
            logger.warning("Uploads directory not found", path=str(self.uploads_dir))
            return

        for pdf_file in self.uploads_dir.rglob("*.pdf"):
            doc_id = pdf_file.stem
            self._doc_path_cache[doc_id] = str(pdf_file)
            # Also cache normalized version (lowercase, no special chars)
            normalized = self._normalize_doc_id(doc_id)
            self._doc_path_cache[normalized] = str(pdf_file)

        logger.info("Document path cache built", document_count=len(self._doc_path_cache) // 2)

    def _normalize_doc_id(self, doc_id: str) -> str:
        """Normalize doc_id for matching"""
        return re.sub(r'[^a-z0-9]', '', doc_id.lower())

    def get_document_path(self, doc_id: str) -> Optional[str]:
        """Get file path for a document ID"""
        # Try exact match first
        if doc_id in self._doc_path_cache:
            return self._doc_path_cache[doc_id]

        # Try normalized match
        normalized = self._normalize_doc_id(doc_id)
        if normalized in self._doc_path_cache:
            return self._doc_path_cache[normalized]

        # Try partial match
        for cached_id, path in self._doc_path_cache.items():
            if normalized in self._normalize_doc_id(cached_id):
                return path

        return None

    def get_document_title(self, doc_id: str) -> str:
        """Get human-readable title from doc_id"""
        # Clean up the doc_id to create a title
        title = doc_id.replace("_", " ").replace("-", " ")
        # Remove common suffixes
        title = re.sub(r'\s*(processed|final|v\d+)$', '', title, flags=re.IGNORECASE)
        # Title case
        title = title.title()
        # Fix common terms - only add ® if not already present
        title = title.replace("Pn Hpt", "PN-HPT®")
        if "Plinest" in title and "Plinest®" not in title:
            title = title.replace("Plinest", "Plinest®")
        if "Newest" in title and "Newest®" not in title:
            title = title.replace("Newest", "Newest®")
        return title

    def create_citations_from_sources(
        self,
        sources: List[Dict[str, Any]]
    ) -> List[Citation]:
        """
        Create citation objects from RAG source results

        Args:
            sources: List of source dictionaries from RAG service

        Returns:
            List of Citation objects
        """
        citations = []

        for i, source in enumerate(sources, 1):
            doc_id = source.get("doc_id", "")
            file_path = self.get_document_path(doc_id) or ""

            citation = Citation(
                citation_id=i,
                doc_id=doc_id,
                doc_title=self.get_document_title(doc_id),
                doc_type=source.get("doc_type", "unknown"),
                page_number=source.get("page"),
                section=source.get("section"),
                relevance_score=source.get("relevance_score", 0),
                file_path=file_path,
                chunk_text=source.get("text", "")
            )
            citations.append(citation)

        return citations

    def format_response_with_citations(
        self,
        response_text: str,
        citations: List[Citation],
        citation_style: str = "footnote"  # "footnote", "inline", "endnote"
    ) -> Dict[str, Any]:
        """
        Format response text with citation references and generate citation list

        Args:
            response_text: The LLM-generated response
            citations: List of Citation objects
            citation_style: How to format citations

        Returns:
            Dictionary with formatted response and citation data
        """
        if citation_style == "inline":
            # Add inline citations like [Source: Document Name]
            citations_section = self._generate_inline_citations(citations)
            formatted_response = response_text + "\n\n" + citations_section

        elif citation_style == "footnote":
            # Add numbered footnotes [1], [2] with references at end
            formatted_response, citation_map = self._add_footnote_markers(response_text, citations)
            footnotes = self._generate_footnotes(citations)
            formatted_response = formatted_response + "\n\n---\n\n**Sources:**\n" + footnotes

        else:  # endnote
            # Simple list at the end
            formatted_response = response_text + "\n\n---\n\n**References:**\n"
            for citation in citations:
                formatted_response += f"- {citation.to_markdown_link()}\n"

        return {
            "formatted_response": formatted_response,
            "citations": [c.to_dict() for c in citations],
            "citation_style": citation_style
        }

    def _generate_inline_citations(self, citations: List[Citation]) -> str:
        """Generate inline citation section"""
        lines = ["**Sources:**"]
        for citation in citations:
            lines.append(f"- {citation.to_markdown_link()}")
        return "\n".join(lines)

    def _add_footnote_markers(
        self,
        text: str,
        citations: List[Citation]
    ) -> tuple[str, Dict[int, Citation]]:
        """
        Attempt to add footnote markers to relevant parts of text
        Returns modified text and citation map
        """
        # For now, we don't modify the text inline
        # A more sophisticated approach would use NLP to match citations to sentences
        return text, {c.citation_id: c for c in citations}

    def _generate_footnotes(self, citations: List[Citation]) -> str:
        """Generate footnote references"""
        lines = []
        for citation in citations:
            line = f"[{citation.citation_id}] {citation.to_markdown_link()}"
            if citation.relevance_score:
                line += f" (relevance: {citation.relevance_score:.0%})"
            lines.append(line)
        return "\n".join(lines)


# Singleton instance
_citation_service: Optional[CitationService] = None


def get_citation_service() -> CitationService:
    """Get singleton citation service instance"""
    global _citation_service
    if _citation_service is None:
        _citation_service = CitationService()
    return _citation_service
