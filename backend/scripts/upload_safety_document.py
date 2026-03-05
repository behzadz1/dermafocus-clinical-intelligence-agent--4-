#!/usr/bin/env python3
"""
Upload Safety Document to Pinecone

This script processes the safety profiles text document and uploads it to Pinecone
with appropriate chunking and metadata for safety-critical retrieval.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.embedding_service import get_embedding_service
from app.services.pinecone_service import get_pinecone_service
from app.utils.metadata_enrichment import build_canonical_metadata
import hashlib
import re


def chunk_safety_document(text: str, chunk_size: int = 1000, overlap: int = 200):
    """
    Chunk the safety document intelligently, keeping product sections together

    Args:
        text: Full text content
        chunk_size: Maximum chunk size
        overlap: Overlap between chunks

    Returns:
        List of chunk dictionaries
    """
    chunks = []

    # Split by product sections (marked by "## Product Name")
    product_sections = re.split(r'\n(?=## [A-Z])', text)

    chunk_id = 0
    for section in product_sections:
        if not section.strip():
            continue

        # Extract product name from section header
        product_match = re.match(r'## ([A-Za-z\s]+)', section)
        product_name = product_match.group(1).strip() if product_match else "Unknown"

        # Split section into subsections (e.g., contraindications, precautions)
        lines = section.split('\n')
        current_subsection = ""
        current_text = ""

        for line in lines:
            # Check if this is a subsection header (### or numbered list)
            if line.startswith('###') or re.match(r'^\d+\.', line.strip()):
                # Save previous subsection if exists
                if current_text:
                    chunks.append({
                        "id": f"safety_{chunk_id}",
                        "text": current_text.strip(),
                        "metadata": {
                            "product": product_name.lower(),
                            "doc_type": "safety_profile",
                            "section": current_subsection.lower(),
                            "chunk_type": "safety"
                        }
                    })
                    chunk_id += 1

                # Start new subsection
                if line.startswith('###'):
                    current_subsection = line.replace('###', '').strip()
                current_text = f"Product: {product_name}\n{line}\n"
            else:
                current_text += line + "\n"

        # Add final subsection
        if current_text.strip():
            chunks.append({
                "id": f"safety_{chunk_id}",
                "text": current_text.strip(),
                "metadata": {
                    "product": product_name.lower(),
                    "doc_type": "safety_profile",
                    "section": current_subsection.lower(),
                    "chunk_type": "safety"
                }
            })
            chunk_id += 1

    return chunks


def main():
    print("=" * 80)
    print("SAFETY DOCUMENT UPLOAD TO PINECONE")
    print("=" * 80)

    # Load the safety document
    safety_doc_path = Path("data/uploads/Safety_Profiles/Dermafocus_Product_Safety_Profiles.txt")

    if not safety_doc_path.exists():
        print(f"❌ Error: Safety document not found at {safety_doc_path}")
        return 1

    print(f"\n📄 Reading safety document from: {safety_doc_path}")
    with open(safety_doc_path, 'r', encoding='utf-8') as f:
        safety_text = f.read()

    print(f"   Document size: {len(safety_text)} characters")

    # Chunk the document
    print("\n📦 Chunking safety document...")
    chunks = chunk_safety_document(safety_text)
    print(f"   Created {len(chunks)} safety chunks")

    # Show chunk distribution
    product_counts = {}
    for chunk in chunks:
        product = chunk['metadata']['product']
        product_counts[product] = product_counts.get(product, 0) + 1

    print("\n   Chunks by product:")
    for product, count in sorted(product_counts.items()):
        print(f"      {product}: {count} chunks")

    # Initialize services
    print("\n🔧 Initializing embedding and Pinecone services...")
    embedding_service = get_embedding_service()
    pinecone_service = get_pinecone_service()

    # Generate embeddings
    print("\n🤖 Generating embeddings...")
    texts = [chunk['text'] for chunk in chunks]
    embeddings = embedding_service.generate_embeddings_batch(texts)
    print(f"   Generated {len(embeddings)} embeddings")

    # Prepare vectors for upload
    print("\n📤 Preparing vectors for upload...")
    vectors = []

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        if embedding is None:
            print(f"   ⚠️  Warning: No embedding for chunk {i}, skipping")
            continue

        # Create canonical metadata
        metadata = build_canonical_metadata(
            doc_id="dermafocus_safety_profiles",
            doc_type="safety_profile",
            chunk_index=i,
            text=chunk['text'],
            metadata={
                **chunk['metadata'],
                "source": "Dermafocus Product Safety Profiles",
                "category": "Safety_Profiles",
                "importance": "critical"  # Mark as critical for boosting
            }
        )

        vectors.append({
            "id": f"safety_profile_{i}_{hashlib.md5(chunk['text'].encode()).hexdigest()[:8]}",
            "values": embedding,
            "metadata": metadata
        })

    print(f"   Prepared {len(vectors)} vectors for upload")

    # Upload to Pinecone
    print("\n☁️  Uploading to Pinecone...")
    batch_size = 100
    uploaded_count = 0

    for batch_start in range(0, len(vectors), batch_size):
        batch = vectors[batch_start:batch_start + batch_size]
        try:
            pinecone_service.upsert_vectors(batch, namespace="default")
            uploaded_count += len(batch)
            print(f"   Uploaded batch {batch_start // batch_size + 1}: {len(batch)} vectors")
        except Exception as e:
            print(f"   ❌ Error uploading batch: {str(e)}")
            return 1

    print("\n" + "=" * 80)
    print("✅ UPLOAD COMPLETE")
    print("=" * 80)
    print(f"Total chunks created: {len(chunks)}")
    print(f"Total vectors uploaded: {uploaded_count}")
    print(f"Document ID: dermafocus_safety_profiles")
    print(f"Doc type: safety_profile")
    print("\n💡 The safety information is now searchable in Pinecone!")
    print("   Safety queries will automatically boost these chunks.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
