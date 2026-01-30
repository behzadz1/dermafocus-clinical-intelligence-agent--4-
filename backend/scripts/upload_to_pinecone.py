#!/usr/bin/env python3
"""
Upload Processed Documents to Pinecone

This script cleans existing Pinecone data and uploads newly processed
hierarchical chunks.

Usage:
    python scripts/upload_to_pinecone.py
    python scripts/upload_to_pinecone.py --namespace dermafocus
    python scripts/upload_to_pinecone.py --skip-clean  # Keep existing data
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.embedding_service import get_embedding_service
from app.services.pinecone_service import get_pinecone_service


def get_index_stats(pinecone_service, namespace: str) -> dict:
    """Get current Pinecone index statistics"""
    try:
        stats = pinecone_service.get_index_stats()
        namespace_stats = stats.get("namespaces", {}).get(namespace, {})
        return {
            "total_vectors": stats.get("total_vector_count", 0),
            "namespace_vectors": namespace_stats.get("vector_count", 0),
            "dimension": stats.get("dimension", 0),
            "namespaces": list(stats.get("namespaces", {}).keys())
        }
    except Exception as e:
        return {"error": str(e)}


def clean_namespace(pinecone_service, namespace: str) -> dict:
    """Delete all vectors in namespace"""
    try:
        result = pinecone_service.delete_vectors(delete_all=True, namespace=namespace)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def safe_vector_id(chunk_id: str) -> str:
    """Create a safe vector ID for Pinecone"""
    import re
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', chunk_id)
    return safe_id[:100]


def upload_documents(
    processed_dir: str,
    namespace: str,
    batch_size: int = 100
) -> dict:
    """Upload all processed documents to Pinecone"""

    embedding_service = get_embedding_service()
    pinecone_service = get_pinecone_service()

    processed_path = Path(processed_dir)
    processed_files = list(processed_path.glob("*_processed.json"))

    stats = {
        "documents_processed": 0,
        "documents_failed": 0,
        "total_chunks": 0,
        "vectors_uploaded": 0,
        "errors": []
    }

    print(f"\nFound {len(processed_files)} processed documents to upload")
    print("-" * 60)

    for i, processed_file in enumerate(processed_files, 1):
        doc_name = processed_file.stem.replace("_processed", "")
        print(f"\n[{i}/{len(processed_files)}] {doc_name}")

        try:
            # Load processed document
            with open(processed_file, 'r', encoding='utf-8') as f:
                doc_data = json.load(f)

            chunks = doc_data.get("chunks", [])
            if not chunks:
                print(f"   No chunks to upload")
                continue

            stats["total_chunks"] += len(chunks)

            # Prepare texts for embedding
            texts = []
            chunk_ids = []
            for j, chunk in enumerate(chunks):
                text = chunk.get("text", "")
                if text.strip():
                    texts.append(text)
                    chunk_ids.append(chunk.get("id", f"chunk_{j}"))

            if not texts:
                print(f"   No text content to embed")
                continue

            # Generate embeddings in batches
            print(f"   Generating embeddings for {len(texts)} chunks...")
            embeddings = embedding_service.generate_embeddings_batch(texts)

            # Prepare vectors
            vectors = []
            for j, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if not chunk.get("text", "").strip():
                    continue

                vector_id = safe_vector_id(chunk_ids[j] if j < len(chunk_ids) else f"chunk_{j}")

                # Prepare metadata (Pinecone has 40KB limit per vector)
                # IMPORTANT: Pinecone doesn't accept null values - use empty strings
                metadata = {
                    "doc_id": doc_data.get("doc_id", "") or "",
                    "doc_type": doc_data.get("detected_type", "") or "",
                    "chunk_type": chunk.get("chunk_type", "flat") or "flat",
                    "parent_id": chunk.get("parent_id", "") or "",  # Convert None to ""
                    "section": (chunk.get("section", "") or "")[:100],
                    "text": chunk.get("text", "")[:1000],  # Truncate for metadata limits
                    "page_number": chunk.get("metadata", {}).get("page_number", 0) or 0,
                    "chunk_index": j
                }

                # Add children info if parent chunk
                children_ids = chunk.get("children_ids")
                if children_ids:
                    metadata["has_children"] = True
                    metadata["children_count"] = len(children_ids)

                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                })

            # Upload in batches
            print(f"   Uploading {len(vectors)} vectors...")
            uploaded = 0
            for batch_start in range(0, len(vectors), batch_size):
                batch = vectors[batch_start:batch_start + batch_size]
                pinecone_service.upsert_vectors(batch, namespace=namespace)
                uploaded += len(batch)

            stats["vectors_uploaded"] += uploaded
            stats["documents_processed"] += 1
            print(f"   Uploaded {uploaded} vectors")

        except Exception as e:
            error_msg = f"{doc_name}: {str(e)[:100]}"
            stats["errors"].append(error_msg)
            stats["documents_failed"] += 1
            print(f"   FAILED: {str(e)[:50]}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Upload processed documents to Pinecone"
    )
    parser.add_argument(
        "--processed-dir",
        default="data/processed",
        help="Directory containing processed JSON files"
    )
    parser.add_argument(
        "--namespace",
        default="default",
        help="Pinecone namespace"
    )
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="Skip cleaning existing data"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Vectors per upload batch"
    )

    args = parser.parse_args()

    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)

    print("=" * 60)
    print("PINECONE UPLOAD - HIERARCHICAL CHUNKS")
    print("=" * 60)
    print(f"Working directory: {os.getcwd()}")
    print(f"Processed dir: {args.processed_dir}")
    print(f"Namespace: {args.namespace}")
    print(f"Skip clean: {args.skip_clean}")

    # Initialize services
    pinecone_service = get_pinecone_service()

    # Check current stats
    print("\n" + "-" * 60)
    print("CURRENT PINECONE STATUS")
    print("-" * 60)
    stats_before = get_index_stats(pinecone_service, args.namespace)
    print(f"Total vectors in index: {stats_before.get('total_vectors', 'N/A')}")
    print(f"Vectors in '{args.namespace}' namespace: {stats_before.get('namespace_vectors', 'N/A')}")
    print(f"Active namespaces: {stats_before.get('namespaces', [])}")

    # Clean existing data
    if not args.skip_clean:
        print("\n" + "-" * 60)
        print("CLEANING EXISTING DATA")
        print("-" * 60)

        if stats_before.get("namespace_vectors", 0) > 0:
            print(f"Deleting all vectors in '{args.namespace}' namespace...")
            clean_result = clean_namespace(pinecone_service, args.namespace)

            if clean_result["success"]:
                print("Namespace cleaned successfully")
                # Wait for deletion to propagate
                print("Waiting for deletion to propagate...")
                time.sleep(3)
            else:
                print(f"Warning: Clean failed - {clean_result.get('error')}")
        else:
            print("Namespace is already empty")

    # Upload new data
    print("\n" + "-" * 60)
    print("UPLOADING NEW HIERARCHICAL CHUNKS")
    print("-" * 60)

    start_time = time.time()
    upload_stats = upload_documents(
        processed_dir=args.processed_dir,
        namespace=args.namespace,
        batch_size=args.batch_size
    )
    upload_time = round(time.time() - start_time, 2)

    # Final stats
    print("\n" + "=" * 60)
    print("UPLOAD COMPLETE")
    print("=" * 60)
    print(f"Documents processed: {upload_stats['documents_processed']}")
    print(f"Documents failed: {upload_stats['documents_failed']}")
    print(f"Total chunks: {upload_stats['total_chunks']}")
    print(f"Vectors uploaded: {upload_stats['vectors_uploaded']}")
    print(f"Upload time: {upload_time}s")

    if upload_stats["errors"]:
        print(f"\nErrors ({len(upload_stats['errors'])}):")
        for error in upload_stats["errors"][:5]:
            print(f"  - {error}")
        if len(upload_stats["errors"]) > 5:
            print(f"  ... and {len(upload_stats['errors']) - 5} more")

    # Verify final state
    print("\n" + "-" * 60)
    print("FINAL PINECONE STATUS")
    print("-" * 60)
    time.sleep(2)  # Wait for index to update
    stats_after = get_index_stats(pinecone_service, args.namespace)
    print(f"Total vectors in index: {stats_after.get('total_vectors', 'N/A')}")
    print(f"Vectors in '{args.namespace}' namespace: {stats_after.get('namespace_vectors', 'N/A')}")

    # Save upload report
    report = {
        "timestamp": datetime.now().isoformat(),
        "namespace": args.namespace,
        "stats_before": stats_before,
        "stats_after": stats_after,
        "upload_stats": upload_stats,
        "upload_time_seconds": upload_time
    }

    report_file = Path(args.processed_dir) / "upload_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
