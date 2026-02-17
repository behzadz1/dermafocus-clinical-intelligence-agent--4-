#!/usr/bin/env python3
"""
Quality Report Generator
Generates detailed quality reports for RAG system performance
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.quality_metrics import get_quality_metrics_collector


def print_section_header(title: str):
    """Print formatted section header"""
    print(f"\n{'=' * 70}")
    print(f"{title}")
    print(f"{'=' * 70}\n")


def print_subsection(title: str):
    """Print formatted subsection header"""
    print(f"\n{title}")
    print(f"{'-' * 70}")


def daily_report(date: datetime = None):
    """Generate daily quality report"""
    if date is None:
        date = datetime.utcnow()

    collector = get_quality_metrics_collector()
    metrics = collector.get_daily_metrics(date)

    print_section_header(f"Daily Quality Report - {metrics['start_date']}")

    # Overview
    print("📊 OVERVIEW")
    print(f"   Total Queries:       {metrics['total_queries']:>10,}")
    print(f"   Refusals:            {metrics['total_refusals']:>10,} ({metrics['refusal_rate']:.1%})")
    print(f"   High Confidence:     {metrics['high_confidence_queries']:>10,}")
    print(f"   Low Confidence:      {metrics['low_confidence_queries']:>10,}")

    # Confidence
    print_subsection("🎯 CONFIDENCE METRICS")
    print(f"   Average Confidence:  {metrics['avg_confidence']:>10.1%}")
    print(f"\n   Distribution:")
    for range_label, count in metrics['confidence_distribution'].items():
        pct = (count / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0
        bar = '█' * int(pct / 2)
        print(f"     {range_label:>7}%:  {count:>5} │ {bar} {pct:.1f}%")

    # Retrieval
    print_subsection("🔍 RETRIEVAL METRICS")
    print(f"   Avg Top Score:       {metrics['avg_top_retrieval_score']:>10.3f}")
    print(f"   Avg Chunks:          {metrics['avg_chunks_retrieved']:>10.1f}")
    print(f"   Avg Strong Matches:  {metrics['avg_strong_matches']:>10.1f}")
    print(f"   Evidence Rate:       {metrics['evidence_sufficient_rate']:>10.1%}")
    print(f"   Reranking Usage:     {metrics['reranking_usage_rate']:>10.1%}")

    # Intent Distribution
    if metrics['intent_distribution']:
        print_subsection("🎭 QUERY INTENTS")
        for intent, count in sorted(metrics['intent_distribution'].items(), key=lambda x: x[1], reverse=True):
            pct = (count / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0
            print(f"   {intent:>20}:  {count:>5} ({pct:.1f}%)")

    # Query Expansion
    if metrics['query_expansion_distribution']:
        print_subsection("🔄 QUERY EXPANSION")
        for expansion, count in metrics['query_expansion_distribution'].items():
            pct = (count / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0
            print(f"   {expansion:>20}:  {count:>5} ({pct:.1f}%)")

    print("\n" + "=" * 70 + "\n")


def weekly_report():
    """Generate weekly quality report"""
    collector = get_quality_metrics_collector()
    metrics = collector.get_weekly_metrics()

    print_section_header(f"Weekly Quality Report ({metrics['start_date']} to {metrics['end_date']})")

    # Overview
    print("📊 OVERVIEW")
    print(f"   Total Queries:       {metrics['total_queries']:>10,}")
    print(f"   Refusals:            {metrics['total_refusals']:>10,} ({metrics['refusal_rate']:.1%})")
    print(f"   High Confidence:     {metrics['high_confidence_queries']:>10,} ({metrics['high_confidence_queries']/max(metrics['total_queries'],1)*100:.1f}%)")
    print(f"   Low Confidence:      {metrics['low_confidence_queries']:>10,} ({metrics['low_confidence_queries']/max(metrics['total_queries'],1)*100:.1f}%)")

    # Quality Metrics
    print_subsection("🎯 QUALITY METRICS")
    print(f"   Average Confidence:       {metrics['avg_confidence']:>10.1%}")
    print(f"   Avg Top Retrieval Score:  {metrics['avg_top_retrieval_score']:>10.3f}")
    print(f"   Avg Chunks Retrieved:     {metrics['avg_chunks_retrieved']:>10.1f}")
    print(f"   Avg Strong Matches:       {metrics['avg_strong_matches']:>10.1f}")
    print(f"   Evidence Sufficient Rate: {metrics['evidence_sufficient_rate']:>10.1%}")
    print(f"   Reranking Usage Rate:     {metrics['reranking_usage_rate']:>10.1%}")

    # Confidence Distribution
    print_subsection("📈 CONFIDENCE DISTRIBUTION")
    for range_label, count in metrics['confidence_distribution'].items():
        pct = (count / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0
        bar = '█' * int(pct / 2)
        print(f"   {range_label:>7}%:  {count:>5} │ {bar} {pct:.1f}%")

    # Daily Trends
    print_subsection("📅 DAILY TRENDS")
    trends = collector.get_quality_trends(days=7)
    print(f"   {'Date':>12}  {'Queries':>8}  {'Avg Conf':>9}  {'Refusals':>9}  {'Evidence':>9}")
    for trend in trends:
        print(
            f"   {trend['date']:>12}  "
            f"{trend['total_queries']:>8}  "
            f"{trend['avg_confidence']:>9.1%}  "
            f"{trend['refusal_rate']:>9.1%}  "
            f"{trend['evidence_sufficient_rate']:>9.1%}"
        )

    # Top Intents
    if metrics['intent_distribution']:
        print_subsection("🎭 TOP QUERY INTENTS")
        for intent, count in sorted(metrics['intent_distribution'].items(), key=lambda x: x[1], reverse=True)[:10]:
            pct = (count / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0
            print(f"   {intent:>25}:  {count:>5} ({pct:.1f}%)")

    # Low Quality Queries
    print_subsection("⚠️  LOW QUALITY QUERIES (Confidence < 60%)")
    low_quality = collector.identify_low_quality_queries(confidence_threshold=0.6, days=7)
    if low_quality:
        print(f"   Found {len(low_quality)} low-quality queries requiring review:\n")
        for i, query in enumerate(low_quality[:10], 1):
            print(f"   {i}. [{query['timestamp'][:10]}] Confidence: {query['confidence']:.1%}")
            print(f"      Query: {query['query_preview']}")
            print(f"      Intent: {query['intent']} | Strong Matches: {query['num_strong_matches']}")
            if query.get('evidence_reason'):
                print(f"      Reason: {query['evidence_reason']}")
            print()
    else:
        print("   ✅ No low-quality queries found!")

    print("\n" + "=" * 70 + "\n")


def monthly_report():
    """Generate monthly quality report"""
    collector = get_quality_metrics_collector()
    metrics = collector.get_monthly_metrics()

    print_section_header(f"Monthly Quality Report ({metrics['start_date']} to {metrics['end_date']})")

    # Overview
    print("📊 OVERVIEW (Last 30 Days)")
    print(f"   Total Queries:       {metrics['total_queries']:>10,}")
    print(f"   Refusals:            {metrics['total_refusals']:>10,} ({metrics['refusal_rate']:.1%})")
    print(f"   High Confidence:     {metrics['high_confidence_queries']:>10,}")
    print(f"   Low Confidence:      {metrics['low_confidence_queries']:>10,}")

    # Quality Summary
    print_subsection("🎯 QUALITY SUMMARY")
    print(f"   Average Confidence:       {metrics['avg_confidence']:>10.1%}")
    print(f"   Avg Top Retrieval Score:  {metrics['avg_top_retrieval_score']:>10.3f}")
    print(f"   Avg Chunks Retrieved:     {metrics['avg_chunks_retrieved']:>10.1f}")
    print(f"   Avg Strong Matches:       {metrics['avg_strong_matches']:>10.1f}")
    print(f"   Evidence Sufficient Rate: {metrics['evidence_sufficient_rate']:>10.1%}")
    print(f"   Reranking Usage Rate:     {metrics['reranking_usage_rate']:>10.1%}")

    # Confidence Distribution
    print_subsection("📈 CONFIDENCE DISTRIBUTION")
    for range_label, count in metrics['confidence_distribution'].items():
        pct = (count / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0
        bar = '█' * int(pct / 2)
        print(f"   {range_label:>7}%:  {count:>5} │ {bar} {pct:.1f}%")

    # Intent Distribution
    if metrics['intent_distribution']:
        print_subsection("🎭 INTENT DISTRIBUTION")
        for intent, count in sorted(metrics['intent_distribution'].items(), key=lambda x: x[1], reverse=True):
            pct = (count / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0
            print(f"   {intent:>25}:  {count:>5} ({pct:.1f}%)")

    # System Performance
    print_subsection("⚙️  SYSTEM PERFORMANCE")
    print(f"   Query Expansion Usage:")
    for expansion, count in metrics['query_expansion_distribution'].items():
        pct = (count / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0
        print(f"     {expansion:>20}:  {count:>5} ({pct:.1f}%)")

    print(f"\n   Hierarchy Matching:")
    for hierarchy, count in metrics['hierarchy_match_distribution'].items():
        pct = (count / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0
        print(f"     {hierarchy:>20}:  {count:>5} ({pct:.1f}%)")

    print("\n" + "=" * 70 + "\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate quality reports for RAG system"
    )
    parser.add_argument(
        "period",
        choices=["daily", "weekly", "monthly"],
        help="Report period"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Specific date for daily report (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    if args.period == "daily":
        if args.date:
            try:
                date = datetime.strptime(args.date, "%Y-%m-%d")
                daily_report(date)
            except ValueError:
                print("Error: Invalid date format. Use YYYY-MM-DD")
                sys.exit(1)
        else:
            daily_report()

    elif args.period == "weekly":
        weekly_report()

    elif args.period == "monthly":
        monthly_report()


if __name__ == "__main__":
    main()
