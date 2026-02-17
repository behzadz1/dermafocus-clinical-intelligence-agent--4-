#!/usr/bin/env python3
"""
Cost Report Generator
Generates detailed cost reports for API usage
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.cost_tracker import get_cost_tracker


def print_cost_breakdown(costs: dict, title: str):
    """Print formatted cost breakdown"""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}\n")

    # Claude costs
    print("🤖 Claude (claude-3-haiku-20240307)")
    print(f"   Input tokens:  {costs['claude']['input_tokens']:>10,}")
    print(f"   Output tokens: {costs['claude']['output_tokens']:>10,}")
    print(f"   Cost:          ${costs['claude']['cost']:>10.4f}")

    # OpenAI costs
    print(f"\n🔤 OpenAI (text-embedding-3-small)")
    print(f"   Tokens:        {costs['openai']['tokens']:>10,}")
    print(f"   Cost:          ${costs['openai']['cost']:>10.4f}")

    # Pinecone costs
    print(f"\n🌲 Pinecone (Serverless)")
    print(f"   Queries:       {costs['pinecone']['queries']:>10,}")
    print(f"   Cost:          ${costs['pinecone']['cost']:>10.4f}")

    # Total
    print(f"\n{'-' * 60}")
    print(f"💰 TOTAL COST:     ${costs['total']:>10.4f}")
    print(f"{'-' * 60}\n")


def daily_report(date: datetime = None):
    """Generate daily cost report"""
    if date is None:
        date = datetime.utcnow()

    cost_tracker = get_cost_tracker()
    costs = cost_tracker.get_daily_costs(date)

    print_cost_breakdown(
        costs,
        f"Daily Cost Report - {costs['date']}"
    )


def weekly_report():
    """Generate weekly cost report"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    cost_tracker = get_cost_tracker()
    costs = cost_tracker.get_date_range_costs(start_date, end_date)

    print_cost_breakdown(
        costs,
        f"Weekly Cost Report ({costs['start_date']} to {costs['end_date']})"
    )


def monthly_report():
    """Generate monthly cost report"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    cost_tracker = get_cost_tracker()
    costs = cost_tracker.get_date_range_costs(start_date, end_date)

    print_cost_breakdown(
        costs,
        f"Monthly Cost Report ({costs['start_date']} to {costs['end_date']})"
    )


def session_report():
    """Generate session cost report"""
    cost_tracker = get_cost_tracker()
    costs = cost_tracker.get_session_costs()

    print(f"\n{'=' * 60}")
    print("Current Session Costs")
    print(f"{'=' * 60}\n")

    # Claude costs
    print("🤖 Claude")
    print(f"   Input tokens:  {costs['claude']['input_tokens']:>10,}")
    print(f"   Output tokens: {costs['claude']['output_tokens']:>10,}")
    print(f"   Cost:          ${costs['claude']['cost']:>10.4f}")

    # OpenAI costs
    print(f"\n🔤 OpenAI")
    print(f"   Tokens:        {costs['openai']['tokens']:>10,}")
    print(f"   Cost:          ${costs['openai']['cost']:>10.4f}")

    # Pinecone costs
    print(f"\n🌲 Pinecone")
    print(f"   Queries:       {costs['pinecone']['queries']:>10,}")
    print(f"   Cost:          ${costs['pinecone']['cost']:>10.4f}")

    # Total
    print(f"\n{'-' * 60}")
    print(f"💰 SESSION TOTAL:  ${costs['total']:>10.4f}")
    print(f"{'-' * 60}\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate cost reports for API usage"
    )
    parser.add_argument(
        "period",
        choices=["daily", "weekly", "monthly", "session"],
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

    elif args.period == "session":
        session_report()


if __name__ == "__main__":
    main()
