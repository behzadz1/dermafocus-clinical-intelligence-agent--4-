#!/usr/bin/env python3
"""
Test Contraindications P0 Fix

Tests if the contraindications query now retrieves the newly indexed safety document
and achieves a passing score (>= 0.50).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag_service import get_rag_service
import json


def test_contraindications_query():
    """Test the contraindications query that previously failed"""

    print("=" * 80)
    print("TESTING CONTRAINDICATIONS P0 FIX")
    print("=" * 80)

    # The query that failed in clinical QA test with score 0.336
    query = "What are the contraindications for polynucleotide treatments?"

    print(f"\n📝 Query: '{query}'")
    print("\n🔍 Retrieving context...")

    # Initialize RAG service
    rag_service = get_rag_service()

    # Get context (same as clinical_qa_test.py)
    result = rag_service.get_context_for_query(query=query, max_chunks=10)

    # Extract metrics
    chunks_found = len(result['chunks'])
    evidence_sufficient = result['evidence']['sufficient']
    top_score = result['evidence']['top_score']
    strong_matches = result['evidence']['strong_matches']
    reason = result['evidence']['reason']

    print(f"\n📊 Results:")
    print(f"   Chunks found: {chunks_found}")
    print(f"   Evidence sufficient: {evidence_sufficient}")
    print(f"   Top score: {top_score:.3f}")
    print(f"   Strong matches: {strong_matches}")
    print(f"   Reason: {reason}")

    # Show top retrieved documents
    print(f"\n📄 Top Retrieved Documents:")
    for i, chunk in enumerate(result['chunks'][:5], 1):
        doc_id = chunk['metadata'].get('doc_id', 'unknown')
        doc_type = chunk['metadata'].get('doc_type', 'unknown')
        score = chunk.get('score', 0)
        section = chunk['metadata'].get('section', '')
        product = chunk['metadata'].get('product', '')

        print(f"\n   [{i}] Score: {score:.3f}")
        print(f"       Doc: {doc_id[:60]}")
        print(f"       Type: {doc_type}")
        if product:
            print(f"       Product: {product}")
        if section:
            print(f"       Section: {section}")
        print(f"       Preview: {chunk['text'][:150]}...")

    # Assess improvement
    print("\n" + "=" * 80)
    print("ASSESSMENT")
    print("=" * 80)

    previous_score = 0.336
    print(f"\n📈 Score Improvement:")
    print(f"   Previous score: {previous_score:.3f} (FAIL)")
    print(f"   Current score:  {top_score:.3f}")
    print(f"   Improvement:    {(top_score - previous_score):.3f} ({((top_score - previous_score) / previous_score * 100):.1f}%)")

    # Determine if fix worked
    if evidence_sufficient and top_score >= 0.70:
        assessment = "✅ PASS - Excellent retrieval!"
        status = "SUCCESS"
    elif evidence_sufficient and top_score >= 0.50:
        assessment = "⚠️  PARTIAL - Acceptable but could improve"
        status = "PARTIAL"
    else:
        assessment = "❌ FAIL - Still needs work"
        status = "FAIL"

    print(f"\n🎯 Assessment: {assessment}")

    # Check if safety document is being retrieved
    safety_doc_found = any(
        chunk['metadata'].get('doc_id') == 'dermafocus_safety_profiles'
        for chunk in result['chunks']
    )

    print(f"\n🔍 Safety Document Found: {'✅ Yes' if safety_doc_found else '❌ No'}")

    if safety_doc_found:
        safety_chunks = [
            chunk for chunk in result['chunks']
            if chunk['metadata'].get('doc_id') == 'dermafocus_safety_profiles'
        ]
        print(f"   Safety chunks retrieved: {len(safety_chunks)}")
        print(f"   Top safety chunk score: {max(c.get('score', 0) for c in safety_chunks):.3f}")

    # Final verdict
    print("\n" + "=" * 80)
    if status == "SUCCESS":
        print("✅ P0 FIX VALIDATED - Contraindications query now passing!")
    elif status == "PARTIAL":
        print("⚠️  P0 FIX PARTIALLY WORKING - Retrieval improved but not optimal")
        print("   Consider:")
        print("   - Increasing safety boost further (0.30 → 0.35)")
        print("   - Adding more safety-related query expansion terms")
        print("   - Checking if reranker is prioritizing safety content")
    else:
        print("❌ P0 FIX NEEDS MORE WORK - Contraindications query still failing")
        print("   Issues to investigate:")
        print("   - Safety document may not be indexed correctly")
        print("   - Query router may not be detecting this as a safety query")
        print("   - Embedding quality for safety content may need improvement")

    print("=" * 80)

    # Save detailed results
    test_results = {
        "query": query,
        "previous_score": previous_score,
        "current_score": top_score,
        "improvement": top_score - previous_score,
        "improvement_pct": (top_score - previous_score) / previous_score * 100,
        "evidence_sufficient": evidence_sufficient,
        "strong_matches": strong_matches,
        "chunks_found": chunks_found,
        "safety_doc_found": safety_doc_found,
        "status": status,
        "top_chunks": [
            {
                "doc_id": c['metadata'].get('doc_id', ''),
                "doc_type": c['metadata'].get('doc_type', ''),
                "score": c.get('score', 0),
                "product": c['metadata'].get('product', ''),
                "section": c['metadata'].get('section', '')
            }
            for c in result['chunks'][:5]
        ]
    }

    output_file = Path(__file__).parent / "contraindications_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2)

    print(f"\n📄 Detailed results saved to: {output_file}")

    return 0 if status == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(test_contraindications_query())
