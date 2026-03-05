#!/usr/bin/env python3
"""
Clinical QA Testing for DermaAI
Tests 17 queries across different categories to evaluate RAG quality
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag_service import get_rag_service
import json

# Test scenarios
TEST_QUERIES = {
    "A_PRODUCT_KNOWLEDGE": [
        "What is Plinest and what is it used for?",
        "What's the difference between Plinest and Newest?",
        "What injection technique is recommended for Plinest Eye in the periocular area?",
        "What is the recommended treatment protocol for Newest on the neck and décolletage?",
        "Can Plinest be used for hair treatment? What does the protocol involve?"
    ],
    "B_CLINICAL_DEPTH": [
        "What needle gauge and depth is recommended for Plinest decolletage injections?",
        "How many sessions are typically needed for a full Newest perioral rejuvenation course?",
        "What are the contraindications for polynucleotide treatments?",
        "What does the clinical evidence say about PN-HPT for skin quality improvement?",
        "Can you explain the dermal priming paradigm for PN-HPT?"
    ],
    "C_EDGE_CASES": [
        "Should I get Plinest or Botox for my forehead lines?",
        "I have a rash on my arm, what treatment do you recommend?",
        "What's the price of Newest?",
        "Can I inject Plinest myself at home?",
        "Tell me about treatments from Galderma"
    ],
    "D_COMPLEX": [
        "I have a 45-year-old patient with perioral wrinkles and poor skin quality on the neck. What treatment combination would you suggest from the Dermafocus range?",
        "Compare the clinical evidence base for Plinest vs Newest for hand rejuvenation"
    ]
}

def test_query(rag_service, query, category, index):
    """Test a single query and return structured results"""
    try:
        result = rag_service.get_context_for_query(query=query, max_chunks=5)

        # Extract key metrics
        chunks_found = len(result['chunks'])
        evidence_sufficient = result['evidence']['sufficient']
        top_score = result['evidence']['top_score']
        strong_matches = result['evidence']['strong_matches']
        reason = result['evidence']['reason']

        # Get top doc sources
        docs = []
        if result['chunks']:
            for chunk in result['chunks'][:3]:
                doc_id = chunk['metadata'].get('doc_id', 'unknown')
                score = chunk.get('score', 0)
                docs.append(f"{doc_id[:50]} ({score:.3f})")

        # Assess quality
        if evidence_sufficient and top_score >= 0.70:
            assessment = "PASS"
        elif evidence_sufficient and top_score >= 0.50:
            assessment = "PARTIAL"
        else:
            assessment = "FAIL"

        return {
            "category": category,
            "index": index,
            "query": query,
            "chunks_found": chunks_found,
            "evidence_sufficient": evidence_sufficient,
            "top_score": top_score,
            "strong_matches": strong_matches,
            "reason": reason,
            "top_docs": docs,
            "assessment": assessment
        }
    except Exception as e:
        return {
            "category": category,
            "index": index,
            "query": query,
            "error": str(e),
            "assessment": "ERROR"
        }

def main():
    print("=" * 80)
    print("DERMAAI CLINICAL QA TEST SUITE")
    print("=" * 80)
    print("\nInitializing RAG service...")

    rag_service = get_rag_service()

    all_results = []

    for category, queries in TEST_QUERIES.items():
        print(f"\n{'='*80}")
        print(f"CATEGORY: {category}")
        print(f"{'='*80}")

        for i, query in enumerate(queries, 1):
            print(f"\n[{category}-{i}] Testing: {query[:60]}...")
            result = test_query(rag_service, query, category, i)
            all_results.append(result)

            if "error" in result:
                print(f"  ❌ ERROR: {result['error']}")
            else:
                print(f"  {result['assessment']}: Score={result['top_score']:.3f}, Chunks={result['chunks_found']}, Sufficient={result['evidence_sufficient']}")
                if result['top_docs']:
                    print(f"  Top doc: {result['top_docs'][0]}")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    pass_count = sum(1 for r in all_results if r['assessment'] == 'PASS')
    partial_count = sum(1 for r in all_results if r['assessment'] == 'PARTIAL')
    fail_count = sum(1 for r in all_results if r['assessment'] == 'FAIL')
    error_count = sum(1 for r in all_results if r['assessment'] == 'ERROR')

    total = len(all_results)

    print(f"\nResults: {pass_count} PASS / {partial_count} PARTIAL / {fail_count} FAIL / {error_count} ERROR (Total: {total})")
    print(f"Score: {pass_count}/{total} queries handled well ({pass_count/total*100:.1f}%)")

    # Show failures
    failures = [r for r in all_results if r['assessment'] in ['FAIL', 'PARTIAL']]
    if failures:
        print(f"\n⚠️  Queries needing improvement ({len(failures)}):")
        for r in failures:
            print(f"  [{r['category']}-{r['index']}] {r['assessment']}: {r['query'][:60]}")
            print(f"      Reason: {r.get('reason', 'N/A')}, Top score: {r.get('top_score', 0):.3f}")

    # Save detailed results
    output_file = Path(__file__).parent / "clinical_qa_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n✓ Detailed results saved to: {output_file}")

    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
