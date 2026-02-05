#!/usr/bin/env python3
"""
Run regression evaluation over the RAG pipeline using a golden QA dataset.
"""

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.rag_eval import (  # noqa: E402
    CaseOutput,
    aggregate_results,
    evaluate_case,
    load_golden_cases,
    save_report,
)


STRICT_REFUSAL_MESSAGE = (
    "I do not have sufficient documented evidence in the current Dermafocus knowledge base "
    "to answer this safely. Please upload or reference the relevant source document."
)


async def run_eval(
    dataset_path: str,
    report_path: str,
    max_cases: int,
    use_llm: bool,
    min_pass_rate: float,
    min_refusal_accuracy: float,
    min_citation_page_valid_rate: float,
) -> int:
    from app.services.claude_service import get_claude_service
    from app.services.rag_service import get_rag_service

    cases = load_golden_cases(dataset_path)
    if max_cases > 0:
        cases = cases[:max_cases]

    rag = get_rag_service()
    claude = get_claude_service() if use_llm else None

    results = []
    for idx, case in enumerate(cases, 1):
        print(f"[{idx}/{len(cases)}] {case.id}: {case.question}")
        context_data = rag.get_context_for_query(
            query=case.question,
            max_chunks=case.max_chunks
        )
        evidence = context_data.get("evidence", {})

        if not evidence.get("sufficient", False):
            answer = STRICT_REFUSAL_MESSAGE
            # Mirror runtime chat behavior: refusals should not carry citations.
            sources = []
            retrieved_chunks = []
        elif use_llm and claude:
            response = await claude.generate_response(
                user_message=case.question,
                context=context_data.get("context_text", "")
            )
            answer = response.get("answer", "")
            sources = context_data.get("sources", [])
            retrieved_chunks = context_data.get("chunks", [])
        else:
            # Retrieval-only mode: keep runs deterministic and cheap.
            top_chunk = context_data.get("chunks", [{}])[0]
            answer = (top_chunk.get("text") or "")[:500]
            sources = context_data.get("sources", [])
            retrieved_chunks = context_data.get("chunks", [])

        output = CaseOutput(
            answer=answer,
            sources=sources,
            retrieved_chunks=retrieved_chunks,
            evidence=evidence,
        )
        keyword_threshold = 0.3 if use_llm else 0.0
        result = evaluate_case(
            case,
            output,
            expected_keyword_threshold=keyword_threshold,
        )
        results.append(result)

    summary = aggregate_results(results)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_path": dataset_path,
        "report_mode": "generation" if use_llm else "retrieval_only",
        "cases_evaluated": len(cases),
    }
    save_report(report_path, results, summary, metadata)

    print("\nSummary")
    print(f"  pass_rate: {summary['pass_rate']}")
    print(f"  refusal_accuracy: {summary['refusal_accuracy']}")
    print(f"  citation_presence_rate: {summary['citation_presence_rate']}")
    print(f"  avg_retrieval_recall_at_k: {summary['avg_retrieval_recall_at_k']}")
    print(f"  report: {report_path}")

    failed_checks = []
    if summary["pass_rate"] < min_pass_rate:
        failed_checks.append(f"pass_rate<{min_pass_rate}")
    if summary["refusal_accuracy"] < min_refusal_accuracy:
        failed_checks.append(f"refusal_accuracy<{min_refusal_accuracy}")
    if summary["citation_page_valid_rate"] < min_citation_page_valid_rate:
        failed_checks.append(f"citation_page_valid_rate<{min_citation_page_valid_rate}")

    if failed_checks:
        print("  gate_status: FAIL")
        print(f"  failed_checks: {', '.join(failed_checks)}")
        return 1

    print("  gate_status: PASS")
    return 0


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RAG evaluation harness")
    parser.add_argument(
        "--dataset",
        default="tests/fixtures/rag_eval_dataset.json",
        help="Path to golden QA dataset JSON (relative to backend/)."
    )
    parser.add_argument(
        "--report",
        default="data/processed/rag_eval_report.json",
        help="Output path for JSON report (relative to backend/)."
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=0,
        help="Limit number of cases (0 = all)."
    )
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Use Claude generation for answer evaluation (default: retrieval-only mode)."
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.9,
        help="Quality gate: minimum pass_rate required."
    )
    parser.add_argument(
        "--min-refusal-accuracy",
        type=float,
        default=1.0,
        help="Quality gate: minimum refusal_accuracy required."
    )
    parser.add_argument(
        "--min-citation-page-valid-rate",
        type=float,
        default=1.0,
        help="Quality gate: minimum citation_page_valid_rate required."
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    backend_root = Path(__file__).parent.parent
    dataset_path = str((backend_root / args.dataset).resolve())
    report_path = str((backend_root / args.report).resolve())
    return asyncio.run(
        run_eval(
            dataset_path=dataset_path,
            report_path=report_path,
            max_cases=args.max_cases,
            use_llm=args.with_llm,
            min_pass_rate=args.min_pass_rate,
            min_refusal_accuracy=args.min_refusal_accuracy,
            min_citation_page_valid_rate=args.min_citation_page_valid_rate,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
