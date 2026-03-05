#!/usr/bin/env python3
"""
Comprehensive Persona Testing via HTTP API
Tests 3 user personas making real API calls
"""

import requests
import json
import time
from typing import Dict, List, Any


BASE_URL = "http://localhost:8000/api"


def test_persona_1_dr_sarah():
    """PERSONA 1: Dr. Sarah - Clinical Practitioner"""
    print("=" * 80)
    print("PERSONA 1: DR. SARAH - EXPERIENCED AESTHETIC PRACTITIONER")
    print("=" * 80)

    conversation_id = f"dr_sarah_{int(time.time())}"

    questions = [
        "I currently use Plinest® for periocular rejuvenation. Can Newest® be used for the same area or is it better suited elsewhere?",
        "What's the injection technique for Newest® on cheeks?",
        "Any clinical papers supporting this?",
        "Can you give me the full treatment protocol — sessions, intervals, volumes?"
    ]

    results = []

    for i, question in enumerate(questions, 1):
        print(f"\n[Q{i}] {question[:70]}...")

        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={
                    "question": question,
                    "conversation_id": conversation_id,
                    "history": []
                },
                timeout=30
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '')
                confidence = data.get('confidence', 0)
                sources = data.get('sources', [])

                print(f"  ✓ {elapsed:.1f}s | Confidence: {confidence} | Sources: {len(sources)}")
                print(f"  Response: {answer[:150]}...")

                results.append({
                    "question": question,
                    "answer": answer,
                    "confidence": confidence,
                    "sources": len(sources),
                    "time": elapsed,
                    "status": "success"
                })
            else:
                print(f"  ✗ HTTP {response.status_code}: {response.text[:100]}")
                results.append({
                    "question": question,
                    "error": f"HTTP {response.status_code}",
                    "status": "failed"
                })

        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
            results.append({
                "question": question,
                "error": str(e),
                "status": "failed"
            })

        time.sleep(0.5)

    return {"persona": "Dr. Sarah", "results": results}


def test_persona_2_receptionist():
    """PERSONA 2: Clinic Receptionist - Non-Clinical"""
    print("\n" + "=" * 80)
    print("PERSONA 2: CLINIC RECEPTIONIST - NON-CLINICAL USER")
    print("=" * 80)

    conversation_id = f"receptionist_{int(time.time())}"

    questions = [
        "A patient is asking what polynucleotides do for the skin. How should I explain it simply?",
        "How long does a typical Plinest® treatment session take?",
        "What should I tell patients about aftercare?"
    ]

    results = []

    for i, question in enumerate(questions, 1):
        print(f"\n[Q{i}] {question[:70]}...")

        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={
                    "question": question,
                    "conversation_id": conversation_id,
                    "history": []
                },
                timeout=30
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '')
                confidence = data.get('confidence', 0)

                # Check language appropriateness
                technical_jargon = sum(1 for term in ['intradermal', 'subdermal', 'pharmacokinetics']
                                     if term in answer.lower())

                print(f"  ✓ {elapsed:.1f}s | Confidence: {confidence} | Jargon: {technical_jargon}")
                print(f"  Response: {answer[:150]}...")

                results.append({
                    "question": question,
                    "answer": answer,
                    "confidence": confidence,
                    "jargon_count": technical_jargon,
                    "time": elapsed,
                    "status": "success"
                })
            else:
                print(f"  ✗ HTTP {response.status_code}")
                results.append({
                    "question": question,
                    "error": f"HTTP {response.status_code}",
                    "status": "failed"
                })

        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
            results.append({
                "question": question,
                "error": str(e),
                "status": "failed"
            })

        time.sleep(0.5)

    return {"persona": "Receptionist", "results": results}


def test_persona_3_salesrep():
    """PERSONA 3: Sales Rep"""
    print("\n" + "=" * 80)
    print("PERSONA 3: DERMAFOCUS SALES REP")
    print("=" * 80)

    conversation_id = f"salesrep_{int(time.time())}"

    questions = [
        "Give me the top 3 differentiators of Plinest® vs other polynucleotide products on the market",
        "What clinical evidence can I reference for Newest®?",
        "Does Dermafocus have anything for intimate health / gynecology?"
    ]

    results = []

    for i, question in enumerate(questions, 1):
        print(f"\n[Q{i}] {question[:70]}...")

        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={
                    "question": question,
                    "conversation_id": conversation_id,
                    "history": []
                },
                timeout=30
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '')
                sources = data.get('sources', [])

                # Check for NewGyn mention
                knows_newgyn = 'newgyn' in answer.lower()

                print(f"  ✓ {elapsed:.1f}s | Sources: {len(sources)} | NewGyn: {'✓' if knows_newgyn else '✗'}")
                print(f"  Response: {answer[:150]}...")

                results.append({
                    "question": question,
                    "answer": answer,
                    "sources": len(sources),
                    "knows_newgyn": knows_newgyn,
                    "time": elapsed,
                    "status": "success"
                })
            else:
                print(f"  ✗ HTTP {response.status_code}")
                results.append({
                    "question": question,
                    "error": f"HTTP {response.status_code}",
                    "status": "failed"
                })

        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
            results.append({
                "question": question,
                "error": str(e),
                "status": "failed"
            })

        time.sleep(0.5)

    return {"persona": "Sales Rep", "results": results}


def generate_comprehensive_report(all_results: List[Dict]):
    """Generate final comprehensive report"""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE PERSONA EVALUATION REPORT")
    print("=" * 80)

    for persona_data in all_results:
        persona = persona_data['persona']
        results = persona_data['results']

        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'failed']

        print(f"\n{persona.upper()}")
        print("-" * 80)
        print(f"  Questions: {len(results)}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")

        if successful:
            avg_time = sum(r.get('time', 0) for r in successful) / len(successful)
            print(f"  Avg Response Time: {avg_time:.2f}s")

            if persona == "Dr. Sarah":
                avg_sources = sum(r.get('sources', 0) for r in successful) / len(successful)
                print(f"  Avg Sources: {avg_sources:.1f}")

            elif persona == "Receptionist":
                total_jargon = sum(r.get('jargon_count', 0) for r in successful)
                print(f"  Technical Jargon: {total_jargon} instances")

            elif persona == "Sales Rep":
                knows_newgyn = any(r.get('knows_newgyn', False) for r in successful)
                print(f"  Knows NewGyn®: {'✓ YES' if knows_newgyn else '✗ NO - CRITICAL GAP'}")

    # Save detailed results
    with open('persona_test_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n📄 Detailed results saved to: persona_test_results.json")


if __name__ == "__main__":
    print("Starting Comprehensive Persona Testing...")
    print("Note: Backend must be running at http://localhost:8000\n")

    all_results = []

    try:
        all_results.append(test_persona_1_dr_sarah())
        all_results.append(test_persona_2_receptionist())
        all_results.append(test_persona_3_salesrep())

        generate_comprehensive_report(all_results)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
