#!/usr/bin/env python3
"""
Direct Test of Reranker Score Normalization
Tests the reranker service directly to verify sigmoid normalization
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from app.services.reranker_service import get_reranker_service

logger = structlog.get_logger()


def test_reranker_direct():
    """Test reranker directly with sample query and passages"""
    print("\n" + "=" * 80)
    print("DIRECT RERANKER SCORE NORMALIZATION TEST")
    print("=" * 80)

    reranker = get_reranker_service()

    # Test query
    query = "What are the contraindications for polynucleotides?"

    # Sample passages (simulating retrieved chunks)
    passages = [
        "Polynucleotides (PN) are contraindicated in patients with active infections, autoimmune diseases, and known hypersensitivity to the product components.",
        "The treatment uses polynucleotides derived from salmon DNA for skin rejuvenation and wound healing.",
        "Hyaluronic acid is a different product used for dermal filling and hydration.",
        "Injection techniques vary depending on the treatment area and desired outcome.",
        "Clinical studies have shown promising results for tissue regeneration with PN therapy."
    ]

    print(f"\nQuery: {query}")
    print(f"Passages: {len(passages)}")
    print("\nReranking...")

    try:
        scores = reranker.score(query, passages)

        if scores is None:
            print("❌ FAIL: Reranker returned None")
            return False

        print(f"\n📊 Reranker Scores:")
        for i, (passage, score) in enumerate(zip(passages, scores), 1):
            # Truncate passage for display
            passage_preview = passage[:60] + "..." if len(passage) > 60 else passage
            print(f"\n  {i}. Score: {score:.6f}")
            print(f"     Passage: {passage_preview}")

            # Validate score range
            if score < 0 or score > 1:
                print(f"     ❌ INVALID: Score {score} outside 0-1 range!")
                return False
            elif score < 0.3:
                print(f"     📊 Low relevance")
            elif score < 0.7:
                print(f"     📊 Medium relevance")
            else:
                print(f"     ✅ High relevance")

        # Validation
        print("\n" + "=" * 80)
        print("VALIDATION RESULTS")
        print("=" * 80)

        all_in_range = all(0 <= s <= 1 for s in scores)
        print(f"\n✓ All scores in 0-1 range: {all_in_range}")

        # Check that most relevant passage (1st one about contraindications) has high score
        top_score = max(scores)
        top_idx = scores.index(top_score)
        print(f"✓ Top score: {top_score:.4f} (passage {top_idx + 1})")

        if top_idx == 0:
            print(f"✓ Correct passage ranked highest (passage 1 about contraindications)")
        else:
            print(f"⚠️  Expected passage 1 to rank highest, but passage {top_idx + 1} ranked highest")

        # Check score distribution
        avg_score = sum(scores) / len(scores)
        print(f"✓ Average score: {avg_score:.4f}")

        # Before fix, scores would be negative (e.g., -8.24, -2.37)
        # After fix, scores should be in 0-1 range
        has_negative = any(s < 0 for s in scores)

        if has_negative:
            print("\n❌ FAIL: Found negative scores - sigmoid normalization not applied")
            return False

        if not all_in_range:
            print("\n❌ FAIL: Scores outside 0-1 range")
            return False

        print("\n✅ PASS: Reranker normalization working correctly!")
        print("\n💡 Fix Applied:")
        print("   - MS-MARCO cross-encoder raw logits normalized with sigmoid")
        print("   - All scores now in 0-1 probability range")
        print("   - Evidence threshold checks (>= 0.50) will now work correctly")

        return True

    except Exception as e:
        print(f"\n❌ FAIL: Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run direct reranker test"""
    print("=" * 80)
    print("RERANKER SCORE NORMALIZATION FIX - DIRECT TEST")
    print("=" * 80)
    print("\nPhase 4.0 Fix: Apply sigmoid normalization to MS-MARCO logits")
    print("Expected: All scores in 0-1 range (before fix: negative scores)")

    try:
        result = test_reranker_direct()

        print("\n" + "=" * 80)
        print("FINAL RESULT")
        print("=" * 80)

        if result:
            print("\n✅ Reranker normalization fix VERIFIED")
            print("\nNext Steps:")
            print("  1. Restart the FastAPI server to load the fixed reranker")
            print("  2. Test with actual RAG queries")
            print("  3. Verify suggested questions are now answerable")
            return 0
        else:
            print("\n❌ Reranker normalization fix FAILED")
            print("\nPlease review the error above")
            return 1

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
