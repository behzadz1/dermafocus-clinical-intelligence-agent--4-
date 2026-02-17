#!/usr/bin/env python3
"""
Test Reranker Service
Tests different reranker providers (ms-marco, cohere, jina)
"""

import sys
import os
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.reranker_service import get_reranker_service


def test_ms_marco_reranker():
    """Test ms-marco (sentence_transformers) reranker"""
    print("=" * 80)
    print("TEST: MS-MARCO Reranker (sentence_transformers)")
    print("=" * 80)

    # Override provider
    os.environ["RERANKER_PROVIDER"] = "sentence_transformers"

    reranker = get_reranker_service()

    query = "What is the Plinest Eye dosing protocol?"
    passages = [
        "Plinest Eye is indicated for periocular rejuvenation with polynucleotides.",
        "The dosing protocol for Plinest Eye involves 1ml per session, administered every 2 weeks for 3-4 sessions.",
        "Newest is used for facial rejuvenation with a different protocol than Plinest.",
        "Contraindications include active infections and pregnancy.",
        "The product contains PN HPT and hyaluronic acid for skin regeneration."
    ]

    print(f"\nQuery: {query}")
    print(f"\nPassages ({len(passages)}):")
    for i, p in enumerate(passages, 1):
        print(f"  {i}. {p[:80]}...")

    scores = reranker.score(query, passages)

    if scores:
        print(f"\n📊 Reranking Scores:")
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        for rank, (idx, score) in enumerate(ranked, 1):
            print(f"  {rank}. [{score:.4f}] Passage {idx+1}")
            print(f"      {passages[idx][:100]}...")

        # Expected: Passage 2 (dosing protocol) should rank highest
        if ranked[0][0] == 1:  # Index 1 is the dosing protocol passage
            print("\n✓ PASS: Dosing protocol passage ranked highest")
            return True
        else:
            print(f"\n✗ FAIL: Expected passage 2 to rank highest, got passage {ranked[0][0]+1}")
            return False
    else:
        print("\n⚠ No scores returned (model may not be available)")
        return False


def test_cohere_reranker():
    """Test Cohere Rerank API"""
    print("\n" + "=" * 80)
    print("TEST: Cohere Reranker")
    print("=" * 80)

    cohere_api_key = os.getenv("COHERE_API_KEY")
    if not cohere_api_key:
        print("\n⚠ COHERE_API_KEY not set - skipping Cohere test")
        print("  To test Cohere: export COHERE_API_KEY=your-key")
        print("  Get API key from: https://cohere.com/")
        return None

    # Override provider
    os.environ["RERANKER_PROVIDER"] = "cohere"

    # Force new instance
    from app.services import reranker_service
    reranker_service._reranker_service = None
    reranker = get_reranker_service()

    query = "periocular injection technique for Plinest Eye"
    passages = [
        "Plinest Eye uses a 30G needle for periocular injections at 2-3mm depth in the mid-dermal layer.",
        "The product is indicated for treating fine lines and dark circles around the eyes.",
        "Newest has a different injection technique suitable for facial areas.",
        "Storage should be at room temperature away from direct sunlight.",
        "Clinical studies showed 85% patient satisfaction with periocular treatment results."
    ]

    print(f"\nQuery: {query}")
    print(f"\nPassages ({len(passages)}):")
    for i, p in enumerate(passages, 1):
        print(f"  {i}. {p[:80]}...")

    try:
        scores = reranker.score(query, passages)

        if scores:
            print(f"\n📊 Reranking Scores:")
            ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            for rank, (idx, score) in enumerate(ranked, 1):
                print(f"  {rank}. [{score:.4f}] Passage {idx+1}")
                print(f"      {passages[idx][:100]}...")

            # Expected: Passage 1 (injection technique) should rank highest
            if ranked[0][0] == 0:
                print("\n✓ PASS: Injection technique passage ranked highest")
                return True
            else:
                print(f"\n⚠ Expected passage 1 to rank highest, got passage {ranked[0][0]+1}")
                return False
        else:
            print("\n✗ FAIL: No scores returned from Cohere")
            return False

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_mechanism():
    """Test that fallback works when primary provider fails"""
    print("\n" + "=" * 80)
    print("TEST: Fallback Mechanism")
    print("=" * 80)

    # Set invalid provider to trigger fallback
    os.environ["RERANKER_PROVIDER"] = "cohere"
    os.environ.pop("COHERE_API_KEY", None)  # Remove API key to force fallback

    # Force new instance
    from app.services import reranker_service
    reranker_service._reranker_service = None
    reranker = get_reranker_service()

    query = "What are the contraindications?"
    passages = [
        "Contraindications include active infections, pregnancy, and autoimmune conditions.",
        "The product is well-tolerated with minimal side effects reported.",
        "Results are visible after 2-3 sessions with continued improvement."
    ]

    print("\nScenario: Cohere provider selected but API key missing")
    print("Expected: Fall back to ms-marco (sentence_transformers)")

    scores = reranker.score(query, passages)

    if scores:
        print(f"\n✓ PASS: Fallback successful - got {len(scores)} scores")
        print(f"  Top score: {max(scores):.4f}")
        return True
    else:
        print("\n✗ FAIL: Fallback did not work")
        return False


def main():
    """Run all reranker tests"""
    print("=" * 80)
    print("RERANKER SERVICE TEST SUITE")
    print("=" * 80)
    print()

    results = {}

    # Test 1: MS-MARCO (default)
    print("\nTest 1: MS-MARCO Reranker...")
    try:
        results["ms_marco"] = test_ms_marco_reranker()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["ms_marco"] = False

    # Test 2: Cohere (if API key available)
    print("\nTest 2: Cohere Reranker...")
    try:
        results["cohere"] = test_cohere_reranker()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["cohere"] = False

    # Test 3: Fallback mechanism
    print("\nTest 3: Fallback Mechanism...")
    try:
        results["fallback"] = test_fallback_mechanism()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["fallback"] = False

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, result in results.items():
        status = "✓ PASS" if result else ("⚠ SKIPPED" if result is None else "✗ FAIL")
        print(f"{test_name}: {status}")

    passed = sum(1 for r in results.values() if r is True)
    total = sum(1 for r in results.values() if r is not None)

    if total == 0:
        print("\n⚠ No tests were run")
        return 0

    if passed == total:
        print(f"\n✅ All {total} tests passed!")
        return 0
    else:
        print(f"\n⚠ {passed}/{total} tests passed")
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
