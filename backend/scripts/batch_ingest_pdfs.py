#!/usr/bin/env python3
"""
Batch PDF Ingestion Script for RAG
==================================
Optimized for processing multiple PDFs (30+) with:
- Progress tracking and ETA
- Rate limiting for API calls
- Resumable processing (skip already processed)
- Comprehensive error handling and recovery
- Detailed logging and summary report

Usage:
    python scripts/batch_ingest_pdfs.py /path/to/pdfs/
    python scripts/batch_ingest_pdfs.py /path/to/pdfs/ --dry-run
    python scripts/batch_ingest_pdfs.py /path/to/pdfs/ --force  # Re-process all
"""

import os
import sys
import json
import time
import hashlib
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
import traceback

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import required libraries
try:
    import fitz  # PyMuPDF - best for text extraction
    from openai import OpenAI
    from pinecone import Pinecone
except ImportError as e:
    print(f"Missing required library: {e}")
    print("\nInstall with:")
    print("  pip install pymupdf openai pinecone-client")
    sys.exit(1)

# Optional: Try to load from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # dotenv not installed, rely on environment variables


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class Config:
    """Processing configuration"""
    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_length: int = 50

    # API settings
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 100  # OpenAI allows up to 2048
    pinecone_batch_size: int = 100

    # Rate limiting (requests per minute)
    openai_rpm_limit: int = 3000
    delay_between_docs: float = 0.5  # seconds

    # Pinecone
    index_name: str = "dermaai-ckpa"
    namespace: str = "default"

    # Processing
    processed_log_file: str = "processed_documents.json"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ProcessingStats:
    """Track processing statistics"""
    total_files: int = 0
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    total_pages: int = 0
    total_chunks: int = 0
    total_vectors: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    errors: List[Dict[str, str]] = field(default_factory=list)

    @property
    def elapsed(self) -> timedelta:
        return datetime.now() - self.start_time

    @property
    def success_rate(self) -> float:
        total = self.processed + self.failed
        return (self.processed / total * 100) if total > 0 else 0

    def eta(self) -> Optional[timedelta]:
        if self.processed == 0:
            return None
        remaining = self.total_files - (self.processed + self.skipped + self.failed)
        avg_time = self.elapsed / self.processed
        return avg_time * remaining


@dataclass
class DocumentResult:
    """Result of processing a single document"""
    file_path: str
    doc_id: str
    success: bool
    pages: int = 0
    chunks: int = 0
    vectors_uploaded: int = 0
    error: Optional[str] = None
    processing_time: float = 0


# =============================================================================
# Text Processing
# =============================================================================

def clean_text(text: str) -> str:
    """Clean extracted text from PDF artifacts"""
    if not text:
        return ""

    import re

    # Remove null bytes and replacement characters
    text = text.replace('\x00', '').replace('\ufffd', '')

    # Normalize whitespace (but preserve paragraph breaks)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove page numbers at end of lines
    text = re.sub(r'\s+Page\s+\d+\s*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'\s+\d+/\d+\s*$', '', text, flags=re.MULTILINE)

    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")

    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks, trying to break at sentence boundaries
    """
    if not text or len(text) < chunk_size:
        return [text] if text and len(text.strip()) > 50 else []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        # Calculate end position
        end = start + chunk_size

        if end >= text_len:
            # Last chunk
            chunk = text[start:].strip()
            if len(chunk) > 50:  # Minimum viable chunk
                chunks.append(chunk)
            break

        # Try to find a good break point (sentence end)
        break_point = end
        search_start = max(start + chunk_size - 200, start)  # Look back up to 200 chars

        # Look for sentence endings
        for punct in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
            last_punct = text.rfind(punct, search_start, end + 50)
            if last_punct > search_start:
                break_point = last_punct + 1
                break

        chunk = text[start:break_point].strip()
        if len(chunk) > 50:
            chunks.append(chunk)

        # Move start with overlap
        start = break_point - overlap if break_point > overlap else break_point

    return chunks


def generate_doc_id(filepath: str) -> str:
    """Generate stable document ID from filepath"""
    filename = Path(filepath).stem
    # Sanitize: lowercase, replace spaces/dashes with underscore
    doc_id = filename.lower().replace(" ", "_").replace("-", "_")
    # Keep only alphanumeric and underscore
    doc_id = "".join(c for c in doc_id if c.isalnum() or c == "_")
    # Ensure it doesn't start with a number
    if doc_id and doc_id[0].isdigit():
        doc_id = "doc_" + doc_id
    return doc_id or "unknown_doc"


def generate_vector_id(doc_id: str, page: int, chunk_idx: int, text: str) -> str:
    """Generate unique vector ID with content hash for deduplication"""
    content_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
    return f"{doc_id}::p{page}::c{chunk_idx}::{content_hash}"


# =============================================================================
# PDF Processing
# =============================================================================

def extract_pdf_text(filepath: str) -> Tuple[List[Dict], Dict]:
    """
    Extract text from PDF using PyMuPDF

    Returns:
        Tuple of (pages list, metadata dict)
    """
    pages = []
    metadata = {}

    try:
        doc = fitz.open(filepath)

        # Extract metadata
        metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "num_pages": len(doc),
            "file_size_kb": round(os.path.getsize(filepath) / 1024, 2)
        }

        # Extract text from each page
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            text = clean_text(text)

            if text and len(text.strip()) > 30:
                pages.append({
                    "page_number": page_num + 1,
                    "text": text,
                    "char_count": len(text)
                })

        doc.close()

    except Exception as e:
        raise Exception(f"Failed to extract PDF text: {e}")

    return pages, metadata


# =============================================================================
# Embedding & Upload
# =============================================================================

class BatchProcessor:
    """Handles batch embedding and vector upload"""

    def __init__(self, config: Config):
        self.config = config
        self.openai_client = None
        self.pinecone_index = None
        self._last_api_call = 0

    def initialize(self):
        """Initialize API clients"""
        # OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.openai_client = OpenAI(api_key=api_key)

        # Pinecone
        pinecone_key = os.getenv("PINECONE_API_KEY")
        if not pinecone_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
        pc = Pinecone(api_key=pinecone_key)
        self.pinecone_index = pc.Index(self.config.index_name)

        # Verify connection
        stats = self.pinecone_index.describe_index_stats()
        print(f"   Connected to Pinecone index: {self.config.index_name}")
        print(f"   Current vectors: {stats.total_vector_count:,}")

    def _rate_limit(self):
        """Simple rate limiting between API calls"""
        elapsed = time.time() - self._last_api_call
        min_interval = 60.0 / self.config.openai_rpm_limit
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_api_call = time.time()

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        if not texts:
            return []

        all_embeddings = []
        batch_size = self.config.embedding_batch_size

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Clean texts
            cleaned = [t.replace("\n", " ").strip() for t in batch]
            cleaned = [t for t in cleaned if t]  # Remove empty

            if not cleaned:
                continue

            self._rate_limit()

            try:
                response = self.openai_client.embeddings.create(
                    model=self.config.embedding_model,
                    input=cleaned
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                print(f"      Warning: Embedding batch failed: {e}")
                # Return empty embeddings for failed batch
                all_embeddings.extend([[] for _ in cleaned])

        return all_embeddings

    def upload_vectors(self, vectors: List[Dict]) -> int:
        """Upload vectors to Pinecone in batches"""
        if not vectors:
            return 0

        uploaded = 0
        batch_size = self.config.pinecone_batch_size

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            try:
                self.pinecone_index.upsert(
                    vectors=batch,
                    namespace=self.config.namespace
                )
                uploaded += len(batch)
            except Exception as e:
                print(f"      Warning: Upload batch failed: {e}")

        return uploaded


# =============================================================================
# Processing Log (for resumable processing)
# =============================================================================

class ProcessingLog:
    """Track which documents have been processed for resumable operations"""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.processed: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        """Load existing log"""
        if self.log_path.exists():
            try:
                with open(self.log_path, 'r') as f:
                    self.processed = json.load(f)
            except Exception:
                self.processed = {}

    def _save(self):
        """Save log to file"""
        with open(self.log_path, 'w') as f:
            json.dump(self.processed, f, indent=2, default=str)

    def is_processed(self, filepath: str) -> bool:
        """Check if file was already processed"""
        file_hash = self._get_file_hash(filepath)
        return file_hash in self.processed

    def mark_processed(self, filepath: str, result: DocumentResult):
        """Mark file as processed"""
        file_hash = self._get_file_hash(filepath)
        self.processed[file_hash] = {
            "file_path": filepath,
            "doc_id": result.doc_id,
            "processed_at": datetime.now().isoformat(),
            "pages": result.pages,
            "chunks": result.chunks,
            "vectors": result.vectors_uploaded,
            "success": result.success
        }
        self._save()

    def _get_file_hash(self, filepath: str) -> str:
        """Get hash of file for change detection"""
        stat = os.stat(filepath)
        # Hash based on path, size, and modification time
        key = f"{filepath}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(key.encode()).hexdigest()


# =============================================================================
# Main Processing Function
# =============================================================================

def process_single_document(
    filepath: str,
    processor: BatchProcessor,
    config: Config
) -> DocumentResult:
    """Process a single PDF document"""
    start_time = time.time()
    doc_id = generate_doc_id(filepath)
    doc_name = Path(filepath).name

    try:
        # Extract text
        pages, metadata = extract_pdf_text(filepath)

        if not pages:
            return DocumentResult(
                file_path=filepath,
                doc_id=doc_id,
                success=False,
                error="No text extracted from PDF"
            )

        # Create chunks
        all_chunks = []
        for page in pages:
            page_chunks = chunk_text(
                page["text"],
                config.chunk_size,
                config.chunk_overlap
            )
            for idx, chunk_text_content in enumerate(page_chunks):
                all_chunks.append({
                    "text": chunk_text_content,
                    "page": page["page_number"],
                    "chunk_idx": idx
                })

        if not all_chunks:
            return DocumentResult(
                file_path=filepath,
                doc_id=doc_id,
                success=False,
                pages=len(pages),
                error="No valid chunks created"
            )

        # Generate embeddings
        texts = [c["text"] for c in all_chunks]
        embeddings = processor.generate_embeddings(texts)

        if len(embeddings) != len(all_chunks):
            # Handle partial embedding failure
            print(f"      Warning: Got {len(embeddings)} embeddings for {len(all_chunks)} chunks")

        # Create vectors with metadata
        vectors = []
        for i, (chunk, embedding) in enumerate(zip(all_chunks, embeddings)):
            if not embedding:  # Skip failed embeddings
                continue

            vector_id = generate_vector_id(
                doc_id,
                chunk["page"],
                chunk["chunk_idx"],
                chunk["text"]
            )

            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "doc_id": doc_id,
                    "document_name": doc_name,
                    "page_number": chunk["page"],
                    "chunk_index": chunk["chunk_idx"],
                    "text": chunk["text"][:1000],  # Truncate for metadata limit
                    "total_pages": len(pages),
                    "upload_timestamp": datetime.now().isoformat()
                }
            })

        # Upload to Pinecone
        uploaded = processor.upload_vectors(vectors)

        return DocumentResult(
            file_path=filepath,
            doc_id=doc_id,
            success=True,
            pages=len(pages),
            chunks=len(all_chunks),
            vectors_uploaded=uploaded,
            processing_time=time.time() - start_time
        )

    except Exception as e:
        return DocumentResult(
            file_path=filepath,
            doc_id=doc_id,
            success=False,
            error=str(e),
            processing_time=time.time() - start_time
        )


def process_directory(
    input_dir: Path,
    config: Config,
    dry_run: bool = False,
    force: bool = False
) -> ProcessingStats:
    """Process all PDFs in a directory"""

    stats = ProcessingStats()

    # Find all PDFs
    pdf_files = sorted(input_dir.glob("*.pdf"))
    stats.total_files = len(pdf_files)

    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return stats

    print(f"\n{'='*60}")
    print(f"PDF Batch Ingestion for RAG")
    print(f"{'='*60}")
    print(f"Input directory: {input_dir}")
    print(f"PDF files found: {stats.total_files}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    # Initialize processor
    processor = BatchProcessor(config)

    if not dry_run:
        print("Initializing API connections...")
        processor.initialize()
        print()

    # Processing log for resumable operations
    log_path = input_dir / config.processed_log_file
    processing_log = ProcessingLog(log_path)

    # Process each file
    for idx, pdf_path in enumerate(pdf_files, 1):
        filename = pdf_path.name

        # Check if already processed (unless force flag)
        if not force and processing_log.is_processed(str(pdf_path)):
            print(f"[{idx}/{stats.total_files}] SKIP (already processed): {filename}")
            stats.skipped += 1
            continue

        # Progress display
        eta = stats.eta()
        eta_str = f" | ETA: {eta}" if eta else ""
        print(f"[{idx}/{stats.total_files}] Processing: {filename}{eta_str}")

        if dry_run:
            # Just extract and show info
            try:
                pages, metadata = extract_pdf_text(str(pdf_path))
                chunks = []
                for page in pages:
                    chunks.extend(chunk_text(page["text"], config.chunk_size, config.chunk_overlap))
                print(f"   Pages: {len(pages)}, Chunks: {len(chunks)}")
                stats.processed += 1
                stats.total_pages += len(pages)
                stats.total_chunks += len(chunks)
            except Exception as e:
                print(f"   ERROR: {e}")
                stats.failed += 1
                stats.errors.append({"file": filename, "error": str(e)})
        else:
            # Full processing
            result = process_single_document(str(pdf_path), processor, config)

            if result.success:
                print(f"   Pages: {result.pages}, Chunks: {result.chunks}, "
                      f"Vectors: {result.vectors_uploaded}, Time: {result.processing_time:.1f}s")
                stats.processed += 1
                stats.total_pages += result.pages
                stats.total_chunks += result.chunks
                stats.total_vectors += result.vectors_uploaded
                processing_log.mark_processed(str(pdf_path), result)
            else:
                print(f"   FAILED: {result.error}")
                stats.failed += 1
                stats.errors.append({"file": filename, "error": result.error})

        # Small delay between documents
        if not dry_run and idx < stats.total_files:
            time.sleep(config.delay_between_docs)

    return stats


def print_summary(stats: ProcessingStats, config: Config):
    """Print final summary"""
    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {stats.elapsed}")
    print(f"\nResults:")
    print(f"  Processed: {stats.processed}")
    print(f"  Skipped:   {stats.skipped}")
    print(f"  Failed:    {stats.failed}")
    print(f"  Success:   {stats.success_rate:.1f}%")
    print(f"\nData:")
    print(f"  Total pages:   {stats.total_pages:,}")
    print(f"  Total chunks:  {stats.total_chunks:,}")
    print(f"  Total vectors: {stats.total_vectors:,}")
    print(f"  Namespace:     {config.namespace}")

    if stats.errors:
        print(f"\nErrors ({len(stats.errors)}):")
        for err in stats.errors[:5]:  # Show first 5
            print(f"  - {err['file']}: {err['error'][:50]}...")
        if len(stats.errors) > 5:
            print(f"  ... and {len(stats.errors) - 5} more")

    print(f"\nNext steps:")
    print(f"  1. Test RAG: curl -X POST http://localhost:8000/api/chat -d '{{\"message\": \"test query\"}}'")
    print(f"  2. Check stats: curl http://localhost:8000/api/search/stats")
    print(f"{'='*60}\n")


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Batch ingest PDFs for RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./documents/              Process all PDFs in directory
  %(prog)s ./documents/ --dry-run    Preview without uploading
  %(prog)s ./documents/ --force      Re-process already processed files
  %(prog)s ./documents/ --namespace medical  Use custom namespace
        """
    )

    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing PDF files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview processing without uploading to Pinecone"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process files even if already processed"
    )
    parser.add_argument(
        "--namespace",
        default="default",
        help="Pinecone namespace (default: 'default')"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Chunk size in characters (default: 1000)"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Chunk overlap in characters (default: 200)"
    )
    parser.add_argument(
        "--index-name",
        default="dermaai-ckpa",
        help="Pinecone index name (default: 'dermaai-ckpa')"
    )

    args = parser.parse_args()

    # Validate input directory
    if not args.input_dir.exists():
        print(f"Error: Directory not found: {args.input_dir}")
        sys.exit(1)

    if not args.input_dir.is_dir():
        print(f"Error: Not a directory: {args.input_dir}")
        sys.exit(1)

    # Create config
    config = Config(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        namespace=args.namespace,
        index_name=args.index_name
    )

    # Process
    try:
        stats = process_directory(
            args.input_dir,
            config,
            dry_run=args.dry_run,
            force=args.force
        )
        print_summary(stats, config)

        # Exit with error code if any failures
        sys.exit(0 if stats.failed == 0 else 1)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress has been saved.")
        print("Run again to resume from where you left off.")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
