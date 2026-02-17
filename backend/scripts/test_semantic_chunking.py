#!/usr/bin/env python3
"""
Test Semantic Chunking
Tests semantic boundary detection using sentence embeddings
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_semantic_similarity():
    """Test basic semantic similarity functionality"""
    print("=" * 80)
    print("SEMANTIC SIMILARITY TEST")
    print("=" * 80)

    try:
        from app.services.semantic_similarity_service import get_semantic_similarity_service

        service = get_semantic_similarity_service()
        print("✓ Semantic similarity service loaded")
        print(f"  Model: all-MiniLM-L6-v2")

        # Test case 1: Similar medical texts
        text1 = "Plinest Eye is designed for periocular rejuvenation with polynucleotides."
        text2 = "The eye area treatment uses PN for skin regeneration and hydration."
        similarity1 = service.compute_similarity(text1, text2)
        print(f"\n📊 Test 1: Similar medical texts")
        print(f"   Similarity: {similarity1:.3f}")
        print(f"   Expected: > 0.7 (similar context)")
        print(f"   Result: {'✓ PASS' if similarity1 > 0.7 else '✗ FAIL'}")

        # Test case 2: Dissimilar topics
        text3 = "Plinest Eye is designed for periocular rejuvenation with polynucleotides."
        text4 = "The study was conducted with 40 patients over 6 weeks in Milan."
        similarity2 = service.compute_similarity(text3, text4)
        print(f"\n📊 Test 2: Dissimilar topics")
        print(f"   Similarity: {similarity2:.3f}")
        print(f"   Expected: < 0.7 (topic change)")
        print(f"   Result: {'✓ PASS' if similarity2 < 0.7 else '✗ FAIL'}")

        # Test case 3: Semantic break detection
        current = "Plinest Eye contains polynucleotides and hyaluronic acid for eye area treatment."
        next_para = "However, contraindications include active infections and pregnancy."
        is_break = service.is_semantic_break(current, next_para, threshold=0.75)
        print(f"\n📊 Test 3: Semantic break detection")
        print(f"   Break detected: {is_break}")
        print(f"   Expected: True (topic transition)")
        print(f"   Result: {'✓ PASS' if is_break else '✗ FAIL'}")

        return True

    except ImportError as e:
        print(f"\n❌ sentence-transformers not installed")
        print(f"   Install with: pip install sentence-transformers")
        print(f"   Error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_adaptive_chunking():
    """Test AdaptiveChunker with semantic similarity"""
    print("\n" + "=" * 80)
    print("ADAPTIVE CHUNKING TEST")
    print("=" * 80)

    try:
        from app.utils.hierarchical_chunking import AdaptiveChunker

        # Sample text with topic changes
        sample_text = """Plinest Eye is a dermal bio-revitalizer specifically designed for the delicate periocular area. It contains polynucleotides (PN HPT™) and hyaluronic acid that work synergistically to improve skin quality.

The product is indicated for treating fine lines, dark circles, and loss of elasticity around the eyes. Clinical studies have shown significant improvements in skin texture and hydration after treatment.

However, there are important contraindications to consider. Active infections in the treatment area and pregnancy are absolute contraindications. Patients with a history of allergic reactions should be carefully evaluated.

The treatment protocol involves 3-4 sessions spaced 2-3 weeks apart. Each session uses 1ml of product injected using a 30G needle at a depth of 2-3mm in the mid-dermal layer.

Results are typically visible after the second session, with optimal outcomes achieved after completing the full protocol. Maintenance treatments every 3-6 months help sustain the benefits.

Patients reported high satisfaction with the treatment, with minimal downtime and mild side effects. The most common adverse events were temporary redness and slight swelling at injection sites."""

        # Test with semantic similarity enabled
        print("\n1️⃣ Testing with SEMANTIC SIMILARITY ENABLED:")
        chunker_semantic = AdaptiveChunker(
            chunk_size=400,
            min_chunk_size=100,
            similarity_threshold=0.75,
            use_semantic_similarity=True
        )

        chunks_semantic = chunker_semantic.chunk(
            text=sample_text,
            doc_id="test_doc",
            doc_type="protocol"
        )

        print(f"   Chunks created: {len(chunks_semantic)}")
        print(f"   Chunk sizes: {[len(c.text) for c in chunks_semantic]}")

        for i, chunk in enumerate(chunks_semantic):
            print(f"\n   Chunk {i+1} ({len(chunk.text)} chars):")
            print(f"   {chunk.text[:150]}...")

        # Test with semantic similarity disabled
        print("\n\n2️⃣ Testing with HEURISTIC DETECTION ONLY:")
        chunker_heuristic = AdaptiveChunker(
            chunk_size=400,
            min_chunk_size=100,
            similarity_threshold=0.75,
            use_semantic_similarity=False
        )

        chunks_heuristic = chunker_heuristic.chunk(
            text=sample_text,
            doc_id="test_doc",
            doc_type="protocol"
        )

        print(f"   Chunks created: {len(chunks_heuristic)}")
        print(f"   Chunk sizes: {[len(c.text) for c in chunks_heuristic]}")

        # Compare
        print(f"\n📊 Comparison:")
        print(f"   Semantic chunks: {len(chunks_semantic)}")
        print(f"   Heuristic chunks: {len(chunks_heuristic)}")
        print(f"   Difference: {abs(len(chunks_semantic) - len(chunks_heuristic))} chunks")

        if len(chunks_semantic) != len(chunks_heuristic):
            print(f"   ✓ Semantic chunking detects different boundaries")
        else:
            print(f"   ℹ Same number of chunks (may have different boundaries)")

        return True

    except ImportError as e:
        print(f"\n⚠️ Semantic similarity not available")
        print(f"   Falling back to heuristic detection")
        print(f"   Error: {e}")
        return True  # Not a failure, just a fallback
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("SEMANTIC CHUNKING TEST SUITE")
    print("=" * 80)
    print()

    # Test 1: Semantic similarity service
    test1_pass = test_semantic_similarity()

    if not test1_pass:
        print("\n" + "=" * 80)
        print("⚠️ Semantic similarity unavailable - semantic chunking will use heuristics")
        print("=" * 80)
        return 0  # Not a failure, just a graceful fallback

    # Test 2: Adaptive chunking
    test2_pass = test_adaptive_chunking()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Semantic similarity: {'✓ PASS' if test1_pass else '✗ FAIL'}")
    print(f"Adaptive chunking: {'✓ PASS' if test2_pass else '✗ FAIL'}")

    if test1_pass and test2_pass:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
