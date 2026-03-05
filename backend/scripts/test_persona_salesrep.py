#!/usr/bin/env python3
"""
Test PERSONA 3: DERMAFOCUS SALES REP

Simulates a sales representative needing product facts, competitive positioning,
and clinical evidence for sales pitches.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag_service import get_rag_service
from app.services.claude_service import get_claude_service
import json
import time


def simulate_salesrep_session():
    """
    Simulate Sales Rep's session with competitive and product positioning questions
    """
    print("=" * 80)
    print("PERSONA 3: DERMAFOCUS SALES REP")
    print("=" * 80)
    print("\nProfile:")
    print("  - Needs product facts for clinic pitches")
    print("  - Wants comparisons and differentiators")
    print("  - Looks for clinical evidence to reference")
    print("  - Needs to know full product portfolio")
    print("\n" + "-" * 80)

    # Initialize services
    rag_service = get_rag_service()
    claude_service = get_claude_service()

    # Conversation history
    conversation_history = []

    # Sales Rep's questions
    questions = [
        {
            "id": "Q1",
            "query": "Give me the top 3 differentiators of Plinest® vs other polynucleotide products on the market",
            "expected": "Competitive positioning, unique selling points, may handle competitor mentions carefully"
        },
        {
            "id": "Q2",
            "query": "What clinical evidence can I reference for Newest®?",
            "expected": "List of clinical papers, studies, evidence-based claims"
        },
        {
            "id": "Q3",
            "query": "Does Dermafocus have anything for intimate health / gynecology?",
            "expected": "Should mention NewGyn® product"
        }
    ]

    results = []

    for i, question in enumerate(questions):
        print(f"\n{'=' * 80}")
        print(f"{question['id']}: {question['query']}")
        print(f"{'=' * 80}")
        print(f"Expected: {question['expected']}")

        start_time = time.time()

        try:
            # Get RAG context
            print("\n[1/3] Retrieving context...")
            context_result = rag_service.get_context_for_query(
                query=question['query'],
                max_chunks=10
            )

            retrieval_time = time.time() - start_time
            print(f"      ⏱️  Retrieval: {retrieval_time:.2f}s")

            # Get Claude response
            print("[2/3] Generating response...")
            generation_start = time.time()

            response = claude_service.generate_response(
                query=question['query'],
                context_chunks=context_result['chunks'],
                conversation_history=conversation_history
            )

            generation_time = time.time() - generation_start
            total_time = time.time() - start_time

            print(f"      ⏱️  Generation: {generation_time:.2f}s")
            print(f"      ⏱️  Total: {total_time:.2f}s")

            # Extract response
            response_text = response.get('response', '')
            confidence = response.get('confidence', 0)
            sources = response.get('sources', [])

            # Update conversation history
            conversation_history.append({
                "role": "user",
                "content": question['query']
            })
            conversation_history.append({
                "role": "assistant",
                "content": response_text
            })

            # Display response
            print(f"\n[3/3] Response (confidence: {confidence}):")
            print("-" * 80)
            print(response_text[:700] + ("..." if len(response_text) > 700 else ""))
            print("-" * 80)

            # Display sources
            print(f"\n📚 Sources: {len(sources)}")
            for j, source in enumerate(sources[:5], 1):
                print(f"   [{j}] {source.get('title', 'Unknown')[:60]}")

            # Analyze response quality
            analysis = analyze_salesrep_response(
                question=question,
                response=response_text,
                context_result=context_result,
                sources=sources,
                timing={
                    "retrieval": retrieval_time,
                    "generation": generation_time,
                    "total": total_time
                }
            )

            results.append(analysis)

            # Print quick assessment
            print(f"\n📊 Quick Assessment:")
            print(f"   Relevance: {analysis['relevance']}/10")
            print(f"   Competitive Positioning: {analysis['competitive_score']}/10")
            print(f"   Citation Quality: {analysis['citation_quality']}/10")
            print(f"   Product Knowledge: {analysis['product_knowledge']}/10")

        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                "question_id": question['id'],
                "error": str(e),
                "status": "failed"
            })

        # Pause between questions
        if i < len(questions) - 1:
            print("\n⏸️  [Simulating user typing next question...]")
            time.sleep(1)

    # Final evaluation
    print("\n" + "=" * 80)
    print("PERSONA 3 EVALUATION: DERMAFOCUS SALES REP")
    print("=" * 80)

    evaluate_salesrep_session(results)

    # Save results
    output_file = Path(__file__).parent / "persona_salesrep_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "persona": "Dermafocus Sales Rep",
            "questions": questions,
            "results": results,
            "conversation_history": conversation_history
        }, f, indent=2)

    print(f"\n📄 Detailed results saved to: {output_file}")

    return results


def analyze_salesrep_response(question, response, context_result, sources, timing):
    """Analyze the quality of a response for a sales rep"""

    query = question['query'].lower()
    response_lower = response.lower()

    # Check relevance
    relevance_score = 5
    if question['id'] == 'Q1':
        # Should mention differentiators/benefits
        if any(word in response_lower for word in ['differentiator', 'unique', 'benefit', 'advantage']):
            relevance_score += 2
        if 'plinest' in response_lower:
            relevance_score += 2
    elif question['id'] == 'Q2':
        # Should mention clinical papers
        if any(word in response_lower for word in ['study', 'paper', 'research', 'evidence', 'clinical']):
            relevance_score += 3
    elif question['id'] == 'Q3':
        # Should mention NewGyn
        if 'newgyn' in response_lower:
            relevance_score += 5
        elif 'gynecology' in response_lower or 'intimate' in response_lower:
            relevance_score += 2
    relevance_score = min(relevance_score, 10)

    # Competitive positioning score
    competitive_score = 5
    if question['id'] == 'Q1':
        # Check if handles competitor mention appropriately
        if 'plinest' in response_lower:
            competitive_score += 2
        # Check for structured answer (numbered list, bullet points implied)
        if any(word in response_lower for word in ['1.', '2.', '3.', 'first', 'second', 'third']):
            competitive_score += 3
    competitive_score = min(competitive_score, 10)

    # Citation quality
    citation_score = 0
    if len(sources) > 0:
        citation_score = min(3 + len(sources) * 1.5, 10)
        if question['id'] == 'Q2' and len(sources) >= 3:
            citation_score = 10  # Excellent for clinical evidence query

    # Product knowledge score
    product_knowledge = 5
    if question['id'] == 'Q3':
        if 'newgyn' in response_lower:
            product_knowledge = 10  # Knows the product portfolio
        elif 'don\'t have' in response_lower or 'not' in response_lower:
            product_knowledge = 0  # Doesn't know about NewGyn
    else:
        product_knowledge = 7  # Default for other questions

    # Check for issues
    issues = []
    if timing['total'] > 5:
        issues.append(f"Slow response: {timing['total']:.1f}s - sales rep needs quick facts")
    if question['id'] == 'Q3' and 'newgyn' not in response_lower:
        issues.append("❌ CRITICAL: Doesn't know about NewGyn® product!")
    if question['id'] == 'Q2' and len(sources) < 2:
        issues.append("Insufficient clinical evidence cited for sales pitch")
    if context_result['evidence']['top_score'] < 0.5:
        issues.append(f"Low retrieval confidence: {context_result['evidence']['top_score']:.2f}")
    if 'I don\'t have' in response or 'I cannot' in response:
        issues.append("Refusal - sales rep needs this information for pitches")
    if len(sources) == 0 and question['id'] == 'Q2':
        issues.append("No clinical papers cited when specifically asked for evidence")

    return {
        "question_id": question['id'],
        "query": question['query'],
        "relevance": relevance_score,
        "competitive_score": competitive_score,
        "citation_quality": citation_score,
        "product_knowledge": product_knowledge,
        "timing": timing,
        "top_retrieval_score": context_result['evidence']['top_score'],
        "sources_cited": len(sources),
        "response_length": len(response),
        "knows_newgyn": 'newgyn' in response_lower,
        "issues": issues,
        "status": "success"
    }


def evaluate_salesrep_session(results):
    """Evaluate the overall sales rep session"""

    if not results:
        print("No results to evaluate!")
        return

    # Calculate averages
    avg_relevance = sum(r.get('relevance', 0) for r in results) / len(results)
    avg_competitive = sum(r.get('competitive_score', 0) for r in results) / len(results)
    avg_citation = sum(r.get('citation_quality', 0) for r in results) / len(results)
    avg_product_knowledge = sum(r.get('product_knowledge', 0) for r in results) / len(results)
    avg_time = sum(r.get('timing', {}).get('total', 0) for r in results) / len(results)

    print(f"\n📊 OVERALL SCORES FOR DERMAFOCUS SALES REP:")
    print(f"\n   1. Conversation Flow Quality:        {avg_relevance:.1f}/10")
    print(f"   2. Response Relevance & Accuracy:    {avg_relevance:.1f}/10")
    print(f"   3. Competitive Positioning:          {avg_competitive:.1f}/10")
    print(f"   4. Citation Quality (Evidence):      {avg_citation:.1f}/10")
    print(f"   5. Product Portfolio Knowledge:      {avg_product_knowledge:.1f}/10")

    print(f"\n⏱️  PERFORMANCE:")
    print(f"   Average response time: {avg_time:.2f}s")

    # Check if knows about NewGyn
    knows_newgyn = any(r.get('knows_newgyn', False) for r in results)
    print(f"\n📦 PRODUCT PORTFOLIO:")
    if knows_newgyn:
        print("   ✅ System knows about NewGyn® (intimate health)")
    else:
        print("   ❌ System DOESN'T know about NewGyn® - CRITICAL GAP!")

    # Collect all issues
    all_issues = []
    for r in results:
        all_issues.extend(r.get('issues', []))

    if all_issues:
        print(f"\n⚠️  ISSUES FOUND ({len(all_issues)}):")
        for issue in set(all_issues):
            count = all_issues.count(issue)
            print(f"   - {issue} ({count}x)")
    else:
        print(f"\n✅ No significant issues detected!")

    # Overall assessment
    overall_score = (avg_relevance + avg_competitive + avg_citation + avg_product_knowledge) / 4
    print(f"\n🎯 OVERALL UX SCORE: {overall_score:.1f}/10")

    if overall_score >= 8:
        print("   ✅ EXCELLENT - Sales rep can confidently use for pitches")
    elif overall_score >= 6:
        print("   ⚠️  GOOD - Usable but needs improvements")
    else:
        print("   ❌ NEEDS WORK - Missing critical sales information")


if __name__ == "__main__":
    simulate_salesrep_session()
