"""
RAG evaluation harness for groundedness/citation/refusal regression checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REFUSAL_HINTS = (
    "insufficient documented evidence",
    "insufficient evidence",
    "cannot answer this safely",
    "cannot answer",
    "please upload or reference",
    "i do not have sufficient"
)


@dataclass
class GoldenQACase:
    """Single QA validation case."""
    id: str
    question: str
    expected_doc_ids: List[str] = field(default_factory=list)
    expected_keywords: List[str] = field(default_factory=list)
    should_refuse: bool = False
    max_chunks: int = 5
    tags: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class CaseOutput:
    """Observed system output for one case."""
    answer: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_chunks: List[Dict[str, Any]] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseResult:
    """Evaluation result for one case."""
    case_id: str
    question: str
    passed: bool
    should_refuse: bool
    refusal_correct: bool
    citation_presence: bool
    citation_page_valid: bool
    retrieval_recall_at_k: float
    keyword_coverage: float
    evidence_sufficient: bool
    error_buckets: List[str] = field(default_factory=list)


def load_golden_dataset(path: str) -> Tuple[Optional[str], List[GoldenQACase]]:
    """Load QA dataset from JSON file with optional version metadata."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    dataset_version: Optional[str] = None
    if isinstance(payload, dict):
        dataset_version = payload.get("version")
        items = payload.get("cases", [])
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("Unsupported dataset JSON structure.")

    cases: List[GoldenQACase] = []
    for item in items:
        cases.append(
            GoldenQACase(
                id=item["id"],
                question=item["question"],
                expected_doc_ids=item.get("expected_doc_ids", []),
                expected_keywords=item.get("expected_keywords", []),
                should_refuse=bool(item.get("should_refuse", False)),
                max_chunks=int(item.get("max_chunks", 5)),
                tags=item.get("tags", []),
                notes=item.get("notes", "")
            )
        )
    return dataset_version, cases


def load_golden_cases(path: str) -> List[GoldenQACase]:
    """Load QA cases from JSON file."""
    _, cases = load_golden_dataset(path)
    return cases


def evaluate_case(
    case: GoldenQACase,
    output: CaseOutput,
    expected_recall_threshold: float = 0.5,
    expected_keyword_threshold: float = 0.3
) -> CaseResult:
    """Score one case against expected behavior."""
    refusal_like = looks_like_refusal(output.answer)
    refusal_correct = refusal_like if case.should_refuse else not refusal_like

    citation_presence = len(output.sources) > 0
    citation_page_valid = all(_source_page_valid(src) for src in output.sources)

    retrieved_doc_ids = _collect_doc_ids(output)
    retrieval_recall = recall_at_k(retrieved_doc_ids, case.expected_doc_ids)
    keyword_coverage = keyword_coverage_rate(output.answer, case.expected_keywords)
    evidence_sufficient = bool(output.evidence.get("sufficient", False))

    pass_conditions: List[bool] = [refusal_correct]
    if case.should_refuse:
        pass_conditions.append(not citation_presence)
    else:
        pass_conditions.append(citation_presence)
        pass_conditions.append(citation_page_valid)
        if case.expected_doc_ids:
            pass_conditions.append(retrieval_recall >= expected_recall_threshold)
        else:
            pass_conditions.append(evidence_sufficient)
        if case.expected_keywords:
            pass_conditions.append(keyword_coverage >= expected_keyword_threshold)

    passed = all(pass_conditions)
    errors = bucket_errors(
        case=case,
        refusal_correct=refusal_correct,
        citation_presence=citation_presence,
        citation_page_valid=citation_page_valid,
        retrieval_recall=retrieval_recall,
        keyword_coverage=keyword_coverage,
        expected_recall_threshold=expected_recall_threshold,
        expected_keyword_threshold=expected_keyword_threshold
    )

    return CaseResult(
        case_id=case.id,
        question=case.question,
        passed=passed,
        should_refuse=case.should_refuse,
        refusal_correct=refusal_correct,
        citation_presence=citation_presence,
        citation_page_valid=citation_page_valid,
        retrieval_recall_at_k=round(retrieval_recall, 3),
        keyword_coverage=round(keyword_coverage, 3),
        evidence_sufficient=evidence_sufficient,
        error_buckets=errors
    )


def aggregate_results(results: List[CaseResult]) -> Dict[str, Any]:
    """Aggregate metrics and error buckets."""
    total = len(results)
    if total == 0:
        return {
            "total_cases": 0,
            "pass_rate": 0.0,
            "avg_retrieval_recall_at_k": 0.0,
            "avg_keyword_coverage": 0.0,
            "refusal_accuracy": 0.0,
            "citation_presence_rate": 0.0,
            "citation_page_valid_rate": 0.0,
            "error_buckets": {},
            "retraining_candidates": [],
            "prompt_tuning_candidates": [],
            "policy_tuning_candidates": []
        }

    pass_rate = sum(1 for r in results if r.passed) / total
    avg_recall = sum(r.retrieval_recall_at_k for r in results) / total
    avg_keywords = sum(r.keyword_coverage for r in results) / total
    refusal_accuracy = sum(1 for r in results if r.refusal_correct) / total
    citation_presence_rate = sum(1 for r in results if r.citation_presence) / total
    citation_page_valid_rate = sum(1 for r in results if r.citation_page_valid) / total

    bucket_counts: Dict[str, int] = {}
    for result in results:
        for bucket in result.error_buckets:
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    retraining_candidates = [r.question for r in results if "retrieval_miss" in r.error_buckets]
    prompt_tuning_candidates = [r.question for r in results if "low_content_coverage" in r.error_buckets]
    policy_tuning_candidates = [
        r.question
        for r in results
        if (
            "missed_refusal" in r.error_buckets
            or "false_refusal" in r.error_buckets
            or "citation_on_refusal" in r.error_buckets
        )
    ]

    return {
        "total_cases": total,
        "pass_rate": round(pass_rate, 3),
        "avg_retrieval_recall_at_k": round(avg_recall, 3),
        "avg_keyword_coverage": round(avg_keywords, 3),
        "refusal_accuracy": round(refusal_accuracy, 3),
        "citation_presence_rate": round(citation_presence_rate, 3),
        "citation_page_valid_rate": round(citation_page_valid_rate, 3),
        "error_buckets": bucket_counts,
        "retraining_candidates": retraining_candidates,
        "prompt_tuning_candidates": prompt_tuning_candidates,
        "policy_tuning_candidates": policy_tuning_candidates,
    }


def save_report(
    output_path: str,
    results: List[CaseResult],
    summary: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Persist evaluation report as JSON."""
    payload = {
        "metadata": metadata or {},
        "summary": summary,
        "results": [asdict(item) for item in results]
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def recall_at_k(retrieved_doc_ids: List[str], expected_doc_ids: List[str]) -> float:
    """Compute recall@k against expected docs."""
    expected = [normalize_doc_id(item) for item in expected_doc_ids if item]
    if not expected:
        return 1.0
    retrieved = [normalize_doc_id(item) for item in retrieved_doc_ids if item]

    matched = 0
    for exp in expected:
        if any(exp in got or got in exp for got in retrieved if got):
            matched += 1
    return matched / len(expected)


def keyword_coverage_rate(answer: str, expected_keywords: List[str]) -> float:
    """Compute expected keyword coverage in answer text."""
    if not expected_keywords:
        return 1.0
    answer_lower = (answer or "").lower()
    hits = sum(1 for keyword in expected_keywords if keyword.lower() in answer_lower)
    return hits / len(expected_keywords)


def looks_like_refusal(answer: str) -> bool:
    """Heuristic refusal detection."""
    answer_lower = (answer or "").lower()
    return any(token in answer_lower for token in REFUSAL_HINTS)


def bucket_errors(
    case: GoldenQACase,
    refusal_correct: bool,
    citation_presence: bool,
    citation_page_valid: bool,
    retrieval_recall: float,
    keyword_coverage: float,
    expected_recall_threshold: float,
    expected_keyword_threshold: float
) -> List[str]:
    """Classify failure buckets for continuous improvement workflows."""
    buckets: List[str] = []

    if case.should_refuse and not refusal_correct:
        buckets.append("missed_refusal")
    if not case.should_refuse and not refusal_correct:
        buckets.append("false_refusal")
    if case.should_refuse and citation_presence:
        buckets.append("citation_on_refusal")
    if not case.should_refuse and not citation_presence:
        buckets.append("missing_citation")
    if citation_presence and not citation_page_valid:
        buckets.append("invalid_citation_page")
    if case.expected_doc_ids and retrieval_recall < expected_recall_threshold:
        buckets.append("retrieval_miss")
    if case.expected_keywords and keyword_coverage < expected_keyword_threshold:
        buckets.append("low_content_coverage")

    return buckets


def normalize_doc_id(value: str) -> str:
    """Normalize doc IDs for robust matching."""
    lowered = (value or "").strip().lower()
    return "".join(ch for ch in lowered if ch.isalnum())


def _collect_doc_ids(output: CaseOutput) -> List[str]:
    doc_ids: List[str] = []

    for source in output.sources:
        doc_id = source.get("doc_id") or source.get("document")
        if doc_id:
            doc_ids.append(str(doc_id))

    for chunk in output.retrieved_chunks:
        metadata = chunk.get("metadata", {})
        doc_id = metadata.get("doc_id")
        if doc_id:
            doc_ids.append(str(doc_id))

    return doc_ids


def _source_page_valid(source: Dict[str, Any]) -> bool:
    page = source.get("page")
    if page is None:
        return False
    try:
        return int(page) > 0
    except (TypeError, ValueError):
        return False
