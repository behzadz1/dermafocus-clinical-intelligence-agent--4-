"""
Document Processing for RAG
Extracts text, tables, and metadata from PDFs
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

# PDF processing libraries
try:
    import PyPDF2
    import pdfplumber
    import fitz  # PyMuPDF
except ImportError:
    print("Warning: PDF libraries not installed. Run: pip install PyPDF2 pdfplumber pymupdf")

from .chunking import TextChunker, Chunk
from .hierarchical_chunking import (
    ChunkingStrategyFactory,
    HierarchicalChunk,
    DocumentType,
    ChunkType,
    chunk_document_hybrid
)


class DocumentProcessor:
    """
    Processes documents (primarily PDFs) for RAG ingestion
    Extracts text, metadata, structure, and prepares chunks
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        use_hierarchical: bool = True
    ):
        """
        Args:
            chunk_size: Target size for text chunks (used for legacy chunking)
            chunk_overlap: Overlap between chunks for context
            use_hierarchical: Use hybrid hierarchical chunking (recommended)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_hierarchical = use_hierarchical
        self.chunker = TextChunker(chunk_size, chunk_overlap)
    
    def process_pdf(
        self,
        file_path: str,
        doc_id: str = None,
        doc_type: str = None,
        folder_name: str = None
    ) -> Dict[str, Any]:
        """
        Process a PDF file completely with hybrid hierarchical chunking

        Args:
            file_path: Path to PDF file
            doc_id: Unique document identifier
            doc_type: Type of document (auto-detected if not provided)
            folder_name: Folder name for document type detection

        Returns:
            Dictionary with processed document data:
            {
                "doc_id": str,
                "doc_type": str,
                "detected_type": str,
                "metadata": dict,
                "full_text": str,
                "pages": list,
                "chunks": list,
                "hierarchical_chunks": list,
                "tables": list,
                "chunking_strategy": str
            }
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate doc_id if not provided
        if not doc_id:
            doc_id = Path(file_path).stem

        # Extract folder name from path if not provided
        if not folder_name:
            folder_name = Path(file_path).parent.name

        print(f"Processing PDF: {file_path}")

        # Extract metadata
        metadata = self._extract_pdf_metadata(file_path)
        metadata["doc_id"] = doc_id
        metadata["source_file"] = os.path.basename(file_path)
        metadata["processed_at"] = datetime.utcnow().isoformat()
        metadata["folder_name"] = folder_name

        # Extract text by page
        pages = self._extract_text_by_page(file_path)

        # Combine all pages
        full_text = "\n\n".join(page["text"] for page in pages if page["text"])

        # Extract tables (optional, using pdfplumber)
        tables = self._extract_tables(file_path)

        # Detect document type if not provided
        if not doc_type or doc_type == "document":
            detected_type = ChunkingStrategyFactory.detect_document_type(
                text=full_text,
                file_path=file_path,
                folder_name=folder_name
            )
            doc_type = detected_type.value
        else:
            detected_type = DocumentType(doc_type) if doc_type in [dt.value for dt in DocumentType] else DocumentType.UNKNOWN

        metadata["doc_type"] = doc_type
        metadata["detected_type"] = detected_type.value

        # Create chunks using appropriate strategy
        if self.use_hierarchical:
            # Use hybrid hierarchical chunking
            hierarchical_chunks, _ = ChunkingStrategyFactory.chunk_document(
                text=full_text,
                doc_id=doc_id,
                file_path=file_path,
                folder_name=folder_name,
                metadata=metadata
            )

            # Convert to storage format
            chunks = [chunk.to_dict() for chunk in hierarchical_chunks]

            # Track parent-child relationships
            parent_chunks = [c for c in chunks if c.get("chunk_type") == "section"]
            child_chunks = [c for c in chunks if c.get("chunk_type") == "detail"]
            flat_chunks = [c for c in chunks if c.get("chunk_type") == "flat"]

            chunking_strategy = ChunkingStrategyFactory.get_chunker(detected_type).__class__.__name__
        else:
            # Legacy chunking
            chunks = self._create_chunks(pages, metadata)
            hierarchical_chunks = []
            parent_chunks = []
            child_chunks = []
            flat_chunks = chunks
            chunking_strategy = "TextChunker (legacy)"

        return {
            "doc_id": doc_id,
            "doc_type": doc_type,
            "detected_type": detected_type.value,
            "metadata": metadata,
            "full_text": full_text,
            "pages": pages,
            "chunks": chunks,
            "tables": tables,
            "chunking_strategy": chunking_strategy,
            "stats": {
                "num_pages": len(pages),
                "num_chunks": len(chunks),
                "num_parent_chunks": len(parent_chunks),
                "num_child_chunks": len(child_chunks),
                "num_flat_chunks": len(flat_chunks),
                "num_tables": len(tables),
                "total_chars": len(full_text)
            }
        }
    
    def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from PDF
        
        Args:
            file_path: Path to PDF
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        try:
            with open(file_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                
                # Basic metadata
                if pdf.metadata:
                    metadata["title"] = pdf.metadata.get("/Title", "")
                    metadata["author"] = pdf.metadata.get("/Author", "")
                    metadata["subject"] = pdf.metadata.get("/Subject", "")
                    metadata["creator"] = pdf.metadata.get("/Creator", "")
                    metadata["producer"] = pdf.metadata.get("/Producer", "")
                
                metadata["num_pages"] = len(pdf.pages)
        except Exception as e:
            print(f"Warning: Could not extract metadata: {e}")
            metadata["num_pages"] = 0
        
        return metadata
    
    def _extract_text_by_page(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from each page of PDF
        
        Args:
            file_path: Path to PDF
            
        Returns:
            List of page dictionaries with text and metadata
        """
        pages = []
        
        try:
            # Use PyMuPDF (fitz) for better text extraction
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Clean text
                text = self._clean_text(text)
                
                # Detect if this is likely a title/header page
                is_header_page = page_num == 0 or len(text) < 200
                
                pages.append({
                    "page_number": page_num + 1,  # 1-indexed for humans
                    "text": text,
                    "char_count": len(text),
                    "is_header_page": is_header_page
                })
            
            doc.close()
            
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            # Fallback to PyPDF2
            try:
                with open(file_path, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    for page_num in range(len(pdf.pages)):
                        page = pdf.pages[page_num]
                        text = page.extract_text()
                        text = self._clean_text(text)
                        
                        pages.append({
                            "page_number": page_num + 1,
                            "text": text,
                            "char_count": len(text),
                            "is_header_page": False
                        })
            except Exception as e2:
                print(f"Fallback also failed: {e2}")
        
        return pages
    
    def _extract_tables(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract tables from PDF using pdfplumber
        
        Args:
            file_path: Path to PDF
            
        Returns:
            List of table dictionaries
        """
        tables = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(page_tables):
                        if table and len(table) > 1:  # Must have headers + at least 1 row
                            tables.append({
                                "page_number": page_num + 1,
                                "table_index": table_idx,
                                "headers": table[0],
                                "rows": table[1:],
                                "num_rows": len(table) - 1,
                                "num_cols": len(table[0]) if table else 0
                            })
        except Exception as e:
            print(f"Warning: Could not extract tables: {e}")
        
        return tables
    
    def _create_chunks(
        self,
        pages: List[Dict[str, Any]],
        base_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create chunks from pages
        
        Args:
            pages: List of page dictionaries
            base_metadata: Base metadata to include in all chunks
            
        Returns:
            List of chunk dictionaries
        """
        all_chunks = []
        
        for page in pages:
            page_text = page["text"]
            if not page_text or len(page_text.strip()) < 50:
                continue
            
            # Create metadata for this page's chunks
            chunk_metadata = {
                **base_metadata,
                "page_number": page["page_number"]
            }
            
            # Chunk the page text
            page_chunks = self.chunker.chunk_text(page_text, chunk_metadata)
            
            # Convert to dictionaries
            for chunk in page_chunks:
                all_chunks.append({
                    "text": chunk.text,
                    "chunk_id": f"{base_metadata['doc_id']}_page{page['page_number']}_chunk{chunk.chunk_id}",
                    "metadata": chunk.metadata
                })
        
        return all_chunks
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers at end of lines (e.g., "Page 1", "1/10")
        text = re.sub(r'\s+Page\s+\d+\s*$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+\d+/\d+\s*$', '', text)
        
        # Remove common PDF artifacts
        text = re.sub(r'\x00', '', text)  # Null bytes
        text = re.sub(r'\ufffd', '', text)  # Replacement characters
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace("'", "'").replace("'", "'")
        
        return text.strip()
    
    def extract_product_info(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract structured product information from chunks
        Looks for common patterns in product factsheets
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Structured product information
        """
        product_info = {
            "name": None,
            "composition": None,
            "indications": [],
            "dosing": None,
            "technique": None,
            "contraindications": []
        }
        
        full_text = " ".join(chunk["text"] for chunk in chunks)
        
        # Extract product name (usually in title or first chunk)
        name_patterns = [
            r'(?:Product|Name):\s*([A-Za-z®]+)',
            r'([A-Z][a-z]+®)',  # Words with ® symbol
        ]
        for pattern in name_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                product_info["name"] = match.group(1)
                break
        
        # Extract composition
        comp_match = re.search(
            r'(?:Composition|Contains?):\s*([^.]+)',
            full_text,
            re.IGNORECASE
        )
        if comp_match:
            product_info["composition"] = comp_match.group(1).strip()
        
        # Extract dosing
        dose_match = re.search(
            r'(?:Dosing|Dose|Protocol):\s*([^.]+)',
            full_text,
            re.IGNORECASE
        )
        if dose_match:
            product_info["dosing"] = dose_match.group(1).strip()
        
        return product_info


class DocumentBatch:
    """
    Process multiple documents in batch
    """
    
    def __init__(self, processor: DocumentProcessor = None):
        """
        Args:
            processor: DocumentProcessor instance (creates new if None)
        """
        self.processor = processor or DocumentProcessor()
        self.results = []
    
    def process_directory(
        self,
        directory: str,
        doc_type: str = None,
        file_pattern: str = "*.pdf",
        auto_detect_type: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process all PDFs in a directory with automatic type detection

        Args:
            directory: Path to directory
            doc_type: Type of documents (auto-detected from folder if None)
            file_pattern: Glob pattern for files
            auto_detect_type: Auto-detect document type from folder name

        Returns:
            List of processed document results
        """
        directory_path = Path(directory)

        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        # Find all matching files
        pdf_files = list(directory_path.glob(file_pattern))

        # Get folder name for type detection
        folder_name = directory_path.name

        print(f"Found {len(pdf_files)} files in {directory}")
        print(f"Folder name for type detection: {folder_name}")

        results = []
        for pdf_file in pdf_files:
            try:
                result = self.processor.process_pdf(
                    str(pdf_file),
                    doc_id=pdf_file.stem,
                    doc_type=doc_type,
                    folder_name=folder_name if auto_detect_type else None
                )
                results.append({
                    "success": True,
                    "file": str(pdf_file),
                    "detected_type": result.get("detected_type"),
                    "chunking_strategy": result.get("chunking_strategy"),
                    "result": result
                })
                print(f"✓ Processed: {pdf_file.name} (type: {result.get('detected_type')}, strategy: {result.get('chunking_strategy')})")
            except Exception as e:
                print(f"✗ Failed: {pdf_file.name} - {e}")
                results.append({
                    "success": False,
                    "file": str(pdf_file),
                    "error": str(e)
                })

        self.results = results
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of batch processing

        Returns:
            Summary dictionary with hierarchical chunk breakdown
        """
        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total - successful

        # Aggregate chunk statistics
        total_chunks = 0
        total_parent_chunks = 0
        total_child_chunks = 0
        total_flat_chunks = 0
        doc_types = {}
        strategies = {}

        for r in self.results:
            if r["success"]:
                stats = r["result"]["stats"]
                total_chunks += stats.get("num_chunks", 0)
                total_parent_chunks += stats.get("num_parent_chunks", 0)
                total_child_chunks += stats.get("num_child_chunks", 0)
                total_flat_chunks += stats.get("num_flat_chunks", 0)

                # Track document types
                detected_type = r.get("detected_type", "unknown")
                doc_types[detected_type] = doc_types.get(detected_type, 0) + 1

                # Track chunking strategies
                strategy = r.get("chunking_strategy", "unknown")
                strategies[strategy] = strategies.get(strategy, 0) + 1

        return {
            "total_files": total,
            "successful": successful,
            "failed": failed,
            "total_chunks": total_chunks,
            "chunk_breakdown": {
                "parent_chunks": total_parent_chunks,
                "child_chunks": total_child_chunks,
                "flat_chunks": total_flat_chunks
            },
            "document_types": doc_types,
            "chunking_strategies": strategies,
            "success_rate": successful / total if total > 0 else 0
        }
