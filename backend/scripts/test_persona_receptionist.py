#!/usr/bin/env python3
"""
Test PERSONA 2: CLINIC RECEPTIONIST - Non-Clinical User

Simulates a receptionist needing to answer basic patient questions with
simple language and practical information.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag_service import get_rag_service
from app.services.claude_service import get_claude_service
import json
import time


def simulate_receptionist_session():
    """
    Simulate Receptionist's session with 3 basic questions
    """
    print("=" * 80)
    print("PERSONA 2: CLINIC RECEPTIONIST - NON-CLINICAL USER")
    print("=" * 80)
    print("\nProfile:")
    print("  - Needs to answer basic patient questions")
    print("  - Low technical knowledge")
    print("  - Expects plain language explanations")
    print("  - Asks about practical logistics (time, aftercare)")
    print("\n" + "-" * 80)

    # Initialize services
    rag_service = get_rag_service()
    claude_service = get_claude_service()

    # Conversation history
    conversation_history = []

    # Receptionist's questions
    questions = [
        {
            "id": "Q1",
            "query": "A patient is asking what polynucleotides do for the skin. How should I explain it simply?",
            "expected": "Simple, non-technical language. Benefits-focused explanation."
        },
        {
            "id": "Q2",
            "query": "How long does a typical Plinest® treatment session take?",
            "expected": "Practical timing information for scheduling"
        },
        {
            "id": "Q3",
            "query": "What should I tell patients about aftercare?",
            "expected": "Clear post-treatment instructions from patient materials"
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
            print(response_text[:600] + ("..." if len(response_text) > 600 else ""))
            print("-" * 80)

            # Display sources
            print(f"\n📚 Sources: {len(sources)}")
            for j, source in enumerate(sources[:3], 1):
                print(f"   [{j}] {source.get('title', 'Unknown')[:60]}")

            # Analyze response quality
            analysis = analyze_receptionist_response(
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
            print(f"   Plain Language: {analysis['tone']}/10")
            print(f"   Practical Info: {analysis['practical_score']}/10")

        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
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
    print("PERSONA 2 EVALUATION: CLINIC RECEPTIONIST")
    print("=" * 80)

    evaluate_receptionist_session(results)

    # Save results
    output_file = Path(__file__).parent / "persona_receptionist_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "persona": "Clinic Receptionist - Non-Clinical User",
            "questions": questions,
            "results": results,
            "conversation_history": conversation_history
        }, f, indent=2)

    print(f"\n📄 Detailed results saved to: {output_file}")

    return results


def analyze_receptionist_response(question, response, context_result, sources, timing):
    """Analyze the quality of a response for a non-clinical user"""

    query = question['query'].lower()
    response_lower = response.lower()

    # Check relevance
    relevance_score = 5
    if 'polynucleotides' in query and ('rejuvenation' in response_lower or 'skin' in response_lower):
        relevance_score += 2
    if 'take' in query or 'long' in query and ('minutes' in response_lower or 'session' in response_lower):
        relevance_score += 2
    if 'aftercare' in query and ('after' in response_lower or 'avoid' in response_lower or 'care' in response_lower):
        relevance_score += 2
    relevance_score = min(relevance_score, 10)

    # Check tone (should be SIMPLE, not technical)
    technical_jargon = ['intradermal', 'subdermal', 'gauge', 'reconstitute', 'pharmacokinetics']
    jargon_count = sum(1 for term in technical_jargon if term in response_lower)

    # Plain language indicators
    plain_indicators = ['helps', 'improves', 'makes', 'will', 'should', 'patients']
    plain_count = sum(1 for term in plain_indicators if term in response_lower)

    # Tone score: high plain language, low jargon
    tone_score = min(5 + plain_count - jargon_count, 10)
    tone_score = max(tone_score, 1)

    # Check practical info (times, instructions)
    practical_score = 5
    if question['id'] == 'Q2':
        # Should mention time duration
        if any(word in response_lower for word in ['minutes', 'hour', 'time', 'take']):
            practical_score += 3
        if any(word in response_lower for word in ['15', '20', '30', '45', '60']):
            practical_score += 2
    elif question['id'] == 'Q3':
        # Should have clear instructions
        if any(word in response_lower for word in ['avoid', 'don\'t', 'should', 'must']):
            practical_score += 3
        if any(word in response_lower for word in ['24', '48', '72', 'hours', 'days']):
            practical_score += 2
    practical_score = min(practical_score, 10)

    # Check for issues
    issues = []
    if timing['total'] > 5:
        issues.append(f"Slow response: {timing['total']:.1f}s")
    if jargon_count > 2:
        issues.append(f"Too technical ({jargon_count} jargon terms) for non-clinical user")
    if context_result['evidence']['top_score'] < 0.5:
        issues.append(f"Low retrieval confidence: {context_result['evidence']['top_score']:.2f}")
    if 'I don\'t have' in response or 'I cannot' in response:
        issues.append("Refusal - receptionist needs this info to help patients")
    if len(response) < 80:
        issues.append("Response too brief for patient-facing explanation")
    if len(sources) == 0:
        issues.append("No sources cited")

    return {
        "question_id": question['id'],
        "query": question['query'],
        "relevance": relevance_score,
        "tone": tone_score,  # Plain language score
        "practical_score": practical_score,
        "timing": timing,
        "top_retrieval_score": context_result['evidence']['top_score'],
        "jargon_count": jargon_count,
        "plain_language_count": plain_count,
        "response_length": len(response),
        "issues": issues,
        "status": "success"
    }


def evaluate_receptionist_session(results):
    """Evaluate the overall receptionist session"""

    if not results:
        print("No results to evaluate!")
        return

    # Calculate averages
    avg_relevance = sum(r.get('relevance', 0) for r in results) / len(results)
    avg_tone = sum(r.get('tone', 0) for r in results) / len(results)
    avg_practical = sum(r.get('practical_score', 0) for r in results) / len(results)
    avg_time = sum(r.get('timing', {}).get('total', 0) for r in results) / len(results)

    print(f"\n📊 OVERALL SCORES FOR CLINIC RECEPTIONIST:")
    print(f"\n   1. Conversation Flow Quality:        {avg_relevance:.1f}/10")
    print(f"   2. Response Relevance & Accuracy:    {avg_relevance:.1f}/10")
    print(f"   3. Plain Language Appropriateness:   {avg_tone:.1f}/10")
    print(f"   4. Practical Information Quality:    {avg_practical:.1f}/10")
    print(f"   5. Source Citation Quality:          N/A (not critical for this role)")

    print(f"\n⏱️  PERFORMANCE:")
    print(f"   Average response time: {avg_time:.2f}s")

    # Language analysis
    total_jargon = sum(r.get('jargon_count', 0) for r in results)
    total_plain = sum(r.get('plain_language_count', 0) for r in results)
    print(f"\n📝 LANGUAGE ANALYSIS:")
    print(f"   Technical jargon count: {total_jargon}")
    print(f"   Plain language count: {total_plain}")
    if total_jargon > total_plain:
        print("   ⚠️  Language too technical for non-clinical user!")

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
    overall_score = (avg_relevance + avg_tone + avg_practical) / 3
    print(f"\n🎯 OVERALL UX SCORE: {overall_score:.1f}/10")

    if overall_score >= 8:
        print("   ✅ EXCELLENT - Receptionist can confidently use this")
    elif overall_score >= 6:
        print("   ⚠️  GOOD - Minor improvements needed")
    else:
        print("   ❌ NEEDS WORK - Too complex for non-clinical staff")


if __name__ == "__main__":
    simulate_receptionist_session()
