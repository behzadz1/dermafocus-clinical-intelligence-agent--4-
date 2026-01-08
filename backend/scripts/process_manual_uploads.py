#!/usr/bin/env python3
"""
Process Manually Uploaded Documents
Processes PDFs that were manually copied to the uploads folder
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.document_processor import DocumentProcessor
from app.config import settings


def process_manual_uploads():
    """Process all PDFs in uploads directory that haven't been processed yet"""
    
    upload_dir = Path(settings.upload_dir)
    processed_dir = Path(settings.processed_dir)
    
    if not upload_dir.exists():
        print(f"Error: Upload directory not found: {upload_dir}")
        return
    
    # Ensure processed directory exists
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all PDFs in uploads
    pdf_files = list(upload_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {upload_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) in uploads directory")
    print(f"Upload dir: {upload_dir}")
    print(f"Processed dir: {processed_dir}")
    print("-" * 60)
    
    # Initialize processor
    processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for i, pdf_path in enumerate(pdf_files, 1):
        doc_id = pdf_path.stem
        processed_file = processed_dir / f"{doc_id}_processed.json"
        
        # Skip if already processed
        if processed_file.exists():
            print(f"[{i}/{len(pdf_files)}] ⏭️  Skipped (already processed): {pdf_path.name}")
            skipped_count += 1
            continue
        
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        print(f"  Doc ID: {doc_id}")
        
        try:
            # Determine doc_type from filename or use 'document'
            doc_type = "document"
            if "product" in pdf_path.name.lower() or "factsheet" in pdf_path.name.lower():
                doc_type = "product"
            elif "protocol" in pdf_path.name.lower():
                doc_type = "protocol"
            elif "clinical" in pdf_path.name.lower() or "paper" in pdf_path.name.lower():
                doc_type = "clinical_paper"
            
            print(f"  Type: {doc_type}")
            
            # Process PDF
            result = processor.process_pdf(
                str(pdf_path),
                doc_id=doc_id,
                doc_type=doc_type
            )
            
            # Save processed data
            with open(processed_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"  ✓ Success!")
            print(f"    Pages: {result['stats']['num_pages']}")
            print(f"    Chunks: {result['stats']['num_chunks']}")
            print(f"    Characters: {result['stats']['total_chars']:,}")
            print(f"    Saved to: {processed_file.name}")
            
            processed_count += 1
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            error_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total files:     {len(pdf_files)}")
    print(f"Processed:       {processed_count}")
    print(f"Skipped:         {skipped_count}")
    print(f"Errors:          {error_count}")
    print("=" * 60)
    
    if processed_count > 0:
        print(f"\n✅ Successfully processed {processed_count} document(s)")
        print(f"📁 Processed files saved to: {processed_dir}")
    
    if error_count > 0:
        print(f"\n⚠️  {error_count} document(s) failed to process")


if __name__ == "__main__":
    print("=" * 60)
    print("DermaAI CKPA - Process Manual Uploads")
    print("=" * 60)
    print()
    
    process_manual_uploads()
