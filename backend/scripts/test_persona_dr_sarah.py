#!/usr/bin/env python3
"""
Test PERSONA 1: Dr. Sarah - Experienced Aesthetic Practitioner

Simulates a clinical professional's conversational flow with technical questions
and follow-ups to test context retention and clinical accuracy.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag_service import get_rag_service
from app.services.claude_service import get_claude_service
import json
import time


def simulate_dr_sarah_session():
    """
    Simulate Dr. Sarah's session with 4 questions in sequence
    """
    print("=" * 80)
    print("PERSONA 1: DR. SARAH - EXPERIENCED AESTHETIC PRACTITIONER")
    print("=" * 80)
    print("\nProfile:")
    print("  - Uses Plinest® for 2 years")
    print("  - Exploring Newest® for new treatment areas")
    print("  - Expects precise clinical language and protocols")
    print("  - Asks rapid follow-up questions")
    print("\n" + "-" * 80)

    # Initialize services
    rag_service = get_rag_service()
    claude_service = get_claude_service()

    # Conversation history (for context retention)
    conversation_history = []

    # Dr. Sarah's questions
    questions = [
        {
            "id": "Q1",
            "query": "I currently use Plinest® for periocular rejuvenation. Can Newest® be used for the same area or is it better suited elsewhere?",
            "expected": "Product comparison, treatment area guidance, clinical differentiation"
        },
        {
            "id": "Q2",
            "query": "What's the injection technique for Newest® on cheeks?",
            "expected": "Specific technique details, needle gauge, depth, injection pattern"
        },
        {
            "id": "Q3",
            "query": "Any clinical papers supporting this?",
            "expected": "Should understand 'this' refers to Newest® cheek treatment from Q2"
        },
        {
            "id": "Q4",
            "query": "Can you give me the full treatment protocol — sessions, intervals, volumes?",
            "expected": "Complete protocol with numbers, schedule, dosing"
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
            print(response_text[:500] + ("..." if len(response_text) > 500 else ""))
            print("-" * 80)

            # Display sources
            print(f"\n📚 Sources: {len(sources)}")
            for j, source in enumerate(sources[:3], 1):
                print(f"   [{j}] {source.get('title', 'Unknown')[:60]}")

            # Analyze response quality
            analysis = analyze_response_quality(
                question=question,
                response=response_text,
                context_result=context_result,
                sources=sources,
                conversation_history=conversation_history,
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
            print(f"   Clinical Tone: {analysis['tone']}/10")
            print(f"   Context Retention: {analysis['context_retention']}/10")
            print(f"   Citation Quality: {analysis['citation_quality']}/10")

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
    print("PERSONA 1 EVALUATION: DR. SARAH")
    print("=" * 80)

    evaluate_overall_session(results, "Dr. Sarah - Clinical Practitioner")

    # Save results
    output_file = Path(__file__).parent / "persona_dr_sarah_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "persona": "Dr. Sarah - Experienced Aesthetic Practitioner",
            "questions": questions,
            "results": results,
            "conversation_history": conversation_history
        }, f, indent=2)

    print(f"\n📄 Detailed results saved to: {output_file}")

    return results


def analyze_response_quality(question, response, context_result, sources, conversation_history, timing):
    """Analyze the quality of a single response"""

    # Check relevance
    query = question['query'].lower()
    response_lower = response.lower()

    relevance_score = 5  # Base score

    # Check for key terms from question
    if 'newest' in query and 'newest' in response_lower:
        relevance_score += 2
    if 'plinest' in query and 'plinest' in response_lower:
        relevance_score += 1
    if 'technique' in query and ('technique' in response_lower or 'injection' in response_lower):
        relevance_score += 1
    if 'protocol' in query and ('protocol' in response_lower or 'session' in response_lower):
        relevance_score += 1

    relevance_score = min(relevance_score, 10)

    # Check clinical tone (technical language)
    clinical_terms = ['intradermal', 'subdermal', 'gauge', 'ml', 'sessions', 'interval', 'protocol', 'technique']
    clinical_count = sum(1 for term in clinical_terms if term in response_lower)
    tone_score = min(5 + clinical_count, 10)

    # Check context retention (for follow-up questions)
    context_retention_score = 10
    if question['id'] in ['Q3', 'Q4']:
        # These are follow-ups - should reference previous context
        if len(conversation_history) < 2:
            context_retention_score = 3
        elif question['id'] == 'Q3' and 'newest' not in response_lower:
            context_retention_score = 5  # Should remember Q2 was about Newest
        elif question['id'] == 'Q4' and ('session' not in response_lower and 'protocol' not in response_lower):
            context_retention_score = 4

    # Check citation quality
    citation_score = 0
    if len(sources) > 0:
        citation_score = min(3 + len(sources) * 2, 10)
        # Check if sources are relevant
        if any('newest' in s.get('title', '').lower() for s in sources) and 'newest' in query:
            citation_score = min(citation_score + 2, 10)

    # Check for specific issues
    issues = []
    if timing['total'] > 5:
        issues.append(f"Slow response time: {timing['total']:.1f}s")
    if len(sources) == 0:
        issues.append("No sources cited")
    if context_result['evidence']['top_score'] < 0.5:
        issues.append(f"Low retrieval confidence: {context_result['evidence']['top_score']:.2f}")
    if len(response) < 100:
        issues.append("Response too brief")
    if 'I don\'t have' in response or 'I cannot' in response:
        issues.append("Refusal detected - may lack information")

    return {
        "question_id": question['id'],
        "query": question['query'],
        "relevance": relevance_score,
        "tone": tone_score,
        "context_retention": context_retention_score,
        "citation_quality": citation_score,
        "timing": timing,
        "top_retrieval_score": context_result['evidence']['top_score'],
        "chunks_retrieved": len(context_result['chunks']),
        "sources_cited": len(sources),
        "response_length": len(response),
        "issues": issues,
        "status": "success"
    }


def evaluate_overall_session(results, persona_name):
    """Evaluate the overall session across all questions"""

    if not results:
        print("No results to evaluate!")
        return

    # Calculate averages
    avg_relevance = sum(r.get('relevance', 0) for r in results) / len(results)
    avg_tone = sum(r.get('tone', 0) for r in results) / len(results)
    avg_context = sum(r.get('context_retention', 0) for r in results) / len(results)
    avg_citation = sum(r.get('citation_quality', 0) for r in results) / len(results)
    avg_time = sum(r.get('timing', {}).get('total', 0) for r in results) / len(results)

    # Calculate conversation flow quality
    flow_score = avg_context  # Based on context retention

    print(f"\n📊 OVERALL SCORES FOR {persona_name.upper()}:")
    print(f"\n   1. Conversation Flow Quality:        {flow_score:.1f}/10")
    print(f"   2. Response Relevance & Accuracy:    {avg_relevance:.1f}/10")
    print(f"   3. Tone Appropriateness:             {avg_tone:.1f}/10")
    print(f"   4. Context Retention Across Turns:   {avg_context:.1f}/10")
    print(f"   5. Source Citation Quality:          {avg_citation:.1f}/10")

    print(f"\n⏱️  PERFORMANCE:")
    print(f"   Average response time: {avg_time:.2f}s")

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
    overall_score = (avg_relevance + avg_tone + avg_context + avg_citation + flow_score) / 5
    print(f"\n🎯 OVERALL UX SCORE: {overall_score:.1f}/10")

    if overall_score >= 8:
        print("   ✅ EXCELLENT - Ready for this user type")
    elif overall_score >= 6:
        print("   ⚠️  GOOD - Minor improvements needed")
    else:
        print("   ❌ NEEDS WORK - Significant issues to address")


if __name__ == "__main__":
    simulate_dr_sarah_session()
