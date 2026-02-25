#!/usr/bin/env python3
"""
Run LLM-as-a-Judge Evaluation on RAG Test Cases
Evaluates RAG responses using Claude Opus 4.5 as judge
"""

import argparse
import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.llm_judge import LLMJudge
from app.evaluation.rag_eval import GoldenQACase, CaseOutput, load_golden_cases
from app.services.rag_service import RAGService
from app.config import settings
import structlog

logger = structlog.get_logger()


async def run_query_through_rag(
    rag_service: RAGService,
    question: str
) -> CaseOutput:
    """
    Run a question through the RAG pipeline

    Args:
        rag_service: RAG service instance
        question: Question to answer

    Returns:
        CaseOutput with answer and retrieved chunks
    """
    try:
        result = await rag_service.query(
            query=question,
            top_k=5,
            include_metadata=True
        )

        return CaseOutput(
            answer=result.get("answer", ""),
            retrieved_chunks=result.get("chunks", []),
            confidence=result.get("confidence", 0.0),
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error("RAG query failed", question=question[:50], error=str(e))
        return CaseOutput(
            answer=f"Error: {str(e)}",
            retrieved_chunks=[],
            confidence=0.0,
            metadata={"error": str(e)}
        )


async def evaluate_dataset(
    args: argparse.Namespace
) -> Dict[str, Any]:
    """
    Evaluate full dataset with LLM judge

    Args:
        args: Command-line arguments

    Returns:
        Evaluation results and statistics
    """
    # Initialize services
    logger.info("Initializing services")
    rag_service = RAGService()
    judge = LLMJudge(
        model=args.judge_model,
        cache_enabled=args.cache_enabled
    )

    # Load dataset
    logger.info("Loading dataset", path=args.dataset)
    cases = load_golden_cases(args.dataset)

    # Limit cases if specified
    if args.max_cases > 0 and len(cases) > args.max_cases:
        cases = cases[:args.max_cases]
        logger.info(f"Limited to {args.max_cases} cases")

    total_cases = len(cases)
    logger.info(f"Loaded {total_cases} test cases")

    # Process cases in batches
    evaluations = []
    successful = 0
    failed = 0

    for i, case in enumerate(cases, 1):
        logger.info(
            f"Processing case {i}/{total_cases}",
            case_id=case.id,
            question=case.question[:60]
        )

        try:
            # Run query through RAG
            if not args.skip_rag:
                output = await run_query_through_rag(rag_service, case.question)
            else:
                # Use mock output for testing judge only
                output = CaseOutput(
                    answer="Mock answer for testing",
                    retrieved_chunks=[
                        {"text": "Mock chunk 1", "doc_id": "mock", "score": 0.9},
                        {"text": "Mock chunk 2", "doc_id": "mock", "score": 0.8}
                    ],
                    confidence=0.85,
                    metadata={}
                )

            # Evaluate with judge
            eval_result = await judge.evaluate_full_case(case, output)
            evaluations.append(eval_result)
            successful += 1

            # Print summary
            context_rel = eval_result.get("context_relevance", {}).get("average_relevance", 0)
            groundedness = eval_result.get("groundedness", {}).get("groundedness_score", 0)
            answer_rel = eval_result.get("answer_relevance", {}).get("relevance_score", 0)

            print(f"  ✓ Case {i}: CR={context_rel:.2f} | GR={groundedness:.2f} | AR={answer_rel:.1f}/10")

        except Exception as e:
            logger.error(
                "Case evaluation failed",
                case_id=case.id,
                error=str(e)
            )
            failed += 1
            print(f"  ✗ Case {i}: Failed - {str(e)[:50]}")

        # Add delay to respect rate limits
        if i < total_cases and not args.skip_rag:
            await asyncio.sleep(args.delay)

    # Aggregate statistics
    stats = aggregate_results(evaluations)
    stats["total_cases"] = total_cases
    stats["successful_evaluations"] = successful
    stats["failed_evaluations"] = failed
    stats["success_rate"] = round(successful / total_cases, 3) if total_cases > 0 else 0

    # Save report
    save_report(args.report, evaluations, stats)

    return stats


def aggregate_results(evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate evaluation results

    Args:
        evaluations: List of evaluation results

    Returns:
        Aggregated statistics
    """
    if not evaluations:
        return {}

    # Collect scores
    context_relevance_scores = []
    groundedness_scores = []
    answer_relevance_scores = []
    overall_scores = []

    for eval_result in evaluations:
        # Context relevance
        cr = eval_result.get("context_relevance", {})
        if "average_relevance" in cr:
            context_relevance_scores.append(cr["average_relevance"])

        # Groundedness
        gr = eval_result.get("groundedness", {})
        if "groundedness_score" in gr:
            groundedness_scores.append(gr["groundedness_score"])

        # Answer relevance
        ar = eval_result.get("answer_relevance", {})
        if "relevance_score" in ar:
            answer_relevance_scores.append(ar["relevance_score"] / 10.0)  # Normalize to 0-1

        # Overall quality
        oq = eval_result.get("overall_quality", {})
        if "overall_score" in oq:
            overall_scores.append(oq["overall_score"] / 10.0)  # Normalize to 0-1

    # Calculate averages
    stats = {
        "context_relevance": {
            "avg": round(sum(context_relevance_scores) / len(context_relevance_scores), 3)
            if context_relevance_scores else 0,
            "count": len(context_relevance_scores)
        },
        "groundedness": {
            "avg": round(sum(groundedness_scores) / len(groundedness_scores), 3)
            if groundedness_scores else 0,
            "count": len(groundedness_scores)
        },
        "answer_relevance": {
            "avg": round(sum(answer_relevance_scores) / len(answer_relevance_scores), 3)
            if answer_relevance_scores else 0,
            "count": len(answer_relevance_scores)
        },
        "overall_quality": {
            "avg": round(sum(overall_scores) / len(overall_scores), 3)
            if overall_scores else 0,
            "count": len(overall_scores)
        }
    }

    # Calculate combined RAG Triad score
    if context_relevance_scores and groundedness_scores and answer_relevance_scores:
        triad_combined = (
            sum(context_relevance_scores) / len(context_relevance_scores) +
            sum(groundedness_scores) / len(groundedness_scores) +
            sum(answer_relevance_scores) / len(answer_relevance_scores)
        ) / 3
        stats["rag_triad_combined"] = round(triad_combined, 3)

    return stats


def save_report(
    report_path: str,
    evaluations: List[Dict[str, Any]],
    stats: Dict[str, Any]
) -> None:
    """
    Save evaluation report to JSON

    Args:
        report_path: Output file path
        evaluations: Individual evaluation results
        stats: Aggregated statistics
    """
    report = {
        "version": "llm-judge-v1.0",
        "generated_at": datetime.utcnow().isoformat(),
        "statistics": stats,
        "evaluations": evaluations
    }

    output_file = Path(report_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("Report saved", path=report_path)


def print_summary(stats: Dict[str, Any]) -> None:
    """
    Print summary of evaluation results

    Args:
        stats: Aggregated statistics
    """
    print("\n" + "=" * 70)
    print("LLM JUDGE EVALUATION COMPLETE")
    print("=" * 70)

    print(f"\n📊 Overall Statistics:")
    print(f"  Total cases: {stats.get('total_cases', 0)}")
    print(f"  Successful: {stats.get('successful_evaluations', 0)}")
    print(f"  Failed: {stats.get('failed_evaluations', 0)}")
    print(f"  Success rate: {stats.get('success_rate', 0):.1%}")

    print(f"\n📈 RAG Triad Metrics:")
    cr = stats.get("context_relevance", {})
    print(f"  Context Relevance: {cr.get('avg', 0):.3f} (avg relevance 0-10)")

    gr = stats.get("groundedness", {})
    print(f"  Groundedness: {gr.get('avg', 0):.3f} (claim support 0-1)")

    ar = stats.get("answer_relevance", {})
    print(f"  Answer Relevance: {ar.get('avg', 0):.3f} (normalized 0-1)")

    if "rag_triad_combined" in stats:
        print(f"  Combined Triad Score: {stats['rag_triad_combined']:.3f}")

    print(f"\n⭐ Overall Quality:")
    oq = stats.get("overall_quality", {})
    print(f"  Average: {oq.get('avg', 0):.3f} (normalized 0-1)")

    # Interpretation
    triad_combined = stats.get("rag_triad_combined", 0)
    if triad_combined >= 0.8:
        status = "🟢 Excellent"
    elif triad_combined >= 0.6:
        status = "🟡 Good"
    elif triad_combined >= 0.4:
        status = "🟠 Fair"
    else:
        status = "🔴 Needs Improvement"

    print(f"\n🎯 System Performance: {status}")
    print(f"   Triad score: {triad_combined:.3f}")

    print("\n" + "=" * 70)


def parse_args(argv: List[str]) -> argparse.Namespace:
    """
    Parse command-line arguments

    Args:
        argv: Command-line arguments

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Run LLM-as-a-Judge evaluation on RAG test cases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate golden dataset
  python scripts/run_llm_judge_eval.py \\
    --dataset tests/fixtures/rag_eval_dataset.json \\
    --report data/llm_judge_report.json

  # Evaluate synthetic dataset (sample)
  python scripts/run_llm_judge_eval.py \\
    --dataset data/synthetic_dataset_v1.json \\
    --max-cases 100 \\
    --report data/llm_judge_synthetic_sample.json

  # Test judge without running RAG queries
  python scripts/run_llm_judge_eval.py \\
    --dataset tests/fixtures/rag_eval_dataset.json \\
    --skip-rag \\
    --max-cases 5 \\
    --report data/judge_test.json
        """
    )

    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to test dataset JSON (golden or synthetic)"
    )

    parser.add_argument(
        "--report",
        required=True,
        help="Output path for evaluation report JSON"
    )

    parser.add_argument(
        "--judge-model",
        default="claude-opus-4-5-20251101",
        help="Claude model to use for judging (default: opus-4-5)"
    )

    parser.add_argument(
        "--max-cases",
        type=int,
        default=0,
        help="Limit number of cases to evaluate (0=all, default: 0)"
    )

    parser.add_argument(
        "--skip-rag",
        action="store_true",
        help="Skip RAG queries, test judge with mock data"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between cases in seconds (default: 2.0)"
    )

    parser.add_argument(
        "--no-cache",
        dest="cache_enabled",
        action="store_false",
        default=True,
        help="Disable evaluation caching"
    )

    return parser.parse_args(argv)


async def main(args: argparse.Namespace) -> int:
    """
    Main function

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0=success, 1=failure)
    """
    try:
        logger.info(
            "Starting LLM judge evaluation",
            dataset=args.dataset,
            judge_model=args.judge_model,
            max_cases=args.max_cases,
            skip_rag=args.skip_rag
        )

        # Run evaluation
        stats = await evaluate_dataset(args)

        # Print summary
        print_summary(stats)

        # Check success criteria
        success_rate = stats.get("success_rate", 0)
        if success_rate < 0.90:
            print(f"\n⚠️  Warning: Success rate below 90% ({success_rate:.1%})")

        triad_combined = stats.get("rag_triad_combined", 0)
        if triad_combined < 0.60:
            print(f"\n⚠️  Warning: Combined triad score below 0.60 ({triad_combined:.3f})")

        print(f"\n✅ Evaluation completed successfully")
        print(f"📄 Report saved: {args.report}")

        return 0

    except Exception as e:
        logger.error("LLM judge evaluation failed", error=str(e))
        print(f"\n❌ Error: {str(e)}")
        return 1


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    exit_code = asyncio.run(main(args))
    sys.exit(exit_code)
