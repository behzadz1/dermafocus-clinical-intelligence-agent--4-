#!/usr/bin/env python3
"""
Test Image Processing and Vision API
Tests image extraction and description generation
"""

import sys
import os
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.document_processor import DocumentProcessor

def test_image_extraction():
    """Test image extraction on a sample document"""

    # Test file path - use a protocol/technique document that likely has diagrams
    test_files = [
        Path(__file__).parent.parent / "data" / "uploads" / "Treatment Techniques & Protocols" / "Advancing Hand Rejuvenation With Newest®.pdf",
        Path(__file__).parent.parent / "data" / "uploads" / "Treatment Techniques & Protocols" / "Injection Technique and Protocols for the Perioral area with Newest®imizing Perioral Rejuvenation.pdf",
        Path(__file__).parent.parent / "data" / "uploads" / "Fact Sheets" / "Newest® Factsheet.pdf"
    ]

    test_file = None
    for f in test_files:
        if f.exists():
            test_file = f
            break

    if not test_file:
        print("No test files found. Trying to find any PDF...")
        uploads_dir = Path(__file__).parent.parent / "data" / "uploads"
        pdf_files = list(uploads_dir.rglob("*.pdf"))
        if pdf_files:
            test_file = pdf_files[0]
        else:
            print("❌ No PDF files found in uploads directory")
            return False

    print("=" * 80)
    print("IMAGE PROCESSING TEST")
    print("=" * 80)
    print(f"Processing: {test_file.name}")
    print(f"Full path: {test_file}\n")

    # Check if ENABLE_IMAGE_ANALYSIS is set
    enable_image_analysis = os.getenv("ENABLE_IMAGE_ANALYSIS", "False").lower() == "true"
    print(f"ENABLE_IMAGE_ANALYSIS: {enable_image_analysis}")

    if not enable_image_analysis:
        print("\n⚠️  Image analysis is DISABLED")
        print("   To enable, set ENABLE_IMAGE_ANALYSIS=True in .env")
        print("   This test will only extract images, not generate descriptions\n")

    # Create processor with image analysis enabled for this test
    processor = DocumentProcessor(
        chunk_size=1000,
        chunk_overlap=200,
        use_hierarchical=True,
        enable_image_analysis=enable_image_analysis  # Use env var
    )

    # Process the document
    try:
        result = processor.process_pdf(
            str(test_file),
            doc_id=test_file.stem
        )
    except Exception as e:
        print(f"\n❌ Error processing document: {e}")
        import traceback
        traceback.print_exc()
        return False

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
    print(f"  - Image chunks: {stats['num_image_chunks']}")
    print(f"Images extracted: {stats['num_images']}")

    # Display image information
    images = result.get("images", [])
    if images:
        print(f"\n{'=' * 80}")
        print("IMAGE DETAILS")
        print("=" * 80)

        for i, image in enumerate(images):
            print(f"\nImage {i+1}:")
            print(f"  Page: {image['page_number']}")
            print(f"  Size: {image['width']}x{image['height']} pixels")
            print(f"  Format: {image['image_ext']}")
            print(f"  File size: {image['size_bytes'] / 1024:.1f} KB")
    else:
        print("\n⚠ No images found in this document")

    # Display sample image chunks (with descriptions)
    image_chunks = [c for c in result["chunks"] if c.get("chunk_type") == "image"]

    if image_chunks:
        print(f"\n{'=' * 80}")
        print("IMAGE CHUNK SAMPLES (WITH DESCRIPTIONS)")
        print("=" * 80)

        for i, chunk in enumerate(image_chunks[:3]):  # Show first 3 image chunks
            print(f"\nImage Chunk {i+1}:")
            print(f"  Chunk ID: {chunk['chunk_id']}")
            print(f"  Page: {chunk['metadata'].get('page_number')}")
            print(f"  Is Image: {chunk['metadata'].get('is_image', False)}")
            print(f"  Image size: {chunk['metadata'].get('image_width')}x{chunk['metadata'].get('image_height')}")
            print(f"  Vision model: {chunk['metadata'].get('vision_model', 'N/A')}")
            print(f"  Confidence: {chunk['metadata'].get('vision_confidence', 0.0):.2f}")
            print(f"\n  Description:")
            print(f"  {chunk['text'][:500]}...")  # First 500 chars
    elif enable_image_analysis and images:
        print("\n⚠ Images were extracted but no descriptions were generated")
        print("   Check if the Vision API is working correctly")
    elif not enable_image_analysis and images:
        print("\n✓ Images extracted successfully")
        print("  Enable ENABLE_IMAGE_ANALYSIS=True in .env to generate descriptions")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Return success if images were found
    return len(images) > 0


if __name__ == "__main__":
    try:
        success = test_image_extraction()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
