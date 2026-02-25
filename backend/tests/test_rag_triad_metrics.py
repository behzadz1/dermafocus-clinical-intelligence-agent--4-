"""
Unit tests for RAG Triad Metrics
Tests the three core metrics: Context Relevance, Groundedness, and Answer Relevance
"""

import pytest
from app.evaluation.rag_eval import (
    _compute_context_relevance,
    _compute_groundedness,
    _compute_answer_relevance,
    evaluate_case,
    aggregate_results,
    GoldenQACase,
    CaseOutput,
)


class TestContextRelevance:
    """Test Context Relevance metric"""

    def test_high_similarity_chunks(self):
        """High similarity scores should yield high context relevance"""
        query = "What is the composition of Plinest?"
        chunks = [
            {"text": "Plinest contains PN-HPT 40mg/2ml", "score": 0.85, "adjusted_score": 0.85},
            {"text": "Polynucleotides are the main ingredient", "score": 0.78, "adjusted_score": 0.78},
        ]

        score, details = _compute_context_relevance(query, chunks)

        assert score >= 0.70, "High similarity should yield high relevance"
        assert details["method"] == "similarity_based"
        assert details["relevant_chunks"] == 2
        assert details["total_chunks"] == 2

    def test_low_similarity_chunks(self):
        """Low similarity scores should yield low context relevance"""
        query = "What is the composition of Plinest?"
        chunks = [
            {"text": "Unrelated content about something else", "score": 0.25, "adjusted_score": 0.25},
            {"text": "More irrelevant text", "score": 0.30, "adjusted_score": 0.30},
        ]

        score, details = _compute_context_relevance(query, chunks)

        assert score < 0.50, "Low similarity should yield low relevance"
        assert details["relevant_chunks"] == 0

    def test_no_chunks(self):
        """No retrieved chunks should yield zero relevance"""
        query = "What is the composition of Plinest?"
        chunks = []

        score, details = _compute_context_relevance(query, chunks)

        assert score == 0.0
        assert details["method"] == "no_chunks"

    def test_mixed_similarity_chunks(self):
        """Mixed similarity scores should yield average relevance"""
        query = "What is the composition of Plinest?"
        chunks = [
            {"text": "Relevant content", "score": 0.85, "adjusted_score": 0.85},
            {"text": "Somewhat relevant", "score": 0.45, "adjusted_score": 0.45},
            {"text": "Not very relevant", "score": 0.25, "adjusted_score": 0.25},
        ]

        score, details = _compute_context_relevance(query, chunks)

        assert 0.40 < score < 0.60, "Mixed similarity should yield average relevance"
        assert details["relevant_chunks"] == 1  # Only first chunk above 0.50


class TestGroundedness:
    """Test Groundedness/Faithfulness metric"""

    def test_grounded_with_citations(self):
        """Response with terms from context and citations should score high"""
        answer = "Plinest contains 40mg/2ml of polynucleotides according to the documentation."
        context = "Plinest® composition: PN-HPT® 40mg/2ml polynucleotides in sterile solution."
        chunks = []

        score, details = _compute_groundedness(answer, context, chunks)

        assert score >= 0.80, "Grounded response with citations should score high"
        assert details["has_citations"] is True
        assert details["grounded_terms"] > 0

    def test_hallucination_detection(self):
        """Response with terms not in context should score low"""
        answer = "Plinest contains 100mg of hyaluronic acid."
        context = "Plinest® composition: PN-HPT® 40mg/2ml polynucleotides."
        chunks = []

        score, details = _compute_groundedness(answer, context, chunks)

        assert score < 0.70, "Hallucinated response should score low"

    def test_proper_refusal(self):
        """Proper refusal should score 1.0 (perfectly grounded)"""
        answer = "I do not have sufficient evidence to answer this question."
        context = "Some context text"
        chunks = []

        score, details = _compute_groundedness(answer, context, chunks)

        assert score == 1.0, "Proper refusal should be perfectly grounded"
        assert details["method"] == "proper_refusal"
        assert details["grounded"] is True

    def test_no_specific_terms(self):
        """Response with generic terms that don't match context should score low"""
        answer = "This is helpful information about the product."
        context = "Different content and materials."
        chunks = []

        score, details = _compute_groundedness(answer, context, chunks)

        # Generic answer with terms not in context scores low (0 grounded terms)
        assert score <= 0.20, "Generic response with no matching terms should score low"


class TestAnswerRelevance:
    """Test Answer Relevance metric"""

    def test_relevant_answer_with_keywords(self):
        """Answer covering expected keywords should score high"""
        query = "What is the composition of Plinest?"
        answer = "Plinest composition includes polynucleotides at 40mg/2ml concentration."
        expected_keywords = ["composition", "polynucleotides", "plinest"]

        score, details = _compute_answer_relevance(query, answer, expected_keywords)

        assert score >= 0.80, "Relevant answer with keywords should score high"
        assert details["keyword_coverage"] == 1.0

    def test_off_topic_answer(self):
        """Answer not addressing query should score low"""
        query = "What is the composition of Plinest?"
        answer = "The treatment protocol involves three sessions spaced two weeks apart."
        expected_keywords = ["composition", "polynucleotides"]

        score, details = _compute_answer_relevance(query, answer, expected_keywords)

        assert score < 0.50, "Off-topic answer should score low"

    def test_appropriate_refusal(self):
        """Refusal when no keywords expected should score 1.0"""
        query = "What is the capital of Peru?"
        answer = "I cannot answer this safely without relevant documentation."
        expected_keywords = []

        score, details = _compute_answer_relevance(query, answer, expected_keywords)

        assert score == 1.0, "Appropriate refusal should score perfectly"
        assert details["method"] == "appropriate_refusal"

    def test_inappropriate_refusal(self):
        """Refusal when answer expected should score low"""
        query = "What is the composition of Plinest?"
        answer = "I cannot answer this question."
        expected_keywords = ["composition", "polynucleotides"]

        score, details = _compute_answer_relevance(query, answer, expected_keywords)

        assert score < 0.50, "Inappropriate refusal should score low"
        assert details["method"] == "unexpected_refusal"


class TestEvaluateCaseWithTriad:
    """Test integration of triad metrics into evaluate_case"""

    def test_evaluate_case_computes_triad(self):
        """evaluate_case should compute all triad metrics when compute_triad=True"""
        case = GoldenQACase(
            id="TEST-001",
            question="What is the composition of Plinest?",
            expected_doc_ids=["Plinest Factsheet"],
            expected_keywords=["composition", "polynucleotides"],
            should_refuse=False,
            max_chunks=5,
            tags=["test"],
            notes="Test case"
        )

        output = CaseOutput(
            answer="Plinest contains 40mg/2ml polynucleotides (PN-HPT).",
            sources=[{"doc_id": "Plinest Factsheet", "page": 1}],
            retrieved_chunks=[
                {"text": "Plinest composition: PN-HPT 40mg/2ml", "score": 0.85, "adjusted_score": 0.85,
                 "metadata": {"doc_id": "Plinest Factsheet"}}
            ],
            evidence={"sufficient": True}
        )

        result = evaluate_case(case, output, compute_triad=True)

        assert result.context_relevance_score > 0, "Context relevance should be computed"
        assert result.groundedness_score > 0, "Groundedness should be computed"
        assert result.answer_relevance_score > 0, "Answer relevance should be computed"
        assert "context_relevance" in result.triad_details
        assert "groundedness" in result.triad_details
        assert "answer_relevance" in result.triad_details

    def test_evaluate_case_skips_triad_when_disabled(self):
        """evaluate_case should skip triad metrics when compute_triad=False"""
        case = GoldenQACase(
            id="TEST-002",
            question="What is the composition of Plinest?",
            expected_doc_ids=["Plinest Factsheet"],
            expected_keywords=["composition"],
            should_refuse=False,
            max_chunks=5,
            tags=["test"],
            notes="Test case"
        )

        output = CaseOutput(
            answer="Plinest contains polynucleotides.",
            sources=[{"doc_id": "Plinest Factsheet", "page": 1}],
            retrieved_chunks=[
                {"text": "Plinest composition info", "score": 0.75, "adjusted_score": 0.75,
                 "metadata": {"doc_id": "Plinest Factsheet"}}
            ],
            evidence={"sufficient": True}
        )

        result = evaluate_case(case, output, compute_triad=False)

        assert result.context_relevance_score == 0.0, "Context relevance should be 0 when disabled"
        assert result.groundedness_score == 0.0, "Groundedness should be 0 when disabled"
        assert result.answer_relevance_score == 0.0, "Answer relevance should be 0 when disabled"
        assert result.triad_details == {}


class TestAggregateTriadMetrics:
    """Test aggregation of triad metrics"""

    def test_aggregate_includes_triad_metrics(self):
        """aggregate_results should include triad metrics in summary"""
        from app.evaluation.rag_eval import CaseResult

        results = [
            CaseResult(
                case_id="TEST-001",
                question="Question 1",
                passed=True,
                should_refuse=False,
                refusal_correct=True,
                citation_presence=True,
                citation_page_valid=True,
                retrieval_recall_at_k=0.8,
                keyword_coverage=0.9,
                evidence_sufficient=True,
                error_buckets=[],
                context_relevance_score=0.85,
                groundedness_score=0.90,
                answer_relevance_score=0.88
            ),
            CaseResult(
                case_id="TEST-002",
                question="Question 2",
                passed=True,
                should_refuse=False,
                refusal_correct=True,
                citation_presence=True,
                citation_page_valid=True,
                retrieval_recall_at_k=0.7,
                keyword_coverage=0.8,
                evidence_sufficient=True,
                error_buckets=[],
                context_relevance_score=0.75,
                groundedness_score=0.80,
                answer_relevance_score=0.82
            ),
        ]

        summary = aggregate_results(results)

        assert "rag_triad" in summary
        assert summary["rag_triad"]["avg_context_relevance"] == 0.8
        assert summary["rag_triad"]["avg_groundedness"] == 0.85
        assert summary["rag_triad"]["avg_answer_relevance"] == 0.85
        assert "triad_combined_score" in summary["rag_triad"]

    def test_aggregate_identifies_low_scoring_queries(self):
        """aggregate_results should identify queries with low triad scores"""
        from app.evaluation.rag_eval import CaseResult

        results = [
            CaseResult(
                case_id="TEST-001",
                question="Good query",
                passed=True,
                should_refuse=False,
                refusal_correct=True,
                citation_presence=True,
                citation_page_valid=True,
                retrieval_recall_at_k=0.8,
                keyword_coverage=0.9,
                evidence_sufficient=True,
                error_buckets=[],
                context_relevance_score=0.85,
                groundedness_score=0.90,
                answer_relevance_score=0.88
            ),
            CaseResult(
                case_id="TEST-002",
                question="Low context relevance",
                passed=False,
                should_refuse=False,
                refusal_correct=True,
                citation_presence=True,
                citation_page_valid=True,
                retrieval_recall_at_k=0.5,
                keyword_coverage=0.6,
                evidence_sufficient=False,
                error_buckets=["retrieval_miss"],
                context_relevance_score=0.45,  # Below threshold
                groundedness_score=0.80,
                answer_relevance_score=0.75
            ),
        ]

        summary = aggregate_results(results)

        assert "triad_improvement_candidates" in summary
        assert len(summary["triad_improvement_candidates"]["low_context_relevance"]) == 1
        assert "Low context relevance" in summary["triad_improvement_candidates"]["low_context_relevance"]
