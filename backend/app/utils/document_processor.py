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


class DocumentProcessor:
    """
    Processes documents (primarily PDFs) for RAG ingestion
    Extracts text, metadata, structure, and prepares chunks
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Args:
            chunk_size: Target size for text chunks
            chunk_overlap: Overlap between chunks for context
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker = TextChunker(chunk_size, chunk_overlap)
    
    def process_pdf(
        self,
        file_path: str,
        doc_id: str = None,
        doc_type: str = "document"
    ) -> Dict[str, Any]:
        """
        Process a PDF file completely
        
        Args:
            file_path: Path to PDF file
            doc_id: Unique document identifier
            doc_type: Type of document (product, protocol, clinical_paper, etc.)
            
        Returns:
            Dictionary with processed document data:
            {
                "doc_id": str,
                "doc_type": str,
                "metadata": dict,
                "full_text": str,
                "pages": list,
                "chunks": list,
                "tables": list
            }
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Generate doc_id if not provided
        if not doc_id:
            doc_id = Path(file_path).stem
        
        print(f"Processing PDF: {file_path}")
        
        # Extract metadata
        metadata = self._extract_pdf_metadata(file_path)
        metadata["doc_id"] = doc_id
        metadata["doc_type"] = doc_type
        metadata["source_file"] = os.path.basename(file_path)
        metadata["processed_at"] = datetime.utcnow().isoformat()
        
        # Extract text by page
        pages = self._extract_text_by_page(file_path)
        
        # Combine all pages
        full_text = "\n\n".join(page["text"] for page in pages if page["text"])
        
        # Extract tables (optional, using pdfplumber)
        tables = self._extract_tables(file_path)
        
        # Create chunks
        chunks = self._create_chunks(pages, metadata)
        
        return {
            "doc_id": doc_id,
            "doc_type": doc_type,
            "metadata": metadata,
            "full_text": full_text,
            "pages": pages,
            "chunks": chunks,
            "tables": tables,
            "stats": {
                "num_pages": len(pages),
                "num_chunks": len(chunks),
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
        doc_type: str = "document",
        file_pattern: str = "*.pdf"
    ) -> List[Dict[str, Any]]:
        """
        Process all PDFs in a directory
        
        Args:
            directory: Path to directory
            doc_type: Type of documents
            file_pattern: Glob pattern for files
            
        Returns:
            List of processed document results
        """
        directory_path = Path(directory)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        # Find all matching files
        pdf_files = list(directory_path.glob(file_pattern))
        
        print(f"Found {len(pdf_files)} files in {directory}")
        
        results = []
        for pdf_file in pdf_files:
            try:
                result = self.processor.process_pdf(
                    str(pdf_file),
                    doc_id=pdf_file.stem,
                    doc_type=doc_type
                )
                results.append({
                    "success": True,
                    "file": str(pdf_file),
                    "result": result
                })
                print(f"✓ Processed: {pdf_file.name}")
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
            Summary dictionary
        """
        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total - successful
        
        total_chunks = sum(
            r["result"]["stats"]["num_chunks"]
            for r in self.results
            if r["success"]
        )
        
        return {
            "total_files": total,
            "successful": successful,
            "failed": failed,
            "total_chunks": total_chunks,
            "success_rate": successful / total if total > 0 else 0
        }
