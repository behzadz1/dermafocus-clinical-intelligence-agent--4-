#!/usr/bin/env python3
"""
Test Feedback System
Tests feedback submission, storage, and reporting
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.feedback import FeedbackRecord, FeedbackRating, FeedbackCategory


def create_test_feedback_data():
    """Create sample feedback data for testing"""
    feedback_dir = Path(__file__).parent.parent / "data" / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)

    # Create sample feedback records
    sample_feedback = [
        {
            "id": f"fb_{uuid.uuid4().hex[:12]}",
            "conversation_id": "conv_test_001",
            "message_id": "msg_001",
            "rating": FeedbackRating.POSITIVE.value,
            "category": None,
            "comment": "Excellent detailed answer about Newest protocol!",
            "query": "What is the Newest treatment protocol?",
            "response": "The Newest protocol involves 4 sessions spaced 3 weeks apart...",
            "confidence": 0.95,
            "sources": ["Newest_Factsheet", "Clinical_Protocol_Newest"],
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "id": f"fb_{uuid.uuid4().hex[:12]}",
            "conversation_id": "conv_test_002",
            "message_id": "msg_002",
            "rating": FeedbackRating.NEGATIVE.value,
            "category": FeedbackCategory.INCOMPLETE_ANSWER.value,
            "comment": "Missing dosing information for Plinest Eye",
            "query": "What is the dosing for Plinest Eye?",
            "response": "Plinest Eye is used for periocular rejuvenation...",
            "confidence": 0.78,
            "sources": ["Plinest_Eye_Factsheet"],
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "id": f"fb_{uuid.uuid4().hex[:12]}",
            "conversation_id": "conv_test_003",
            "message_id": "msg_003",
            "rating": FeedbackRating.NEGATIVE.value,
            "category": FeedbackCategory.INCORRECT_INFORMATION.value,
            "comment": "The contraindications listed are incomplete",
            "query": "What are the contraindications for Newest?",
            "response": "Contraindications include active infections...",
            "confidence": 0.92,
            "sources": ["Newest_Factsheet"],
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "id": f"fb_{uuid.uuid4().hex[:12]}",
            "conversation_id": "conv_test_004",
            "message_id": "msg_004",
            "rating": FeedbackRating.POSITIVE.value,
            "category": None,
            "comment": "Very helpful comparison!",
            "query": "Compare Newest and Plinest",
            "response": "Newest and Plinest both contain polynucleotides...",
            "confidence": 0.89,
            "sources": ["Newest_Factsheet", "Plinest_Factsheet"],
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "id": f"fb_{uuid.uuid4().hex[:12]}",
            "conversation_id": "conv_test_005",
            "message_id": "msg_005",
            "rating": FeedbackRating.NEGATIVE.value,
            "category": FeedbackCategory.POOR_SOURCES.value,
            "comment": "Sources don't seem relevant to my question",
            "query": "What is the difference in technique?",
            "response": "The injection technique varies by product...",
            "confidence": 0.65,
            "sources": ["Generic_Brochure"],
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "id": f"fb_{uuid.uuid4().hex[:12]}",
            "conversation_id": "conv_test_006",
            "message_id": "msg_006",
            "rating": FeedbackRating.POSITIVE.value,
            "category": None,
            "comment": None,
            "query": "What products treat fine lines?",
            "response": "Several products treat fine lines including Newest, Plinest...",
            "confidence": 0.91,
            "sources": ["Product_Overview"],
            "timestamp": datetime.utcnow().isoformat()
        }
    ]

    # Write to today's feedback file
    date = datetime.utcnow()
    filename = f"feedback_{date.strftime('%Y%m%d')}.jsonl"
    feedback_file = feedback_dir / filename

    with open(feedback_file, "w", encoding="utf-8") as f:
        for record in sample_feedback:
            f.write(json.dumps(record) + "\n")

    print(f"✓ Created {len(sample_feedback)} test feedback records")
    print(f"  File: {feedback_file}")

    return len(sample_feedback)


def test_feedback_loading():
    """Test that feedback can be loaded"""
    print("\n" + "=" * 80)
    print("TEST: Feedback Loading")
    print("=" * 80)

    from scripts.generate_feedback_report import load_feedback

    feedback = load_feedback(days=1)
    print(f"✓ Loaded {len(feedback)} feedback records")

    if feedback:
        print("\nSample record:")
        sample = feedback[0]
        print(f"  ID: {sample.id}")
        print(f"  Rating: {sample.rating.value}")
        print(f"  Query: {sample.query}")
        print(f"  Confidence: {sample.confidence}")

    return len(feedback) > 0


def test_report_generation():
    """Test report generation"""
    print("\n" + "=" * 80)
    print("TEST: Report Generation")
    print("=" * 80)

    from scripts.generate_feedback_report import load_feedback, generate_report, print_report

    feedback = load_feedback(days=1)
    if not feedback:
        print("⚠ No feedback to generate report from")
        return False

    report = generate_report(feedback, days=1)
    print_report(report)

    return True


def test_feedback_stats_api():
    """Test feedback stats API (manual check)"""
    print("\n" + "=" * 80)
    print("TEST: Feedback API Endpoints")
    print("=" * 80)

    print("\nTo test the API endpoints, run:")
    print("  1. Start the backend: cd backend && uvicorn app.main:app --reload")
    print("  2. Visit: http://localhost:8000/api/feedback/stats")
    print("  3. Visit: http://localhost:8000/api/feedback/recent")
    print("\nOr use curl:")
    print("  curl http://localhost:8000/api/feedback/stats?days=7")
    print("  curl http://localhost:8000/api/feedback/recent?limit=10")


def main():
    """Run all feedback system tests"""
    print("=" * 80)
    print("FEEDBACK SYSTEM TEST SUITE")
    print("=" * 80)

    # Test 1: Create test data
    print("\nTest 1: Creating test feedback data...")
    try:
        count = create_test_feedback_data()
        test1_pass = count > 0
    except Exception as e:
        print(f"✗ Failed: {e}")
        test1_pass = False

    # Test 2: Load feedback
    print("\nTest 2: Loading feedback data...")
    try:
        test2_pass = test_feedback_loading()
    except Exception as e:
        print(f"✗ Failed: {e}")
        test2_pass = False

    # Test 3: Generate report
    print("\nTest 3: Generating quality report...")
    try:
        test3_pass = test_report_generation()
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        test3_pass = False

    # Test 4: API endpoints info
    test_feedback_stats_api()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Test data creation: {'✓ PASS' if test1_pass else '✗ FAIL'}")
    print(f"Feedback loading: {'✓ PASS' if test2_pass else '✗ FAIL'}")
    print(f"Report generation: {'✓ PASS' if test3_pass else '✗ FAIL'}")

    if test1_pass and test2_pass and test3_pass:
        print("\n✅ All tests passed!")
        print("\n💡 Next steps:")
        print("  1. Start the backend to test API endpoints")
        print("  2. Submit real feedback via POST /api/feedback/submit")
        print("  3. View stats via GET /api/feedback/stats")
        print("  4. Generate reports with: python scripts/generate_feedback_report.py")
        return 0
    else:
        print("\n❌ Some tests failed")
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
