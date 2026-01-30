#!/usr/bin/env python3
"""
Process all missing PDF documents from uploads folder
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
import json
import hashlib
from datetime import datetime

from app.utils.document_processor import DocumentProcessor
from app.services.embedding_service import get_embedding_service
from app.services.pinecone_service import get_pinecone_service
from app.utils.chunking import chunk_text

def process_missing_documents():
    """Process all PDFs that haven't been processed yet"""
    
    # Initialize services
    processor = DocumentProcessor()
    embedding_service = get_embedding_service()
    pinecone_service = get_pinecone_service()
    
    # Load existing processed docs
    processed_json_path = 'data/uploads/processed_documents.json'
    with open(processed_json_path, 'r') as f:
        processed_docs = json.load(f)
    
    # Get all processed file paths
    processed_paths = set()
    for doc in processed_docs.values():
        if doc.get('success'):
            processed_paths.add(doc['file_path'])
    
    # Find all PDFs in uploads
    uploads_dir = Path("data/uploads")
    all_pdfs = list(uploads_dir.rglob("*.pdf"))
    
    # Find missing files
    missing_files = []
    for pdf_path in all_pdfs:
        if str(pdf_path) not in processed_paths:
            missing_files.append(pdf_path)
    
    if not missing_files:
        print("✅ All PDF files have already been processed!")
        return
    
    print(f"Found {len(missing_files)} unprocessed PDFs\n")
    
    total_new_vectors = 0
    successful = 0
    failed = 0
    
    for pdf_path in missing_files:
        try:
            print(f"\n{'='*80}")
            print(f"Processing: {pdf_path.name}")
            print(f"Path: {pdf_path.relative_to(uploads_dir)}")
            print(f"{'='*80}")
            
            # Extract text
            result = processor.process_pdf(str(pdf_path))
            if not result['success']:
                print(f"❌ Failed to extract: {result.get('error')}")
                failed += 1
                continue
            
            full_text = result['text']
            print(f"✓ Extracted {result['pages']} pages")
            
            # Chunk text
            chunks = chunk_text(full_text, chunk_size=1000, overlap=200)
            print(f"✓ Created {len(chunks)} chunks")
            
            # Generate embeddings
            print("Generating embeddings...")
            embeddings = []
            for i, chunk in enumerate(chunks, 1):
                emb = embedding_service.generate_embedding(chunk)
                embeddings.append(emb)
                if i % 10 == 0:
                    print(f"  {i}/{len(chunks)} embeddings...")
            
            print(f"✓ Generated {len(embeddings)} embeddings")
            
            # Prepare vectors for Pinecone
            doc_name = pdf_path.name
            doc_id = doc_name.lower().replace(' ', '_').replace('.pdf', '').replace('®', '').replace('(', '').replace(')', '')
            
            # Determine doc type based on folder
            parent_folder = pdf_path.parent.name
            if 'Clinical Papers' in str(pdf_path):
                doc_type = 'clinical_paper'
            elif 'Case Studies' in str(pdf_path):
                doc_type = 'case_study'
            elif 'Fact Sheets' in str(pdf_path) or 'Fact Sheet' in str(pdf_path):
                doc_type = 'fact_sheet'
            elif 'Brochures' in str(pdf_path):
                doc_type = 'brochure'
            elif 'Treatment' in str(pdf_path) or 'Protocol' in str(pdf_path):
                doc_type = 'protocol'
            else:
                doc_type = 'other'
            
            # Create vectors
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector = {
                    'id': f"{doc_id}_chunk_{i}",
                    'values': embedding,
                    'metadata': {
                        'text': chunk,
                        'document_name': doc_name,
                        'doc_id': doc_id,
                        'chunk_index': i,
                        'doc_type': doc_type,
                        'page_number': float(i // 2 + 1)
                    }
                }
                vectors.append(vector)
            
            # Upload to Pinecone in batches
            print("Uploading to Pinecone...")
            batch_size = 100
            num_batches = (len(vectors) - 1) // batch_size + 1
            for batch_start in range(0, len(vectors), batch_size):
                batch = vectors[batch_start:batch_start + batch_size]
                pinecone_service.upsert_vectors(batch)
                batch_num = batch_start // batch_size + 1
                print(f"  Batch {batch_num}/{num_batches}")
            
            print(f"✅ Uploaded {len(vectors)} vectors to Pinecone")
            total_new_vectors += len(vectors)
            successful += 1
            
            # Update processed_documents.json
            file_hash = hashlib.md5(str(pdf_path).encode()).hexdigest()
            processed_docs[file_hash] = {
                'file_path': str(pdf_path),
                'doc_id': doc_id,
                'processed_at': datetime.now().isoformat(),
                'pages': result['pages'],
                'chunks': len(chunks),
                'vectors': len(vectors),
                'success': True
            }
            
        except Exception as e:
            print(f"❌ Error processing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Save updated processed_documents.json
    with open(processed_json_path, 'w') as f:
        json.dump(processed_docs, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"Total files processed: {successful}")
    print(f"Failed: {failed}")
    print(f"Total new vectors added: {total_new_vectors}")
    print(f"Updated processed_documents.json with {len(processed_docs)} documents")
    
    # Verify Pinecone stats
    stats = pinecone_service.get_index_stats()
    print(f"\nPinecone Index Stats:")
    print(f"  Total vectors: {stats.total_vector_count}")
    print(f"  Dimension: {stats.dimension}")

if __name__ == "__main__":
    process_missing_documents()
