#!/usr/bin/env python3
"""
Test Table Extraction and Markdown Formatting
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.document_processor import DocumentProcessor

def test_table_extraction():
    """Test table extraction on a sample document"""

    # Test file path - use a protocol document that likely has tables
    test_file = Path(__file__).parent.parent / "data" / "uploads" / "Treatment Techniques & Protocols" / "Advancing Hand Rejuvenation With Newest®.pdf"

    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        # Try another file
        uploads_dir = Path(__file__).parent.parent / "data" / "uploads"
        pdf_files = list(uploads_dir.rglob("*.pdf"))
        if pdf_files:
            test_file = pdf_files[0]
            print(f"Using alternate file: {test_file}")
        else:
            print("No PDF files found in uploads directory")
            return

    print("=" * 80)
    print("TABLE EXTRACTION TEST")
    print("=" * 80)
    print(f"Processing: {test_file.name}\n")

    # Create processor with hierarchical chunking enabled
    processor = DocumentProcessor(
        chunk_size=1000,
        chunk_overlap=200,
        use_hierarchical=True
    )

    # Process the document
    result = processor.process_pdf(
        str(test_file),
        doc_id=test_file.stem
    )

    # Display results
    print("\n" + "=" * 80)
    print("EXTRACTION RESULTS")
    print("=" * 80)

    stats = result["stats"]
    print(f"Total pages: {stats['num_pages']}")
    print(f"Total chunks: {stats['num_chunks']}")
    print(f"  - Parent chunks: {stats['num_parent_chunks']}")
    print(f"  - Child chunks: {stats['num_child_chunks']}")
    print(f"  - Flat chunks: {stats['num_flat_chunks']}")
    print(f"  - Table chunks: {stats['num_table_chunks']}")
    print(f"Tables extracted: {stats['num_tables']}")

    # Display table information
    tables = result.get("tables", [])
    if tables:
        print(f"\n{'=' * 80}")
        print("TABLE DETAILS")
        print("=" * 80)

        for i, table in enumerate(tables):
            print(f"\nTable {i+1}:")
            print(f"  Page: {table['page_number']}")
            print(f"  Rows: {table['num_rows']}")
            print(f"  Columns: {table['num_cols']}")
            print(f"  Headers: {table['headers']}")

    # Display sample table chunks
    table_chunks = [c for c in result["chunks"] if c.get("chunk_type") == "table"]

    if table_chunks:
        print(f"\n{'=' * 80}")
        print("TABLE CHUNK SAMPLES")
        print("=" * 80)

        for i, chunk in enumerate(table_chunks[:2]):  # Show first 2 table chunks
            print(f"\nTable Chunk {i+1}:")
            print(f"  Chunk ID: {chunk['chunk_id']}")
            print(f"  Page: {chunk['metadata'].get('page_number')}")
            print(f"  Table Type: {chunk['metadata'].get('table_type', 'unknown')}")
            print(f"  Is Table: {chunk['metadata'].get('is_table', False)}")
            print(f"  Text Preview:\n")
            print("  " + "\n  ".join(chunk['text'].split('\n')[:10]))  # First 10 lines
            if len(chunk['text'].split('\n')) > 10:
                print("  ...")
    else:
        print("\n⚠ No table chunks found in this document")
        print("This document may not contain tables, or tables were not detected")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Return success/failure
    return len(table_chunks) > 0


if __name__ == "__main__":
    success = test_table_extraction()
    sys.exit(0 if success else 1)
