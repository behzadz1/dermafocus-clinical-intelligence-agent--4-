#!/usr/bin/env python3
"""
Upload Vectors to Pinecone
Generates embeddings for processed documents and uploads to Pinecone
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.embedding_service import get_embedding_service
from app.services.pinecone_service import get_pinecone_service
from app.config import settings


class VectorUploader:
    """Upload document embeddings to Pinecone"""
    
    def __init__(self):
        """Initialize services"""
        self.embedding_service = get_embedding_service()
        self.pinecone_service = get_pinecone_service()
        self.processed_dir = Path(settings.processed_dir)
    
    def upload_document(
        self,
        doc_id: str,
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Upload a single document to Pinecone
        
        Args:
            doc_id: Document identifier
            namespace: Pinecone namespace
            
        Returns:
            Upload result
        """
        print(f"Processing: {doc_id}")
        
        # Load processed document
        processed_file = self.processed_dir / f"{doc_id}_processed.json"
        
        if not processed_file.exists():
            raise FileNotFoundError(f"Processed file not found: {processed_file}")
        
        with open(processed_file) as f:
            doc_data = json.load(f)
        
        chunks = doc_data.get("chunks", [])
        
        if not chunks:
            print(f"  ⚠️  No chunks found")
            return {"success": False, "error": "No chunks"}
        
        print(f"  Chunks: {len(chunks)}")
        
        # Extract texts for embedding
        texts = [chunk["text"] for chunk in chunks]
        
        print(f"  Generating embeddings...")
        start_time = time.time()
        
        # Generate embeddings in batches
        embeddings = self.embedding_service.generate_embeddings_batch(texts)
        
        embed_time = time.time() - start_time
        print(f"  ✓ Embeddings generated ({embed_time:.2f}s)")
        
        # Prepare vectors for Pinecone
        vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            vector = {
                "id": chunk["chunk_id"],
                "values": embedding,
                "metadata": {
                    **chunk["metadata"],
                    "text": chunk["text"][:1000],  # Store first 1000 chars in metadata
                    "full_text_length": len(chunk["text"])
                }
            }
            vectors.append(vector)
        
        print(f"  Uploading to Pinecone (namespace: {namespace})...")
        
        # Upload to Pinecone
        result = self.pinecone_service.upsert_vectors(vectors, namespace=namespace)
        
        print(f"  ✓ Uploaded {result['upserted_count']} vectors")
        
        return {
            "success": True,
            "doc_id": doc_id,
            "chunks_processed": len(chunks),
            "vectors_uploaded": result["upserted_count"],
            "namespace": namespace,
            "time_taken": time.time() - start_time
        }
    
    def upload_all(self, namespace: str = "default") -> Dict[str, Any]:
        """
        Upload all processed documents to Pinecone
        
        Args:
            namespace: Pinecone namespace
            
        Returns:
            Summary of uploads
        """
        if not self.processed_dir.exists():
            raise FileNotFoundError(f"Processed directory not found: {self.processed_dir}")
        
        # Find all processed documents
        processed_files = list(self.processed_dir.glob("*_processed.json"))
        
        if not processed_files:
            print("No processed documents found")
            return {
                "total": 0,
                "successful": 0,
                "failed": 0
            }
        
        print(f"Found {len(processed_files)} processed document(s)")
        print(f"Namespace: {namespace}")
        print("-" * 60)
        
        results = []
        successful = 0
        failed = 0
        
        for i, file_path in enumerate(processed_files, 1):
            doc_id = file_path.stem.replace("_processed", "")
            
            print(f"\n[{i}/{len(processed_files)}]")
            
            try:
                result = self.upload_document(doc_id, namespace)
                results.append(result)
                successful += 1
                
            except Exception as e:
                print(f"  ✗ Failed: {str(e)}")
                results.append({
                    "success": False,
                    "doc_id": doc_id,
                    "error": str(e)
                })
                failed += 1
        
        # Calculate totals
        total_chunks = sum(r.get("chunks_processed", 0) for r in results if r["success"])
        total_vectors = sum(r.get("vectors_uploaded", 0) for r in results if r["success"])
        total_time = sum(r.get("time_taken", 0) for r in results if r["success"])
        
        # Print summary
        print("\n" + "=" * 60)
        print("UPLOAD SUMMARY")
        print("=" * 60)
        print(f"Total documents:    {len(processed_files)}")
        print(f"Successful:         {successful}")
        print(f"Failed:             {failed}")
        print(f"Total chunks:       {total_chunks}")
        print(f"Total vectors:      {total_vectors}")
        print(f"Total time:         {total_time:.2f}s")
        print(f"Namespace:          {namespace}")
        print("=" * 60)
        
        if failed > 0:
            print("\nFailed uploads:")
            for result in results:
                if not result["success"]:
                    print(f"  ✗ {result['doc_id']}: {result.get('error')}")
        
        return {
            "total": len(processed_files),
            "successful": successful,
            "failed": failed,
            "total_chunks": total_chunks,
            "total_vectors": total_vectors,
            "results": results
        }
    
    def verify_upload(self, namespace: str = "default") -> Dict[str, Any]:
        """
        Verify vectors were uploaded successfully
        
        Args:
            namespace: Namespace to check
            
        Returns:
            Verification results
        """
        print("Verifying upload...")
        
        try:
            stats = self.pinecone_service.get_index_stats()
            
            namespace_stats = stats["namespaces"].get(namespace, {})
            vector_count = namespace_stats.get("vector_count", 0)
            
            print(f"\n✓ Verification successful")
            print(f"  Namespace: {namespace}")
            print(f"  Vector count: {vector_count}")
            print(f"  Dimension: {stats['dimension']}")
            
            return {
                "success": True,
                "namespace": namespace,
                "vector_count": vector_count,
                "dimension": stats["dimension"]
            }
            
        except Exception as e:
            print(f"\n✗ Verification failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Upload document embeddings to Pinecone"
    )
    parser.add_argument(
        "--doc-id",
        help="Upload a specific document by ID"
    )
    parser.add_argument(
        "--namespace",
        default="default",
        help="Pinecone namespace (default: default)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify upload after completion"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("DermaAI CKPA - Vector Upload to Pinecone")
    print("=" * 60)
    print()
    
    try:
        uploader = VectorUploader()
        
        if args.doc_id:
            # Upload single document
            result = uploader.upload_document(args.doc_id, args.namespace)
            
            if result["success"]:
                print("\n✓ Upload successful")
            else:
                print("\n✗ Upload failed")
                sys.exit(1)
        else:
            # Upload all documents
            summary = uploader.upload_all(args.namespace)
            
            if summary["failed"] > 0:
                print(f"\n⚠️  Some uploads failed")
                sys.exit(1)
            else:
                print(f"\n✓ All uploads successful")
        
        # Verify if requested
        if args.verify:
            print()
            uploader.verify_upload(args.namespace)
    
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
