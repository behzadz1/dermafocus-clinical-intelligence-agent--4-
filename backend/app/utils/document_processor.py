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

from .chunking import TextChunker, TableChunker, Chunk
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
        use_hierarchical: bool = True,
        enable_image_analysis: bool = False
    ):
        """
        Args:
            chunk_size: Target size for text chunks (used for legacy chunking)
            chunk_overlap: Overlap between chunks for context
            use_hierarchical: Use hybrid hierarchical chunking (recommended)
            enable_image_analysis: Enable Claude Vision API for image descriptions (adds cost)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_hierarchical = use_hierarchical
        self.enable_image_analysis = enable_image_analysis
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

        # Combine all pages while preserving page-level character spans
        full_text, page_spans = self._build_full_text_with_page_spans(pages)

        # Extract tables (optional, using pdfplumber)
        tables = self._extract_tables(file_path)

        # Create table chunks from extracted tables
        table_chunks = self._create_table_chunks(tables, metadata)

        # Extract images (optional, using PyMuPDF)
        images = self._extract_images(file_path)

        # Create image chunks with descriptions (if enabled)
        page_texts = {page["page_number"]: page["text"] for page in pages}
        image_chunks = self._create_image_chunks(images, metadata, page_texts)

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

            # Attach page provenance for reliable citations downstream.
            self._attach_page_provenance_to_chunks(chunks, full_text, page_spans)

            # Integrate table chunks into main chunk list
            if table_chunks:
                chunks.extend(table_chunks)
                print(f"  Added {len(table_chunks)} table chunks")

            # Integrate image chunks into main chunk list
            if image_chunks:
                chunks.extend(image_chunks)
                print(f"  Added {len(image_chunks)} image chunks")

            # Track parent-child relationships
            parent_chunks = [c for c in chunks if c.get("chunk_type") == "section"]
            child_chunks = [c for c in chunks if c.get("chunk_type") == "detail"]
            flat_chunks = [c for c in chunks if c.get("chunk_type") == "flat"]
            table_chunk_list = [c for c in chunks if c.get("chunk_type") == "table"]
            image_chunk_list = [c for c in chunks if c.get("chunk_type") == "image"]

            chunking_strategy = ChunkingStrategyFactory.get_chunker(detected_type).__class__.__name__
        else:
            # Legacy chunking
            chunks = self._create_chunks(pages, metadata)

            # Add table chunks to legacy chunks as well
            if table_chunks:
                chunks.extend(table_chunks)

            # Add image chunks to legacy chunks as well
            if image_chunks:
                chunks.extend(image_chunks)

            hierarchical_chunks = []
            parent_chunks = []
            child_chunks = []
            flat_chunks = [c for c in chunks if c.get("chunk_type") not in ["table", "image"]]
            table_chunk_list = [c for c in chunks if c.get("chunk_type") == "table"]
            image_chunk_list = [c for c in chunks if c.get("chunk_type") == "image"]
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
            "images": images,
            "chunking_strategy": chunking_strategy,
            "stats": {
                "num_pages": len(pages),
                "num_chunks": len(chunks),
                "num_parent_chunks": len(parent_chunks),
                "num_child_chunks": len(child_chunks),
                "num_flat_chunks": len(flat_chunks),
                "num_table_chunks": len(table_chunk_list),
                "num_tables": len(tables),
                "num_image_chunks": len(image_chunk_list),
                "num_images": len(images),
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
                        # Accept tables with at least 1 row (may be single-row tables)
                        if table and len(table) >= 1:
                            # Check if this looks like a real table (not just text blocks)
                            if len(table[0]) > 1:  # Must have at least 2 columns
                                # If only one row, treat it as data (no separate header)
                                if len(table) == 1:
                                    headers = [f"Column {i+1}" for i in range(len(table[0]))]
                                    rows = table
                                else:
                                    headers = table[0]
                                    rows = table[1:]

                                tables.append({
                                    "page_number": page_num + 1,
                                    "table_index": table_idx,
                                    "headers": headers,
                                    "rows": rows,
                                    "num_rows": len(rows),
                                    "num_cols": len(table[0]) if table else 0
                                })
        except Exception as e:
            print(f"Warning: Could not extract tables: {e}")

        return tables

    def _create_table_chunks(
        self,
        tables: List[Dict[str, Any]],
        base_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Convert extracted tables to markdown chunks

        Args:
            tables: List of table dictionaries from _extract_tables
            base_metadata: Base metadata for chunks

        Returns:
            List of chunk dictionaries with markdown tables
        """
        table_chunks = []

        for table_info in tables:
            headers = table_info.get("headers", [])
            rows = table_info.get("rows", [])
            page_number = table_info.get("page_number")

            if not headers or not rows:
                continue

            # Create table context
            table_context = f"Table from page {page_number}:"

            # Create metadata for this table
            chunk_metadata = {
                **base_metadata,
                "page_number": page_number,
                "table_index": table_info.get("table_index", 0)
            }

            # Use TableChunker to create markdown table chunk
            chunks = TableChunker.chunk_table(
                table_data=rows,
                headers=headers,
                base_metadata=chunk_metadata,
                as_markdown=True,
                table_context=table_context
            )

            # Convert Chunk objects to dicts
            for chunk in chunks:
                doc_id = base_metadata.get("doc_id", "unknown")
                table_chunks.append({
                    "text": chunk.text,
                    "chunk_id": f"{doc_id}_table_p{page_number}_t{table_info.get('table_index', 0)}",
                    "metadata": chunk.metadata,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    "chunk_type": "table"
                })

        return table_chunks

    def _extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract images from PDF using PyMuPDF (fitz)

        Args:
            file_path: Path to PDF

        Returns:
            List of image dictionaries with image data and metadata
        """
        images = []

        try:
            doc = fitz.open(file_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)

                for img_idx, img_info in enumerate(image_list):
                    xref = img_info[0]  # Image XREF

                    # Extract image bytes
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        width = base_image.get("width", 0)
                        height = base_image.get("height", 0)

                        # Filter out very small images (likely icons/logos)
                        if width < 100 or height < 100:
                            continue

                        # Get image position on page
                        img_rect = page.get_image_rects(xref)
                        position = img_rect[0] if img_rect else None

                        images.append({
                            "page_number": page_num + 1,
                            "image_index": img_idx,
                            "xref": xref,
                            "image_bytes": image_bytes,
                            "image_ext": image_ext,
                            "width": width,
                            "height": height,
                            "position": position,
                            "size_bytes": len(image_bytes)
                        })

                    except Exception as e:
                        print(f"Warning: Could not extract image {xref} from page {page_num + 1}: {e}")
                        continue

            doc.close()
            print(f"  Extracted {len(images)} images from PDF")

        except Exception as e:
            print(f"Warning: Could not extract images: {e}")

        return images

    def _create_image_chunks(
        self,
        images: List[Dict[str, Any]],
        base_metadata: Dict[str, Any],
        page_texts: Dict[int, str] = None
    ) -> List[Dict[str, Any]]:
        """
        Create image chunks with Claude Vision descriptions

        Args:
            images: List of image dictionaries from _extract_images
            base_metadata: Base metadata for chunks
            page_texts: Dict mapping page numbers to page text for context

        Returns:
            List of chunk dictionaries with image descriptions
        """
        if not self.enable_image_analysis or not images:
            return []

        image_chunks = []

        try:
            # Import vision service
            from app.services.vision_service import get_vision_service
            vision_service = get_vision_service()

            print(f"  Analyzing {len(images)} images with Claude Vision API...")

            for image_info in images:
                page_number = image_info.get("page_number")
                image_bytes = image_info.get("image_bytes")
                image_ext = image_info.get("image_ext", "png")

                if not image_bytes:
                    continue

                # Get page context if available
                page_context = ""
                if page_texts and page_number in page_texts:
                    page_context = page_texts[page_number][:500]  # First 500 chars

                # Generate description using Claude Vision
                result = vision_service.describe_image(
                    image_bytes=image_bytes,
                    image_type=image_ext,
                    context=page_context,
                    max_tokens=500
                )

                description = result.get("description")
                if not description:
                    print(f"    ⚠ Failed to describe image on page {page_number}: {result.get('error', 'unknown error')}")
                    continue

                # Create image chunk metadata
                chunk_metadata = {
                    **base_metadata,
                    "page_number": page_number,
                    "image_index": image_info.get("image_index", 0),
                    "is_image": True,
                    "image_width": image_info.get("width"),
                    "image_height": image_info.get("height"),
                    "image_size_bytes": image_info.get("size_bytes"),
                    "vision_model": result.get("model", "unknown"),
                    "vision_confidence": result.get("confidence", 0.9)
                }

                doc_id = base_metadata.get("doc_id", "unknown")
                image_chunk = {
                    "text": f"Image from page {page_number}:\n\n{description}",
                    "chunk_id": f"{doc_id}_image_p{page_number}_i{image_info.get('image_index', 0)}",
                    "metadata": chunk_metadata,
                    "char_start": 0,
                    "char_end": len(description),
                    "chunk_type": "image"
                }

                image_chunks.append(image_chunk)
                print(f"    ✓ Page {page_number}: Image described ({len(description)} chars)")

        except ImportError:
            print("  ⚠ Vision service not available - skipping image analysis")
        except Exception as e:
            print(f"  ⚠ Error creating image chunks: {e}")

        return image_chunks

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

    def _build_full_text_with_page_spans(
        self,
        pages: List[Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, int]]]:
        """
        Build full text and track per-page character spans for provenance.

        Returns:
            Tuple of (full_text, page_spans)
            where page_spans entries are {"page_number": int, "start": int, "end": int}
        """
        full_text_parts: List[str] = []
        page_spans: List[Dict[str, int]] = []
        cursor = 0
        separator = "\n\n"

        for page in pages:
            page_text = (page.get("text") or "").strip()
            if not page_text:
                continue

            if full_text_parts:
                cursor += len(separator)

            start = cursor
            end = start + len(page_text)
            page_spans.append({
                "page_number": int(page.get("page_number", 0) or 0),
                "start": start,
                "end": end
            })

            full_text_parts.append(page_text)
            cursor = end

        return separator.join(full_text_parts), page_spans

    def _attach_page_provenance_to_chunks(
        self,
        chunks: List[Dict[str, Any]],
        full_text: str,
        page_spans: List[Dict[str, int]]
    ) -> None:
        """
        Add page_number/page_start/page_end metadata to chunks.
        """
        if not chunks or not page_spans:
            return

        search_cursor = 0

        for chunk in chunks:
            metadata = chunk.setdefault("metadata", {})
            start = chunk.get("char_start")
            end = chunk.get("char_end")

            # Some chunkers don't provide reliable offsets; derive best-effort offsets.
            if not isinstance(start, int) or not isinstance(end, int) or end <= start:
                chunk_text = (chunk.get("text") or "").strip()
                if chunk_text and full_text:
                    probe = chunk_text[:160]
                    found_at = full_text.find(probe, search_cursor)
                    if found_at == -1:
                        found_at = full_text.find(probe)
                    if found_at != -1:
                        start = found_at
                        end = found_at + len(probe)
                        search_cursor = found_at + len(probe)

            pages = []
            if isinstance(start, int) and isinstance(end, int) and end > start:
                for span in page_spans:
                    overlap_start = max(start, span["start"])
                    overlap_end = min(end, span["end"])
                    if overlap_start < overlap_end:
                        pages.append(span["page_number"])

            # Fallback to existing metadata if overlap matching failed.
            if not pages:
                fallback_page = metadata.get("page_number")
                if isinstance(fallback_page, int) and fallback_page > 0:
                    pages = [fallback_page]

            if pages:
                metadata["page_number"] = pages[0]
                metadata["page_start"] = pages[0]
                metadata["page_end"] = pages[-1]

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

        # Normalize line endings and keep line structure for section detection.
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove extra spaces/tabs while preserving newlines.
        text = re.sub(r"[ \t]+", " ", text)
        text = "\n".join(line.strip() for line in text.split("\n"))
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove standalone page number lines (e.g., "Page 1", "1/10")
        text = re.sub(r"(?im)^\s*Page\s+\d+\s*$", "", text)
        text = re.sub(r"(?m)^\s*\d+/\d+\s*$", "", text)
        
        # Remove common PDF artifacts
        text = re.sub(r'\x00', '', text)  # Null bytes
        text = re.sub(r'\ufffd', '', text)  # Replacement characters
        
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
