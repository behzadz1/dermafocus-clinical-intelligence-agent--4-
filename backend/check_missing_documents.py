#!/usr/bin/env python3
"""
Check which documents in uploads folder are missing from processing
"""
import json
from pathlib import Path
from collections import Counter

# Get all PDFs in uploads
uploads_dir = Path("data/uploads")
all_pdfs = {}
for pdf_path in uploads_dir.rglob("*.pdf"):
    all_pdfs[pdf_path.name] = str(pdf_path)

print(f"Total PDFs in uploads folder: {len(all_pdfs)}")

# Get processed documents
with open('data/uploads/processed_documents.json', 'r') as f:
    processed = json.load(f)

processed_files = {}
for hash_key, doc in processed.items():
    if doc.get('success'):
        filename = Path(doc['file_path']).name
        processed_files[filename] = doc['file_path']

print(f"Total successfully processed: {len(processed_files)}")

# Find missing files
missing_files = set(all_pdfs.keys()) - set(processed_files.keys())

if missing_files:
    print(f"\n⚠️  MISSING {len(missing_files)} files:\n")
    for file in sorted(missing_files):
        rel_path = Path(all_pdfs[file]).relative_to(uploads_dir)
        print(f"  - {rel_path}")
else:
    print("\n✅ All files have been processed!")

# Check for duplicate filenames (same name in different folders)
pdf_names = [p.name for p in uploads_dir.rglob("*.pdf")]
duplicates = {name: count for name, count in Counter(pdf_names).items() if count > 1}

if duplicates:
    print(f"\n⚠️  Found {len(duplicates)} duplicate filenames (may cause issues):\n")
    for name, count in duplicates.items():
        print(f"\n  {name} ({count} copies):")
        for pdf in uploads_dir.rglob(f"**/{name}"):
            print(f"    → {pdf.relative_to(uploads_dir)}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total PDFs: {len(all_pdfs)}")
print(f"Processed: {len(processed_files)}")
print(f"Missing: {len(missing_files)}")
print(f"Duplicates: {len(duplicates)}")
