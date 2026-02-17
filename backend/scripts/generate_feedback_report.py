#!/usr/bin/env python3
"""
Feedback Report Generator
Analyzes user feedback and generates quality reports
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import List, Dict

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.feedback import FeedbackRecord, FeedbackRating, FeedbackCategory


def load_feedback(days: int = 7) -> List[FeedbackRecord]:
    """Load feedback from the last N days"""
    feedback_dir = Path(__file__).parent.parent / "data" / "feedback"

    if not feedback_dir.exists():
        print(f"⚠ Feedback directory not found: {feedback_dir}")
        return []

    all_feedback = []
    for i in range(days):
        date = datetime.utcnow() - timedelta(days=i)
        filename = f"feedback_{date.strftime('%Y%m%d')}.jsonl"
        feedback_file = feedback_dir / filename

        if feedback_file.exists():
            with open(feedback_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            record = FeedbackRecord.model_validate_json(line)
                            all_feedback.append(record)
                        except Exception as e:
                            print(f"Warning: Failed to parse feedback line: {e}")

    return all_feedback


def generate_report(feedback_list: List[FeedbackRecord], days: int = 7) -> Dict:
    """Generate comprehensive quality report"""

    if not feedback_list:
        return {
            "summary": "No feedback data available",
            "total_feedback": 0
        }

    # Basic statistics
    total = len(feedback_list)
    positive = sum(1 for f in feedback_list if f.rating == FeedbackRating.POSITIVE)
    negative = sum(1 for f in feedback_list if f.rating == FeedbackRating.NEGATIVE)
    neutral = sum(1 for f in feedback_list if f.rating == FeedbackRating.NEUTRAL)

    positive_rate = (positive / total * 100) if total > 0 else 0
    negative_rate = (negative / total * 100) if total > 0 else 0

    # Category breakdown (negative feedback)
    category_counts = Counter()
    for f in feedback_list:
        if f.rating == FeedbackRating.NEGATIVE and f.category:
            category_counts[f.category.value] += 1

    # Confidence analysis
    confidences = [f.confidence for f in feedback_list if f.confidence is not None]
    avg_confidence = sum(confidences) / len(confidences) if confidences else None

    # Low confidence negative feedback (potential issues)
    low_confidence_negative = [
        f for f in feedback_list
        if f.rating == FeedbackRating.NEGATIVE and f.confidence and f.confidence < 0.7
    ]

    # High confidence negative feedback (concerning)
    high_confidence_negative = [
        f for f in feedback_list
        if f.rating == FeedbackRating.NEGATIVE and f.confidence and f.confidence >= 0.9
    ]

    # Query analysis - most complained about
    negative_queries = defaultdict(list)
    for f in feedback_list:
        if f.rating == FeedbackRating.NEGATIVE and f.query:
            negative_queries[f.query].append(f)

    top_problematic_queries = sorted(
        negative_queries.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:10]

    # Trending issues (last 3 days vs previous days)
    cutoff_date = datetime.utcnow() - timedelta(days=3)
    recent_feedback = [f for f in feedback_list if f.timestamp >= cutoff_date]
    older_feedback = [f for f in feedback_list if f.timestamp < cutoff_date]

    recent_negative_rate = (
        sum(1 for f in recent_feedback if f.rating == FeedbackRating.NEGATIVE) /
        len(recent_feedback) * 100
    ) if recent_feedback else 0

    older_negative_rate = (
        sum(1 for f in older_feedback if f.rating == FeedbackRating.NEGATIVE) /
        len(older_feedback) * 100
    ) if older_feedback else 0

    # Build report
    report = {
        "report_generated": datetime.utcnow().isoformat(),
        "period_days": days,
        "summary": {
            "total_feedback": total,
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "positive_rate": round(positive_rate, 2),
            "negative_rate": round(negative_rate, 2),
            "avg_confidence": round(avg_confidence, 3) if avg_confidence else None
        },
        "category_breakdown": dict(category_counts),
        "confidence_analysis": {
            "low_confidence_negative_count": len(low_confidence_negative),
            "high_confidence_negative_count": len(high_confidence_negative)
        },
        "trending": {
            "recent_negative_rate": round(recent_negative_rate, 2),
            "older_negative_rate": round(older_negative_rate, 2),
            "trend": "improving" if recent_negative_rate < older_negative_rate else "worsening"
        },
        "top_problematic_queries": [
            {
                "query": query,
                "negative_count": len(feedbacks),
                "categories": list(set(f.category.value for f in feedbacks if f.category)),
                "sample_comments": [f.comment for f in feedbacks if f.comment][:3]
            }
            for query, feedbacks in top_problematic_queries
        ],
        "action_items": []
    }

    # Generate action items
    if negative_rate > 20:
        report["action_items"].append({
            "priority": "high",
            "issue": "High negative feedback rate",
            "action": f"Investigate why {negative_rate:.1f}% of feedback is negative"
        })

    if high_confidence_negative:
        report["action_items"].append({
            "priority": "high",
            "issue": f"{len(high_confidence_negative)} responses with high confidence but negative feedback",
            "action": "Review these responses - may indicate incorrect information"
        })

    if category_counts.get("incorrect_information", 0) > 5:
        report["action_items"].append({
            "priority": "high",
            "issue": f"{category_counts['incorrect_information']} reports of incorrect information",
            "action": "Audit knowledge base for accuracy"
        })

    if category_counts.get("incomplete_answer", 0) > 10:
        report["action_items"].append({
            "priority": "medium",
            "issue": f"{category_counts['incomplete_answer']} reports of incomplete answers",
            "action": "Review chunking strategy and context assembly"
        })

    if recent_negative_rate > older_negative_rate * 1.5:
        report["action_items"].append({
            "priority": "high",
            "issue": "Negative feedback rate increasing",
            "action": "Investigate recent changes or document updates"
        })

    # Add sample problematic feedback for manual review
    report["flagged_for_review"] = [
        {
            "feedback_id": f.id,
            "query": f.query,
            "response_preview": f.response[:200] + "..." if len(f.response) > 200 else f.response,
            "confidence": f.confidence,
            "category": f.category.value if f.category else None,
            "comment": f.comment
        }
        for f in high_confidence_negative[:5]
    ]

    return report


def print_report(report: Dict):
    """Print formatted report to console"""
    print("=" * 80)
    print("USER FEEDBACK QUALITY REPORT")
    print("=" * 80)
    print(f"Generated: {report['report_generated']}")
    print(f"Period: Last {report['period_days']} days")
    print()

    # Summary
    summary = report["summary"]
    print("📊 SUMMARY")
    print("-" * 80)
    print(f"Total Feedback: {summary['total_feedback']}")
    print(f"  Positive: {summary['positive_count']} ({summary['positive_rate']}%)")
    print(f"  Negative: {summary['negative_count']} ({summary['negative_rate']}%)")
    print(f"  Neutral: {summary['neutral_count']}")
    print(f"Average Confidence: {summary['avg_confidence']}")
    print()

    # Category breakdown
    if report["category_breakdown"]:
        print("📋 NEGATIVE FEEDBACK CATEGORIES")
        print("-" * 80)
        for category, count in sorted(report["category_breakdown"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count}")
        print()

    # Trending
    trending = report["trending"]
    trend_emoji = "📈" if trending["trend"] == "worsening" else "📉"
    print(f"{trend_emoji} TREND")
    print("-" * 80)
    print(f"Recent (last 3 days): {trending['recent_negative_rate']}% negative")
    print(f"Previous period: {trending['older_negative_rate']}% negative")
    print(f"Trend: {trending['trend'].upper()}")
    print()

    # Top problematic queries
    if report["top_problematic_queries"]:
        print("⚠️  TOP PROBLEMATIC QUERIES")
        print("-" * 80)
        for i, item in enumerate(report["top_problematic_queries"][:5], 1):
            print(f"{i}. \"{item['query']}\" - {item['negative_count']} complaints")
            print(f"   Categories: {', '.join(item['categories'])}")
            if item['sample_comments']:
                print(f"   Sample: \"{item['sample_comments'][0][:100]}...\"")
            print()

    # Action items
    if report["action_items"]:
        print("🔴 ACTION ITEMS")
        print("-" * 80)
        for item in report["action_items"]:
            priority_emoji = "🔴" if item["priority"] == "high" else "🟡"
            print(f"{priority_emoji} [{item['priority'].upper()}] {item['issue']}")
            print(f"   → {item['action']}")
            print()

    # Flagged for review
    if report["flagged_for_review"]:
        print("🚩 FLAGGED FOR MANUAL REVIEW")
        print("-" * 80)
        for item in report["flagged_for_review"]:
            print(f"Feedback ID: {item['feedback_id']}")
            print(f"Query: {item['query']}")
            print(f"Confidence: {item['confidence']}")
            print(f"Category: {item['category']}")
            print(f"Comment: {item['comment']}")
            print(f"Response: {item['response_preview']}")
            print()

    print("=" * 80)


def save_report(report: Dict, output_dir: Path = None):
    """Save report to JSON file"""
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "reports"

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"feedback_report_{timestamp}.json"
    output_file = output_dir / filename

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"✓ Report saved to: {output_file}")


def main():
    """Generate and display feedback quality report"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate user feedback quality report")
    parser.add_argument("--days", type=int, default=7, help="Number of days to analyze (default: 7)")
    parser.add_argument("--save", action="store_true", help="Save report to JSON file")
    args = parser.parse_args()

    print(f"Loading feedback from last {args.days} days...")
    feedback_list = load_feedback(days=args.days)

    if not feedback_list:
        print("\n⚠️  No feedback data found")
        print("   Users haven't submitted any feedback yet")
        print("   Feedback will be stored in: backend/data/feedback/")
        return

    print(f"✓ Loaded {len(feedback_list)} feedback records\n")

    # Generate report
    report = generate_report(feedback_list, days=args.days)

    # Print to console
    print_report(report)

    # Save if requested
    if args.save:
        save_report(report)

    print("\n💡 TIP: Run with --save to export report as JSON")


if __name__ == "__main__":
    main()
