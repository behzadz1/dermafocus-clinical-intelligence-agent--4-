#!/usr/bin/env python3
"""
Process All Documents with Hierarchical Chunking

This script processes all PDFs in the uploads directory using
document-type specific chunking strategies.

Usage:
    python scripts/process_all_documents.py
    python scripts/process_all_documents.py --upload-to-pinecone
    python scripts/process_all_documents.py --dry-run
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.document_processor import DocumentProcessor, DocumentBatch
from app.utils.hierarchical_chunking import (
    ChunkingStrategyFactory,
    DocumentType,
    ChunkType
)


class HierarchicalDocumentProcessor:
    """
    Processes all documents with hierarchical chunking strategies
    """

    def __init__(
        self,
        upload_dir: str = "data/uploads",
        output_dir: str = "data/processed",
        use_hierarchical: bool = True
    ):
        self.upload_dir = Path(upload_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.processor = DocumentProcessor(use_hierarchical=use_hierarchical)
        self.results = []
        self.stats = {
            "total_files": 0,
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "total_chunks": 0,
            "parent_chunks": 0,
            "child_chunks": 0,
            "flat_chunks": 0,
            "by_doc_type": {},
            "by_strategy": {},
            "processing_time": 0
        }

    def discover_documents(self) -> Dict[str, List[Path]]:
        """
        Discover all PDF documents organized by folder
        """
        documents = {}

        if not self.upload_dir.exists():
            print(f"Upload directory not found: {self.upload_dir}")
            return documents

        # Find all subdirectories with PDFs
        for folder in self.upload_dir.iterdir():
            if folder.is_dir():
                pdfs = list(folder.glob("*.pdf"))
                if pdfs:
                    documents[folder.name] = pdfs

        # Also check root uploads directory
        root_pdfs = list(self.upload_dir.glob("*.pdf"))
        if root_pdfs:
            documents["_root"] = root_pdfs

        return documents

    def process_all(
        self,
        dry_run: bool = False,
        force_reprocess: bool = False
    ) -> Dict[str, Any]:
        """
        Process all discovered documents

        Args:
            dry_run: If True, just report what would be processed
            force_reprocess: If True, reprocess even if output exists

        Returns:
            Processing results and statistics
        """
        start_time = time.time()

        # Discover documents
        documents_by_folder = self.discover_documents()

        if not documents_by_folder:
            print("No documents found to process!")
            return self.stats

        # Count total files
        total_files = sum(len(pdfs) for pdfs in documents_by_folder.values())
        self.stats["total_files"] = total_files

        print("\n" + "=" * 70)
        print("HIERARCHICAL DOCUMENT PROCESSING")
        print("=" * 70)
        print(f"Upload directory: {self.upload_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"Total documents found: {total_files}")
        print(f"Dry run: {dry_run}")
        print("=" * 70)

        # Show discovery summary
        print("\nDocuments by folder:")
        for folder, pdfs in documents_by_folder.items():
            doc_type = ChunkingStrategyFactory.detect_document_type(folder_name=folder)
            print(f"  {folder}: {len(pdfs)} PDFs → {doc_type.value}")

        if dry_run:
            print("\n[DRY RUN] Would process the above documents.")
            return self.stats

        print("\n" + "-" * 70)
        print("Starting processing...")
        print("-" * 70)

        # Process each folder
        processed_count = 0
        for folder_name, pdf_files in documents_by_folder.items():
            print(f"\n📁 Processing folder: {folder_name}")

            for pdf_path in pdf_files:
                processed_count += 1
                progress = f"[{processed_count}/{total_files}]"

                # Check if already processed
                output_file = self.output_dir / f"{pdf_path.stem}_processed.json"
                if output_file.exists() and not force_reprocess:
                    print(f"  {progress} ⏭️  Skipping (already processed): {pdf_path.name}")
                    self.stats["skipped"] += 1
                    continue

                # Process the document
                result = self._process_document(pdf_path, folder_name, progress)
                self.results.append(result)

        # Calculate final statistics
        self.stats["processing_time"] = round(time.time() - start_time, 2)

        # Print summary
        self._print_summary()

        return self.stats

    def _process_document(
        self,
        pdf_path: Path,
        folder_name: str,
        progress: str
    ) -> Dict[str, Any]:
        """
        Process a single document

        Args:
            pdf_path: Path to PDF file
            folder_name: Name of containing folder
            progress: Progress string for display

        Returns:
            Processing result dictionary
        """
        try:
            print(f"  {progress} 📄 Processing: {pdf_path.name}")

            # Process with hierarchical chunking
            result = self.processor.process_pdf(
                str(pdf_path),
                doc_id=pdf_path.stem,
                folder_name=folder_name
            )

            # Save processed document
            output_file = self.output_dir / f"{pdf_path.stem}_processed.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # Update statistics
            self._update_stats(result)

            # Print result summary
            doc_type = result.get("detected_type", "unknown")
            strategy = result.get("chunking_strategy", "unknown")
            num_chunks = result["stats"]["num_chunks"]
            parent_chunks = result["stats"].get("num_parent_chunks", 0)
            child_chunks = result["stats"].get("num_child_chunks", 0)

            print(f"           ✅ Type: {doc_type}, Strategy: {strategy}")
            print(f"           📊 Chunks: {num_chunks} total ({parent_chunks} parent, {child_chunks} child)")

            return {
                "success": True,
                "file": str(pdf_path),
                "doc_type": doc_type,
                "strategy": strategy,
                "chunks": num_chunks,
                "output": str(output_file)
            }

        except Exception as e:
            print(f"           ❌ Failed: {str(e)[:50]}")
            self.stats["failed"] += 1

            return {
                "success": False,
                "file": str(pdf_path),
                "error": str(e)
            }

    def _update_stats(self, result: Dict[str, Any]):
        """Update processing statistics from a result"""
        self.stats["processed"] += 1

        stats = result.get("stats", {})
        self.stats["total_chunks"] += stats.get("num_chunks", 0)
        self.stats["parent_chunks"] += stats.get("num_parent_chunks", 0)
        self.stats["child_chunks"] += stats.get("num_child_chunks", 0)
        self.stats["flat_chunks"] += stats.get("num_flat_chunks", 0)

        # Track by document type
        doc_type = result.get("detected_type", "unknown")
        if doc_type not in self.stats["by_doc_type"]:
            self.stats["by_doc_type"][doc_type] = {"count": 0, "chunks": 0}
        self.stats["by_doc_type"][doc_type]["count"] += 1
        self.stats["by_doc_type"][doc_type]["chunks"] += stats.get("num_chunks", 0)

        # Track by strategy
        strategy = result.get("chunking_strategy", "unknown")
        if strategy not in self.stats["by_strategy"]:
            self.stats["by_strategy"][strategy] = 0
        self.stats["by_strategy"][strategy] += 1

    def _print_summary(self):
        """Print processing summary"""
        print("\n" + "=" * 70)
        print("PROCESSING COMPLETE")
        print("=" * 70)

        print(f"\n📊 Overall Statistics:")
        print(f"   Total files:     {self.stats['total_files']}")
        print(f"   Processed:       {self.stats['processed']}")
        print(f"   Skipped:         {self.stats['skipped']}")
        print(f"   Failed:          {self.stats['failed']}")
        print(f"   Processing time: {self.stats['processing_time']}s")

        print(f"\n📦 Chunk Statistics:")
        print(f"   Total chunks:    {self.stats['total_chunks']}")
        print(f"   Parent chunks:   {self.stats['parent_chunks']}")
        print(f"   Child chunks:    {self.stats['child_chunks']}")
        print(f"   Flat chunks:     {self.stats['flat_chunks']}")

        print(f"\n📁 By Document Type:")
        for doc_type, data in self.stats["by_doc_type"].items():
            print(f"   {doc_type}: {data['count']} docs, {data['chunks']} chunks")

        print(f"\n⚙️  By Chunking Strategy:")
        for strategy, count in self.stats["by_strategy"].items():
            print(f"   {strategy}: {count} docs")

        # Check for failures
        if self.stats["failed"] > 0:
            print(f"\n⚠️  Failed Documents:")
            for result in self.results:
                if not result.get("success"):
                    print(f"   - {result['file']}: {result.get('error', 'Unknown error')[:50]}")

    def upload_to_pinecone(
        self,
        namespace: str = "default",
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Upload all processed documents to Pinecone

        Args:
            namespace: Pinecone namespace
            batch_size: Vectors per batch upload

        Returns:
            Upload statistics
        """
        print("\n" + "=" * 70)
        print("UPLOADING TO PINECONE")
        print("=" * 70)

        try:
            from app.services.embedding_service import get_embedding_service
            from app.services.pinecone_service import get_pinecone_service

            embedding_service = get_embedding_service()
            pinecone_service = get_pinecone_service()

            upload_stats = {
                "total_vectors": 0,
                "uploaded": 0,
                "failed": 0,
                "documents_processed": 0
            }

            # Find all processed documents
            processed_files = list(self.output_dir.glob("*_processed.json"))
            print(f"Found {len(processed_files)} processed documents")

            for i, processed_file in enumerate(processed_files, 1):
                print(f"\n[{i}/{len(processed_files)}] Uploading: {processed_file.stem}")

                try:
                    with open(processed_file, 'r', encoding='utf-8') as f:
                        doc_data = json.load(f)

                    chunks = doc_data.get("chunks", [])
                    if not chunks:
                        print(f"   ⏭️  No chunks to upload")
                        continue

                    # Prepare texts for embedding
                    texts = [chunk.get("text", "") for chunk in chunks]
                    chunk_ids = [chunk.get("id", f"chunk_{j}") for j, chunk in enumerate(chunks)]

                    # Generate embeddings
                    print(f"   Generating embeddings for {len(texts)} chunks...")
                    embeddings = embedding_service.generate_embeddings_batch(texts)

                    # Prepare vectors
                    vectors = []
                    for j, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                        # Create safe vector ID
                        vector_id = self._safe_vector_id(chunk_ids[j])

                        # Prepare metadata (Pinecone has limits on metadata size)
                        metadata = {
                            "doc_id": doc_data.get("doc_id", ""),
                            "doc_type": doc_data.get("doc_type", ""),
                            "chunk_type": chunk.get("chunk_type", "flat"),
                            "parent_id": chunk.get("parent_id", ""),
                            "section": chunk.get("section", "")[:100],
                            "text": chunk.get("text", "")[:1000],  # Truncate for metadata limits
                            "page_number": chunk.get("metadata", {}).get("page_number", 0)
                        }

                        vectors.append({
                            "id": vector_id,
                            "values": embedding,
                            "metadata": metadata
                        })

                    # Upload in batches
                    print(f"   Uploading {len(vectors)} vectors...")
                    for batch_start in range(0, len(vectors), batch_size):
                        batch = vectors[batch_start:batch_start + batch_size]
                        pinecone_service.upsert_vectors(batch, namespace=namespace)
                        upload_stats["uploaded"] += len(batch)

                    upload_stats["documents_processed"] += 1
                    upload_stats["total_vectors"] += len(vectors)
                    print(f"   ✅ Uploaded {len(vectors)} vectors")

                except Exception as e:
                    print(f"   ❌ Failed: {str(e)[:50]}")
                    upload_stats["failed"] += 1

            # Print summary
            print("\n" + "-" * 70)
            print("UPLOAD COMPLETE")
            print("-" * 70)
            print(f"Documents processed: {upload_stats['documents_processed']}")
            print(f"Total vectors uploaded: {upload_stats['uploaded']}")
            print(f"Failed documents: {upload_stats['failed']}")

            return upload_stats

        except ImportError as e:
            print(f"Error: Could not import services. Make sure dependencies are installed: {e}")
            return {"error": str(e)}

    def _safe_vector_id(self, chunk_id: str) -> str:
        """Create a safe vector ID for Pinecone"""
        import re
        # Replace non-alphanumeric characters
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', chunk_id)
        # Truncate to max length
        return safe_id[:100]


def main():
    parser = argparse.ArgumentParser(
        description="Process all PDFs with hierarchical chunking"
    )
    parser.add_argument(
        "--upload-dir",
        default="data/uploads",
        help="Directory containing PDF files"
    )
    parser.add_argument(
        "--output-dir",
        default="data/processed",
        help="Directory for processed output"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually processing"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reprocessing of already processed documents"
    )
    parser.add_argument(
        "--upload-to-pinecone",
        action="store_true",
        help="Upload processed documents to Pinecone after processing"
    )
    parser.add_argument(
        "--namespace",
        default="default",
        help="Pinecone namespace for upload"
    )

    args = parser.parse_args()

    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)

    print(f"Working directory: {os.getcwd()}")

    # Initialize processor
    processor = HierarchicalDocumentProcessor(
        upload_dir=args.upload_dir,
        output_dir=args.output_dir,
        use_hierarchical=True
    )

    # Process all documents
    stats = processor.process_all(
        dry_run=args.dry_run,
        force_reprocess=args.force
    )

    # Upload to Pinecone if requested
    if args.upload_to_pinecone and not args.dry_run:
        processor.upload_to_pinecone(namespace=args.namespace)

    # Save processing report
    if not args.dry_run:
        report_file = Path(args.output_dir) / "processing_report.json"
        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
            "results": processor.results
        }
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {report_file}")


if __name__ == "__main__":
    main()
