#!/usr/bin/env python3
"""
RAG Quality Validation Script

Tests the RAG system with diverse semantic challenges and measures
confidence and answer quality.

Usage:
    python scripts/validate_rag_quality.py
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag_service import get_rag_service
from app.services.claude_service import get_claude_service
from app.services.embedding_service import get_embedding_service
from app.services.pinecone_service import get_pinecone_service


@dataclass
class TestQuestion:
    """A test question with expected validation criteria"""
    id: str
    question: str
    category: str  # semantic challenge type
    difficulty: str  # easy, medium, hard
    expected_keywords: List[str]  # keywords that should appear in answer
    expected_products: List[str]  # products that should be mentioned
    validation_notes: str  # what makes a good answer


@dataclass
class TestResult:
    """Result of a single test"""
    question_id: str
    question: str
    category: str
    difficulty: str
    answer: str
    retrieval_confidence: float  # from Pinecone scores
    keyword_match_rate: float  # % of expected keywords found
    product_match_rate: float  # % of expected products mentioned
    sources_cited: int
    response_length: int
    passed: bool
    notes: str


# Define test questions with diverse semantic challenges
TEST_QUESTIONS: List[TestQuestion] = [
    # === DIRECT FACTUAL (Easy) ===
    TestQuestion(
        id="DF01",
        question="What is Newest?",
        category="direct_factual",
        difficulty="easy",
        expected_keywords=["polynucleotides", "hyaluronic acid", "bio-remodeling", "HPT"],
        expected_products=["Newest"],
        validation_notes="Should explain composition and mechanism"
    ),
    TestQuestion(
        id="DF02",
        question="What is the composition of Plinest Eye?",
        category="direct_factual",
        difficulty="easy",
        expected_keywords=["polynucleotides", "periorbital", "mg", "ml"],
        expected_products=["Plinest Eye"],
        validation_notes="Should mention PN-HPT concentration and volume"
    ),

    # === PROCEDURAL/HOW-TO (Medium) ===
    TestQuestion(
        id="PR01",
        question="How do I treat hands with polynucleotides?",
        category="procedural",
        difficulty="medium",
        expected_keywords=["injection", "technique", "needle", "sessions", "dorsum"],
        expected_products=["Newest", "Plinest"],
        validation_notes="Should describe injection technique and protocol"
    ),
    TestQuestion(
        id="PR02",
        question="What is the treatment protocol for periorbital rejuvenation?",
        category="procedural",
        difficulty="medium",
        expected_keywords=["sessions", "weeks", "technique", "depth", "periorbital"],
        expected_products=["Plinest Eye"],
        validation_notes="Should include number of sessions, timing, technique"
    ),

    # === COMPARISON (Medium-Hard) ===
    TestQuestion(
        id="CP01",
        question="What's the difference between Newest and Plinest?",
        category="comparison",
        difficulty="medium",
        expected_keywords=["hyaluronic", "polynucleotides", "composition", "indication"],
        expected_products=["Newest", "Plinest"],
        validation_notes="Should contrast compositions and use cases"
    ),
    TestQuestion(
        id="CP02",
        question="Polynucleotides vs PRP for hair loss - which is better?",
        category="comparison",
        difficulty="hard",
        expected_keywords=["hair", "follicle", "growth", "efficacy", "study"],
        expected_products=["Plinest", "Hair"],
        validation_notes="Should reference clinical evidence for both"
    ),

    # === SAFETY/CONTRAINDICATIONS (Critical) ===
    TestQuestion(
        id="SF01",
        question="What are the contraindications for polynucleotide treatments?",
        category="safety",
        difficulty="medium",
        expected_keywords=["contraindication", "allergy", "infection", "pregnancy", "autoimmune"],
        expected_products=[],
        validation_notes="Must list absolute and relative contraindications"
    ),
    TestQuestion(
        id="SF02",
        question="Are there any side effects I should warn patients about?",
        category="safety",
        difficulty="medium",
        expected_keywords=["side effect", "swelling", "bruising", "redness", "temporary"],
        expected_products=[],
        validation_notes="Should list common and rare side effects"
    ),

    # === MECHANISM/SCIENTIFIC (Hard) ===
    TestQuestion(
        id="MC01",
        question="How do polynucleotides stimulate collagen production?",
        category="mechanism",
        difficulty="hard",
        expected_keywords=["fibroblast", "collagen", "receptor", "synthesis", "extracellular"],
        expected_products=[],
        validation_notes="Should explain cellular mechanism"
    ),
    TestQuestion(
        id="MC02",
        question="What is the mechanism of action of PN-HPT?",
        category="mechanism",
        difficulty="hard",
        expected_keywords=["polynucleotides", "HPT", "purified", "regeneration", "cell"],
        expected_products=[],
        validation_notes="Should explain what HPT means and how it works"
    ),

    # === VAGUE/AMBIGUOUS (Hard) ===
    TestQuestion(
        id="VG01",
        question="What should I use for aging skin?",
        category="vague_query",
        difficulty="hard",
        expected_keywords=["treatment", "skin", "rejuvenation", "collagen"],
        expected_products=["Newest", "Plinest"],
        validation_notes="Should ask clarifying questions or provide options"
    ),
    TestQuestion(
        id="VG02",
        question="My patient has wrinkles",
        category="vague_query",
        difficulty="hard",
        expected_keywords=["wrinkle", "treatment", "area", "depth"],
        expected_products=[],
        validation_notes="Should seek more info or provide general guidance"
    ),

    # === TERMINOLOGY VARIATIONS (Medium) ===
    TestQuestion(
        id="TV01",
        question="Tell me about bio-remodelers for skin",
        category="terminology_variation",
        difficulty="medium",
        expected_keywords=["bio-remodeling", "polynucleotides", "regeneration"],
        expected_products=["Newest", "Plinest"],
        validation_notes="Should recognize bio-remodeler terminology"
    ),
    TestQuestion(
        id="TV02",
        question="What PN products do you have for the face?",
        category="terminology_variation",
        difficulty="medium",
        expected_keywords=["polynucleotides", "face", "facial"],
        expected_products=["Plinest", "Newest"],
        validation_notes="Should understand PN = polynucleotides"
    ),

    # === MULTI-PART QUESTIONS (Hard) ===
    TestQuestion(
        id="MP01",
        question="For nasolabial folds, what product should I use, how many sessions, and what's the expected downtime?",
        category="multi_part",
        difficulty="hard",
        expected_keywords=["nasolabial", "sessions", "downtime", "technique"],
        expected_products=["Newest", "Plinest"],
        validation_notes="Should address all three parts"
    ),

    # === CLINICAL SCENARIO (Hard) ===
    TestQuestion(
        id="CS01",
        question="A 45-year-old woman with thin crepey skin under her eyes wants treatment. What do you recommend?",
        category="clinical_scenario",
        difficulty="hard",
        expected_keywords=["periorbital", "thin skin", "treatment", "technique"],
        expected_products=["Plinest Eye"],
        validation_notes="Should recommend appropriate product with rationale"
    ),
    TestQuestion(
        id="CS02",
        question="Patient presents with hair thinning and is interested in non-surgical options",
        category="clinical_scenario",
        difficulty="hard",
        expected_keywords=["hair", "scalp", "follicle", "treatment", "protocol"],
        expected_products=["Hair", "Scalp"],
        validation_notes="Should recommend hair-specific protocol"
    ),

    # === DOSING/TECHNICAL (Medium) ===
    TestQuestion(
        id="DT01",
        question="What needle size should I use for periorbital injections?",
        category="dosing_technical",
        difficulty="medium",
        expected_keywords=["needle", "gauge", "30G", "27G", "technique"],
        expected_products=["Plinest Eye"],
        validation_notes="Should specify needle gauge and depth"
    ),
    TestQuestion(
        id="DT02",
        question="How many ml of Newest per treatment area?",
        category="dosing_technical",
        difficulty="medium",
        expected_keywords=["ml", "volume", "area", "dose"],
        expected_products=["Newest"],
        validation_notes="Should provide specific dosing guidance"
    ),

    # === NEGATIVE/EDGE CASES ===
    TestQuestion(
        id="NG01",
        question="Can I use polynucleotides with botox in the same session?",
        category="combination_therapy",
        difficulty="hard",
        expected_keywords=["combination", "botox", "same", "session", "treatment"],
        expected_products=[],
        validation_notes="Should address combination safety"
    ),
]


async def run_validation():
    """Run validation tests on the RAG system"""

    print("=" * 70)
    print("RAG QUALITY VALIDATION")
    print("=" * 70)
    print(f"Test questions: {len(TEST_QUESTIONS)}")
    print(f"Categories: {len(set(q.category for q in TEST_QUESTIONS))}")
    print("=" * 70)

    # Initialize services
    rag_service = get_rag_service()
    claude_service = get_claude_service()

    results: List[TestResult] = []

    for i, test_q in enumerate(TEST_QUESTIONS, 1):
        print(f"\n[{i}/{len(TEST_QUESTIONS)}] {test_q.category.upper()}: {test_q.question[:50]}...")

        try:
            # Get RAG context (sync method)
            context_result = rag_service.get_context_for_query(test_q.question)
            context = context_result.get("context_text", "")  # Fixed: use context_text
            sources = context_result.get("sources", [])

            # Calculate retrieval confidence from Pinecone scores
            # Fixed: use relevance_score instead of score
            scores = [s.get("relevance_score", 0) for s in sources if "relevance_score" in s]
            avg_retrieval_confidence = sum(scores) / len(scores) if scores else 0

            # Generate answer using Claude (async method)
            response = await claude_service.generate_response(
                user_message=test_q.question,
                context=context
            )
            answer = response.get("answer", "")

            # Validate answer
            answer_lower = answer.lower()

            # Check keyword matches
            keywords_found = sum(1 for kw in test_q.expected_keywords if kw.lower() in answer_lower)
            keyword_match_rate = keywords_found / len(test_q.expected_keywords) if test_q.expected_keywords else 1.0

            # Check product mentions
            products_found = sum(1 for prod in test_q.expected_products if prod.lower() in answer_lower)
            product_match_rate = products_found / len(test_q.expected_products) if test_q.expected_products else 1.0

            # Determine pass/fail
            # Pass criteria: retrieval confidence > 0.5 AND keyword match > 50%
            passed = avg_retrieval_confidence > 0.5 and keyword_match_rate >= 0.5

            # Build notes
            notes = []
            if avg_retrieval_confidence < 0.5:
                notes.append(f"Low retrieval confidence ({avg_retrieval_confidence:.2f})")
            if keyword_match_rate < 0.5:
                missing_kw = [kw for kw in test_q.expected_keywords if kw.lower() not in answer_lower]
                notes.append(f"Missing keywords: {missing_kw[:3]}")
            if test_q.expected_products and product_match_rate < 0.5:
                missing_prod = [p for p in test_q.expected_products if p.lower() not in answer_lower]
                notes.append(f"Missing products: {missing_prod}")

            result = TestResult(
                question_id=test_q.id,
                question=test_q.question,
                category=test_q.category,
                difficulty=test_q.difficulty,
                answer=answer[:500] + "..." if len(answer) > 500 else answer,
                retrieval_confidence=round(avg_retrieval_confidence, 3),
                keyword_match_rate=round(keyword_match_rate, 3),
                product_match_rate=round(product_match_rate, 3),
                sources_cited=len(sources),
                response_length=len(answer),
                passed=passed,
                notes="; ".join(notes) if notes else "OK"
            )
            results.append(result)

            # Print summary
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status} | Retrieval: {avg_retrieval_confidence:.2f} | Keywords: {keyword_match_rate:.0%} | Products: {product_match_rate:.0%}")

        except Exception as e:
            print(f"   ❌ ERROR: {str(e)[:50]}")
            results.append(TestResult(
                question_id=test_q.id,
                question=test_q.question,
                category=test_q.category,
                difficulty=test_q.difficulty,
                answer=f"ERROR: {str(e)}",
                retrieval_confidence=0,
                keyword_match_rate=0,
                product_match_rate=0,
                sources_cited=0,
                response_length=0,
                passed=False,
                notes=f"Error: {str(e)[:100]}"
            ))

    # Generate report
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    # Overall stats
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    print(f"\n📊 Overall Results:")
    print(f"   Total tests:  {total}")
    print(f"   Passed:       {passed} ({passed/total:.0%})")
    print(f"   Failed:       {failed} ({failed/total:.0%})")

    # Average confidence
    avg_retrieval = sum(r.retrieval_confidence for r in results) / total
    avg_keyword = sum(r.keyword_match_rate for r in results) / total
    avg_product = sum(r.product_match_rate for r in results) / total

    print(f"\n📈 Average Scores:")
    print(f"   Retrieval Confidence: {avg_retrieval:.2%}")
    print(f"   Keyword Match Rate:   {avg_keyword:.2%}")
    print(f"   Product Match Rate:   {avg_product:.2%}")

    # By category
    print(f"\n📁 By Category:")
    categories = {}
    for r in results:
        if r.category not in categories:
            categories[r.category] = {"total": 0, "passed": 0, "retrieval": [], "keyword": []}
        categories[r.category]["total"] += 1
        categories[r.category]["passed"] += 1 if r.passed else 0
        categories[r.category]["retrieval"].append(r.retrieval_confidence)
        categories[r.category]["keyword"].append(r.keyword_match_rate)

    for cat, data in sorted(categories.items()):
        pass_rate = data["passed"] / data["total"]
        avg_ret = sum(data["retrieval"]) / len(data["retrieval"])
        avg_kw = sum(data["keyword"]) / len(data["keyword"])
        status = "✅" if pass_rate >= 0.7 else "⚠️" if pass_rate >= 0.5 else "❌"
        print(f"   {status} {cat}: {data['passed']}/{data['total']} ({pass_rate:.0%}) | Ret: {avg_ret:.2f} | KW: {avg_kw:.0%}")

    # By difficulty
    print(f"\n📊 By Difficulty:")
    difficulties = {}
    for r in results:
        if r.difficulty not in difficulties:
            difficulties[r.difficulty] = {"total": 0, "passed": 0}
        difficulties[r.difficulty]["total"] += 1
        difficulties[r.difficulty]["passed"] += 1 if r.passed else 0

    for diff in ["easy", "medium", "hard"]:
        if diff in difficulties:
            data = difficulties[diff]
            rate = data["passed"] / data["total"]
            print(f"   {diff.capitalize()}: {data['passed']}/{data['total']} ({rate:.0%})")

    # Failed tests details
    failed_results = [r for r in results if not r.passed]
    if failed_results:
        print(f"\n❌ Failed Tests ({len(failed_results)}):")
        for r in failed_results:
            print(f"   [{r.question_id}] {r.question[:40]}...")
            print(f"       Retrieval: {r.retrieval_confidence:.2f} | Keywords: {r.keyword_match_rate:.0%}")
            print(f"       Notes: {r.notes[:60]}")

    # Save detailed report
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total, 3),
            "avg_retrieval_confidence": round(avg_retrieval, 3),
            "avg_keyword_match_rate": round(avg_keyword, 3),
            "avg_product_match_rate": round(avg_product, 3)
        },
        "by_category": {
            cat: {
                "total": data["total"],
                "passed": data["passed"],
                "pass_rate": round(data["passed"] / data["total"], 3),
                "avg_retrieval": round(sum(data["retrieval"]) / len(data["retrieval"]), 3),
                "avg_keyword": round(sum(data["keyword"]) / len(data["keyword"]), 3)
            }
            for cat, data in categories.items()
        },
        "by_difficulty": {
            diff: {
                "total": data["total"],
                "passed": data["passed"],
                "pass_rate": round(data["passed"] / data["total"], 3)
            }
            for diff, data in difficulties.items()
        },
        "results": [asdict(r) for r in results]
    }

    report_path = Path("data/processed/validation_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Detailed report saved to: {report_path}")

    # Final confidence rating
    print("\n" + "=" * 70)
    confidence_score = (avg_retrieval * 0.4 + avg_keyword * 0.4 + (passed/total) * 0.2)

    if confidence_score >= 0.8:
        grade = "A - Excellent"
    elif confidence_score >= 0.7:
        grade = "B - Good"
    elif confidence_score >= 0.6:
        grade = "C - Acceptable"
    elif confidence_score >= 0.5:
        grade = "D - Needs Improvement"
    else:
        grade = "F - Poor"

    print(f"🎯 OVERALL CONFIDENCE SCORE: {confidence_score:.1%}")
    print(f"📊 GRADE: {grade}")
    print("=" * 70)

    return report


def main():
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)

    print(f"Working directory: {os.getcwd()}")

    # Run async validation
    report = asyncio.run(run_validation())

    return report


if __name__ == "__main__":
    main()
