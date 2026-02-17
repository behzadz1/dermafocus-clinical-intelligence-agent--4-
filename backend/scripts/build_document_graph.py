#!/usr/bin/env python3
"""
Build Document Graph from Processed Documents
Extracts product mentions and builds cross-document relationships
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.document_graph import get_document_graph

def load_processed_documents(processed_dir: str) -> List[Dict]:
    """Load all processed JSON documents"""
    processed_path = Path(processed_dir)

    if not processed_path.exists():
        print(f"Error: Processed directory not found: {processed_dir}")
        return []

    documents = []
    for json_file in processed_path.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                doc_data = json.load(f)
                documents.append(doc_data)
        except Exception as e:
            print(f"Warning: Failed to load {json_file.name}: {e}")

    return documents


def build_graph_from_documents(documents: List[Dict]):
    """Build document graph from processed documents"""
    doc_graph = get_document_graph()

    print(f"\nBuilding document graph from {len(documents)} documents...")
    print("=" * 80)

    added_count = 0
    skipped_count = 0

    for doc_data in documents:
        doc_id = doc_data.get("doc_id")
        full_text = doc_data.get("full_text", "")
        doc_type = doc_data.get("doc_type", "document")
        metadata = doc_data.get("metadata", {})

        if not doc_id or not full_text:
            print(f"   Skipping document (missing data): {doc_id or 'unknown'}")
            skipped_count += 1
            continue

        try:
            result = doc_graph.add_document(
                doc_id=doc_id,
                full_text=full_text,
                doc_type=doc_type,
                metadata=metadata
            )

            products = result.get("products", [])
            related_count = len(result.get("related_docs", []))

            print(f"   ✓ {doc_id}")
            print(f"     Products: {', '.join(products) if products else 'none'}")
            print(f"     Related docs: {related_count}")

            added_count += 1

        except Exception as e:
            print(f"   ✗ Failed to add {doc_id}: {e}")
            skipped_count += 1

    print("\n" + "=" * 80)
    print(f"Graph building complete:")
    print(f"  Added: {added_count}")
    print(f"  Skipped: {skipped_count}")

    # Show graph statistics
    stats = doc_graph.get_graph_stats()
    print(f"\nGraph Statistics:")
    print(f"  Total documents: {stats.get('total_documents', 0)}")
    print(f"  Total products: {stats.get('total_products', 0)}")
    print(f"  Total doc types: {stats.get('total_doc_types', 0)}")


def main():
    """Main execution"""
    # Default path to processed documents
    backend_dir = Path(__file__).parent.parent
    processed_dir = backend_dir / "data" / "processed"

    # Allow custom path as argument
    if len(sys.argv) > 1:
        processed_dir = Path(sys.argv[1])

    print("=" * 80)
    print("DOCUMENT GRAPH BUILDER")
    print("=" * 80)
    print(f"Loading documents from: {processed_dir}")

    # Load documents
    documents = load_processed_documents(str(processed_dir))

    if not documents:
        print("No documents found. Exiting.")
        return

    print(f"Found {len(documents)} processed documents")

    # Build graph
    build_graph_from_documents(documents)

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()
