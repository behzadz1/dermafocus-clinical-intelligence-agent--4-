#!/usr/bin/env python3
"""
Test Query Router Service
Tests query classification and type-specific routing
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.query_router import get_query_router, QueryType


def test_protocol_queries():
    """Test protocol query classification"""
    print("=" * 80)
    print("TEST: Protocol Query Classification")
    print("=" * 80)

    router = get_query_router()

    test_queries = [
        "What is the Newest treatment protocol?",
        "How many sessions are needed for Plinest Eye?",
        "What are the steps for administering Newest?",
        "What is the frequency of Plinest treatments?",
    ]

    correct = 0
    for query in test_queries:
        result = router.route_query(query)
        query_type = result["query_type"]
        config = result["config"]

        print(f"\nQuery: {query}")
        print(f"  Type: {query_type.value}")
        print(f"  Top-K Multiplier: {config['top_k_multiplier']}")
        print(f"  Boost Multiplier: {config['boost_multiplier']}")
        print(f"  Boost Doc Types: {config['boost_doc_types']}")

        if query_type == QueryType.PROTOCOL:
            print("  ✓ PASS")
            correct += 1
        else:
            print("  ✗ FAIL - Expected PROTOCOL")

    print(f"\n{correct}/{len(test_queries)} protocol queries classified correctly")
    return correct == len(test_queries)


def test_safety_queries():
    """Test safety query classification"""
    print("\n" + "=" * 80)
    print("TEST: Safety Query Classification")
    print("=" * 80)

    router = get_query_router()

    test_queries = [
        "What are the contraindications for Newest?",
        "Are there any side effects of Plinest?",
        "What are the safety precautions for Plinest Eye?",
        "Can I use Newest during pregnancy?",
    ]

    correct = 0
    for query in test_queries:
        result = router.route_query(query)
        query_type = result["query_type"]
        config = result["config"]

        print(f"\nQuery: {query}")
        print(f"  Type: {query_type.value}")
        print(f"  Prefer Sections: {config['prefer_sections']}")

        if query_type == QueryType.SAFETY:
            print("  ✓ PASS")
            correct += 1
        else:
            print("  ✗ FAIL - Expected SAFETY")

    print(f"\n{correct}/{len(test_queries)} safety queries classified correctly")
    return correct == len(test_queries)


def test_technique_queries():
    """Test technique query classification"""
    print("\n" + "=" * 80)
    print("TEST: Technique Query Classification")
    print("=" * 80)

    router = get_query_router()

    test_queries = [
        "What is the injection technique for Plinest Eye?",
        "How deep should I inject Newest?",
        "What needle size is recommended for Plinest?",
        "What is the proper administration method?",
    ]

    correct = 0
    for query in test_queries:
        result = router.route_query(query)
        query_type = result["query_type"]
        config = result["config"]

        print(f"\nQuery: {query}")
        print(f"  Type: {query_type.value}")
        print(f"  Prefer Chunk Types: {config['prefer_chunk_types']}")

        if query_type == QueryType.TECHNIQUE:
            print("  ✓ PASS")
            correct += 1
        else:
            print("  ✗ FAIL - Expected TECHNIQUE")

    print(f"\n{correct}/{len(test_queries)} technique queries classified correctly")
    return correct == len(test_queries)


def test_comparison_queries():
    """Test comparison query classification"""
    print("\n" + "=" * 80)
    print("TEST: Comparison Query Classification")
    print("=" * 80)

    router = get_query_router()

    test_queries = [
        "Compare Newest and Plinest",
        "What is the difference between Plinest Eye and Plinest Hair?",
        "Newest vs Plinest for facial rejuvenation",
        "Which is better: Newest or Plinest?",
    ]

    correct = 0
    for query in test_queries:
        result = router.route_query(query)
        query_type = result["query_type"]
        config = result["config"]

        print(f"\nQuery: {query}")
        print(f"  Type: {query_type.value}")
        print(f"  Top-K Multiplier: {config['top_k_multiplier']}")  # Should be 1.5
        print(f"  Boost Multiplier: {config['boost_multiplier']}")

        if query_type == QueryType.COMPARISON:
            print("  ✓ PASS")
            correct += 1
        else:
            print("  ✗ FAIL - Expected COMPARISON")

    print(f"\n{correct}/{len(test_queries)} comparison queries classified correctly")
    return correct == len(test_queries)


def test_product_info_queries():
    """Test product info query classification"""
    print("\n" + "=" * 80)
    print("TEST: Product Info Query Classification")
    print("=" * 80)

    router = get_query_router()

    test_queries = [
        "What is Newest?",
        "Tell me about Plinest Eye",
        "What are the main features of Plinest?",
        "Describe the Newest product",
    ]

    correct = 0
    for query in test_queries:
        result = router.route_query(query)
        query_type = result["query_type"]
        config = result["config"]

        print(f"\nQuery: {query}")
        print(f"  Type: {query_type.value}")
        print(f"  Boost Doc Types: {config['boost_doc_types']}")

        if query_type == QueryType.PRODUCT_INFO:
            print("  ✓ PASS")
            correct += 1
        else:
            print("  ✗ FAIL - Expected PRODUCT_INFO")

    print(f"\n{correct}/{len(test_queries)} product info queries classified correctly")
    return correct == len(test_queries)


def test_indication_queries():
    """Test indication query classification"""
    print("\n" + "=" * 80)
    print("TEST: Indication Query Classification")
    print("=" * 80)

    router = get_query_router()

    test_queries = [
        "What is Newest used for?",
        "What are the indications for Plinest Eye?",
        "When should I use Plinest?",
        "What conditions does Newest treat?",
    ]

    correct = 0
    for query in test_queries:
        result = router.route_query(query)
        query_type = result["query_type"]

        print(f"\nQuery: {query}")
        print(f"  Type: {query_type.value}")

        if query_type == QueryType.INDICATION:
            print("  ✓ PASS")
            correct += 1
        else:
            print("  ✗ FAIL - Expected INDICATION")

    print(f"\n{correct}/{len(test_queries)} indication queries classified correctly")
    return correct == len(test_queries)


def test_composition_queries():
    """Test composition query classification"""
    print("\n" + "=" * 80)
    print("TEST: Composition Query Classification")
    print("=" * 80)

    router = get_query_router()

    test_queries = [
        "What is in Newest?",
        "What are the ingredients of Plinest?",
        "What is the composition of Plinest Eye?",
        "Does Newest contain hyaluronic acid?",
    ]

    correct = 0
    for query in test_queries:
        result = router.route_query(query)
        query_type = result["query_type"]

        print(f"\nQuery: {query}")
        print(f"  Type: {query_type.value}")

        if query_type == QueryType.COMPOSITION:
            print("  ✓ PASS")
            correct += 1
        else:
            print("  ✗ FAIL - Expected COMPOSITION")

    print(f"\n{correct}/{len(test_queries)} composition queries classified correctly")
    return correct == len(test_queries)


def test_clinical_evidence_queries():
    """Test clinical evidence query classification"""
    print("\n" + "=" * 80)
    print("TEST: Clinical Evidence Query Classification")
    print("=" * 80)

    router = get_query_router()

    test_queries = [
        "What is the clinical evidence for Newest?",
        "Are there any studies on Plinest efficacy?",
        "What are the results of Plinest Eye clinical trials?",
        "Show me evidence for Newest effectiveness",
    ]

    correct = 0
    for query in test_queries:
        result = router.route_query(query)
        query_type = result["query_type"]
        config = result["config"]

        print(f"\nQuery: {query}")
        print(f"  Type: {query_type.value}")
        print(f"  Boost Doc Types: {config['boost_doc_types']}")

        if query_type == QueryType.CLINICAL_EVIDENCE:
            print("  ✓ PASS")
            correct += 1
        else:
            print("  ✗ FAIL - Expected CLINICAL_EVIDENCE")

    print(f"\n{correct}/{len(test_queries)} clinical evidence queries classified correctly")
    return correct == len(test_queries)


def test_general_queries():
    """Test general query classification (fallback)"""
    print("\n" + "=" * 80)
    print("TEST: General Query Classification (Fallback)")
    print("=" * 80)

    router = get_query_router()

    test_queries = [
        "Tell me about dermatology treatments",
        "What products do you have?",
        "How can I contact support?",
        "What is your company about?",
    ]

    correct = 0
    for query in test_queries:
        result = router.route_query(query)
        query_type = result["query_type"]

        print(f"\nQuery: {query}")
        print(f"  Type: {query_type.value}")

        if query_type == QueryType.GENERAL:
            print("  ✓ PASS")
            correct += 1
        else:
            print("  ✗ FAIL - Expected GENERAL")

    print(f"\n{correct}/{len(test_queries)} general queries classified correctly")
    return correct == len(test_queries)


def test_routing_configuration():
    """Test that routing configurations are properly structured"""
    print("\n" + "=" * 80)
    print("TEST: Routing Configuration Structure")
    print("=" * 80)

    router = get_query_router()

    # Test a protocol query
    result = router.route_query("What is the Newest treatment protocol?")
    config = result["config"]

    print("\nProtocol Query Configuration:")
    print(f"  top_k_multiplier: {config.get('top_k_multiplier')} (expected: 1.2)")
    print(f"  boost_multiplier: {config.get('boost_multiplier')} (expected: 0.15)")
    print(f"  boost_doc_types: {config.get('boost_doc_types')}")
    print(f"  prefer_sections: {config.get('prefer_sections')}")
    print(f"  prefer_chunk_types: {config.get('prefer_chunk_types')}")

    # Verify configuration has all expected keys
    required_keys = ["top_k_multiplier", "boost_multiplier", "boost_doc_types",
                     "prefer_sections", "prefer_chunk_types"]
    has_all_keys = all(key in config for key in required_keys)

    if has_all_keys:
        print("\n✓ PASS - Configuration has all required keys")
        return True
    else:
        print("\n✗ FAIL - Configuration missing keys")
        return False


def main():
    """Run all query router tests"""
    print("=" * 80)
    print("QUERY ROUTER TEST SUITE")
    print("=" * 80)
    print()

    results = {}

    # Test 1: Protocol queries
    print("\nTest 1: Protocol Queries...")
    try:
        results["protocol"] = test_protocol_queries()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["protocol"] = False

    # Test 2: Safety queries
    print("\nTest 2: Safety Queries...")
    try:
        results["safety"] = test_safety_queries()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["safety"] = False

    # Test 3: Technique queries
    print("\nTest 3: Technique Queries...")
    try:
        results["technique"] = test_technique_queries()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["technique"] = False

    # Test 4: Comparison queries
    print("\nTest 4: Comparison Queries...")
    try:
        results["comparison"] = test_comparison_queries()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["comparison"] = False

    # Test 5: Product info queries
    print("\nTest 5: Product Info Queries...")
    try:
        results["product_info"] = test_product_info_queries()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["product_info"] = False

    # Test 6: Indication queries
    print("\nTest 6: Indication Queries...")
    try:
        results["indication"] = test_indication_queries()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["indication"] = False

    # Test 7: Composition queries
    print("\nTest 7: Composition Queries...")
    try:
        results["composition"] = test_composition_queries()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["composition"] = False

    # Test 8: Clinical evidence queries
    print("\nTest 8: Clinical Evidence Queries...")
    try:
        results["clinical_evidence"] = test_clinical_evidence_queries()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["clinical_evidence"] = False

    # Test 9: General queries
    print("\nTest 9: General Queries...")
    try:
        results["general"] = test_general_queries()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["general"] = False

    # Test 10: Routing configuration
    print("\nTest 10: Routing Configuration...")
    try:
        results["config"] = test_routing_configuration()
    except Exception as e:
        print(f"✗ Test failed: {e}")
        results["config"] = False

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")

    passed = sum(1 for r in results.values() if r is True)
    total = len(results)

    if passed == total:
        print(f"\n✅ All {total} tests passed!")
        print("\n💡 Query routing is working correctly")
        print("   - All query types classified accurately")
        print("   - Type-specific configurations applied")
        print("   - Ready for integration testing with RAG service")
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
