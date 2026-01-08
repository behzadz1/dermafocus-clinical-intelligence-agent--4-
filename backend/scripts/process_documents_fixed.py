#!/usr/bin/env python3
"""
Fixed document processor with globally unique vector IDs

This replaces your current document processor to prevent vector ID collisions.
Vector IDs are now: {doc_id}::p{page}::c{chunk}::{hash}
"""
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Import required libraries
try:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from openai import OpenAI
    from pinecone import Pinecone
except ImportError as e:
    print(f"❌ Error: Missing required library")
    print(f"   {e}")
    print(f"\nInstall with:")
    print(f"   pip install langchain langchain-community openai pinecone-client pypdf")
    sys.exit(1)


def generate_document_id(filepath: str) -> str:
    """
    Generate stable document ID from filepath
    
    Examples:
      "Plinest Guide.pdf" -> "plinest_guide"
      "Treatment-Protocol-2024.pdf" -> "treatment_protocol_2024"
    """
    filename = Path(filepath).stem
    # Sanitize filename for use as ID
    doc_id = filename.lower().replace(" ", "_").replace("-", "_")
    # Remove any special characters, keep only alphanumeric and underscore
    doc_id = "".join(c for c in doc_id if c.isalnum() or c == "_")
    return doc_id


def generate_vector_id(
    doc_id: str, 
    page_num: int, 
    chunk_idx: int, 
    chunk_text: str
) -> str:
    """
    Generate globally unique vector ID
    
    Format: {doc_id}::p{page}::c{chunk}::{hash}
    
    Examples:
      "plinest_guide::p3::c0::a3f89b2e"
      "treatment_protocol::p12::c2::7d4c1e9f"
    
    The hash provides:
    - Extra uniqueness guarantee
    - Deduplication detection (same content = same hash)
    - Debugging aid (can identify chunk by hash)
    """
    # Create content hash for extra uniqueness and deduplication
    content_hash = hashlib.md5(chunk_text.encode('utf-8')).hexdigest()[:8]
    
    vector_id = f"{doc_id}::p{page_num}::c{chunk_idx}::{content_hash}"
    return vector_id


def process_document_with_unique_ids(
    filepath: str,
    openai_client: OpenAI,
    pinecone_index,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    test_mode: bool = False
) -> Dict:
    """
    Process a single document with globally unique vector IDs
    
    Args:
        filepath: Path to PDF file
        openai_client: OpenAI client for embeddings
        pinecone_index: Pinecone index to upload to
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        test_mode: If True, don't upload, just process
    
    Returns:
        Dict with processing results
    """
    print(f"\n📄 Processing: {filepath}")
    
    # Generate stable document ID
    doc_id = generate_document_id(filepath)
    doc_name = Path(filepath).name
    
    print(f"   📝 Document ID: {doc_id}")
    print(f"   📁 Filename: {doc_name}")
    
    # Load document
    try:
        loader = PyPDFLoader(filepath)
        pages = loader.load()
        total_pages = len(pages)
        print(f"   📄 Pages: {total_pages}")
    except Exception as e:
        print(f"   ❌ Error loading PDF: {e}")
        return {"error": str(e)}
    
    # Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    
    all_vectors = []
    total_chunks = 0
    
    # Process each page
    for page_num, page in enumerate(pages, start=1):
        # Split page into chunks
        chunks = text_splitter.split_text(page.page_content)
        
        for chunk_idx, chunk_text in enumerate(chunks):
            # Generate globally unique vector ID
            vector_id = generate_vector_id(doc_id, page_num, chunk_idx, chunk_text)
            
            try:
                # Generate embedding
                response = openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=chunk_text
                )
                embedding = response.data[0].embedding
            except Exception as e:
                print(f"   ❌ Error generating embedding for page {page_num}, chunk {chunk_idx}: {e}")
                continue
            
            # Enhanced metadata
            metadata = {
                "doc_id": doc_id,
                "document_name": doc_name,
                "page_number": page_num,
                "chunk_index": chunk_idx,
                "chunk_id": vector_id,
                "text": chunk_text[:1000],  # Truncate if too long for metadata
                "upload_timestamp": datetime.now().isoformat(),
                "total_pages": total_pages,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            }
            
            all_vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": metadata
            })
            
            total_chunks += 1
    
    print(f"   ✅ Created {total_chunks} chunks")
    if all_vectors:
        print(f"   🔑 Sample vector ID: {all_vectors[0]['id']}")
    
    # Upload to Pinecone in batches
    if not test_mode and all_vectors:
        batch_size = 100
        num_batches = (len(all_vectors) - 1) // batch_size + 1
        
        print(f"   📤 Uploading {num_batches} batches to Pinecone...")
        
        for i in range(0, len(all_vectors), batch_size):
            batch = all_vectors[i:i+batch_size]
            try:
                pinecone_index.upsert(vectors=batch, namespace="default")
                batch_num = i // batch_size + 1
                print(f"      Batch {batch_num}/{num_batches} uploaded ✓")
            except Exception as e:
                print(f"      ❌ Error uploading batch {batch_num}: {e}")
    elif test_mode:
        print(f"   🧪 Test mode - skipping upload")
    
    return {
        "document_id": doc_id,
        "document_name": doc_name,
        "total_pages": total_pages,
        "total_chunks": total_chunks,
        "vector_ids": [v["id"] for v in all_vectors],
        "success": True
    }


def main():
    """Process all documents with unique vector IDs"""
    print("🚀 Document Processor with Unique Vector IDs")
    print("=" * 70)
    
    # Check for test mode
    test_mode = "--test-mode" in sys.argv
    if test_mode:
        print("🧪 Running in TEST MODE (no uploads)")
        print("=" * 70)
    
    # Check environment variables
    missing_vars = []
    if not os.getenv("OPENAI_API_KEY"):
        missing_vars.append("OPENAI_API_KEY")
    if not os.getenv("PINECONE_API_KEY"):
        missing_vars.append("PINECONE_API_KEY")
    
    if missing_vars:
        print(f"❌ Error: Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print(f"\nSet them with:")
        print(f"   export OPENAI_API_KEY=your_key")
        print(f"   export PINECONE_API_KEY=your_key")
        sys.exit(1)
    
    # Initialize clients
    try:
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index("dermaai-ckpa")
        print("✅ Connected to OpenAI and Pinecone")
    except Exception as e:
        print(f"❌ Error initializing clients: {e}")
        sys.exit(1)
    
    # Find documents to process
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        # Process specific file
        pdf_files = [Path(sys.argv[1])]
        print(f"\n📄 Processing single file: {pdf_files[0]}")
    else:
        # Process all PDFs in documents/raw/
        docs_dir = Path("documents/raw")
        if not docs_dir.exists():
            docs_dir = Path("backend/documents/raw")
        if not docs_dir.exists():
            print(f"❌ Error: Documents directory not found")
            print(f"   Tried: documents/raw/ and backend/documents/raw/")
            sys.exit(1)
        
        pdf_files = list(docs_dir.glob("*.pdf"))
        print(f"\n📚 Found {len(pdf_files)} documents in {docs_dir}")
    
    if not pdf_files:
        print(f"❌ No PDF files found")
        sys.exit(1)
    
    print("=" * 70)
    
    # Process each document
    results = []
    for pdf_file in pdf_files:
        try:
            result = process_document_with_unique_ids(
                str(pdf_file),
                openai_client,
                index,
                test_mode=test_mode
            )
            if result.get("success"):
                results.append(result)
        except Exception as e:
            print(f"❌ Error processing {pdf_file}: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ Processing Complete!")
    print(f"\n📊 Summary:")
    print(f"   Documents processed: {len(results)}")
    print(f"   Total chunks: {sum(r['total_chunks'] for r in results)}")
    print(f"   Total pages: {sum(r['total_pages'] for r in results)}")
    
    # Verify uniqueness of generated IDs
    all_ids = []
    for r in results:
        all_ids.extend(r["vector_ids"])
    
    if all_ids:
        print(f"\n🔑 Vector ID Verification:")
        print(f"   Total vector IDs generated: {len(all_ids)}")
        print(f"   Unique IDs: {len(set(all_ids))}")
        
        if len(all_ids) == len(set(all_ids)):
            print(f"   ✅ All IDs are unique!")
        else:
            duplicates = len(all_ids) - len(set(all_ids))
            print(f"   ❌ WARNING: {duplicates} duplicate IDs found!")
            print(f"   This should not happen - please report this bug")
        
        # Show sample IDs
        print(f"\n📝 Sample Vector IDs:")
        for vid in all_ids[:5]:
            print(f"   {vid}")
    
    if test_mode:
        print(f"\n🧪 Test mode completed - no vectors uploaded")
        print(f"   Remove --test-mode flag to upload for real")
    else:
        print(f"\n💡 Next steps:")
        print(f"   1. Run diagnosis: python diagnose_vector_collisions.py")
        print(f"   2. Test RAG quality: Ask questions about your documents")
        print(f"   3. Verify sources are correct and from all documents")


if __name__ == "__main__":
    main()
