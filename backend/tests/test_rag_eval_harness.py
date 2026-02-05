"""Tests for RAG evaluation harness."""

from pathlib import Path

from app.evaluation.rag_eval import (
    CaseOutput,
    GoldenQACase,
    aggregate_results,
    evaluate_case,
    load_golden_cases,
)


FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "rag_eval_dataset.json"
)


def test_load_golden_cases():
    cases = load_golden_cases(str(FIXTURE_PATH))
    assert len(cases) >= 5
    assert any(case.should_refuse for case in cases)
    assert any(not case.should_refuse for case in cases)


def test_non_refusal_case_passes_with_citations_and_recall():
    case = GoldenQACase(
        id="T1",
        question="What is Plinest Eye?",
        expected_doc_ids=["Plinest Eye Factsheet"],
        expected_keywords=["plinest", "eye"],
        should_refuse=False,
    )
    output = CaseOutput(
        answer="Plinest Eye is indicated for periocular rejuvenation.",
        sources=[{"document": "Plinest Eye Factsheet", "page": 3}],
        retrieved_chunks=[{"metadata": {"doc_id": "Plinest Eye Factsheet"}}],
        evidence={"sufficient": True},
    )

    result = evaluate_case(case, output)
    assert result.passed is True
    assert result.error_buckets == []


def test_refusal_case_passes_when_refusal_and_no_sources():
    case = GoldenQACase(
        id="T2",
        question="Capital of Peru?",
        should_refuse=True,
    )
    output = CaseOutput(
        answer=(
            "I do not have sufficient documented evidence in the current "
            "Dermafocus knowledge base to answer this safely."
        ),
        sources=[],
        retrieved_chunks=[],
        evidence={"sufficient": False},
    )

    result = evaluate_case(case, output)
    assert result.passed is True
    assert result.refusal_correct is True


def test_bucketing_marks_failures():
    case = GoldenQACase(
        id="T3",
        question="Protocol for Newest",
        expected_doc_ids=["Newest Factsheet"],
        expected_keywords=["protocol", "sessions"],
        should_refuse=False,
    )
    output = CaseOutput(
        answer="I cannot answer that.",
        sources=[{"document": "Wrong Doc", "page": 0}],
        retrieved_chunks=[{"metadata": {"doc_id": "Wrong Doc"}}],
        evidence={"sufficient": True},
    )

    result = evaluate_case(case, output)
    assert result.passed is False
    assert "false_refusal" in result.error_buckets
    assert "invalid_citation_page" in result.error_buckets
    assert "retrieval_miss" in result.error_buckets
    assert "low_content_coverage" in result.error_buckets


def test_aggregate_returns_improvement_candidates():
    failing = GoldenQACase(
        id="T4",
        question="Need evidence",
        expected_doc_ids=["DocA"],
        expected_keywords=["keyword"],
    )
    ok = GoldenQACase(
        id="T5",
        question="Should refuse",
        should_refuse=True,
    )

    fail_result = evaluate_case(
        failing,
        CaseOutput(
            answer="Short answer",
            sources=[],
            retrieved_chunks=[],
            evidence={"sufficient": False},
        ),
    )
    ok_result = evaluate_case(
        ok,
        CaseOutput(
            answer="I do not have sufficient documented evidence to answer this safely.",
            sources=[],
            retrieved_chunks=[],
            evidence={"sufficient": False},
        ),
    )

    summary = aggregate_results([fail_result, ok_result])
    assert summary["total_cases"] == 2
    assert summary["pass_rate"] < 1.0
    assert "Need evidence" in summary["retraining_candidates"]
    assert "Need evidence" in summary["prompt_tuning_candidates"]

