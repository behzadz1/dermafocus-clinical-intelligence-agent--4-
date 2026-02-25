"""
Unit tests for LLM Judge evaluation
Tests all four evaluation dimensions with mocked API calls
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.evaluation.llm_judge import LLMJudge
from app.evaluation.rag_eval import GoldenQACase, CaseOutput


@pytest.fixture
def mock_llm_judge(tmp_path):
    """Create LLMJudge with mocked Anthropic client"""
    with patch('app.evaluation.llm_judge.AsyncAnthropic') as mock_client:
        judge = LLMJudge(
            model="claude-opus-4-5-20251101",
            cache_enabled=False,
            cache_dir=str(tmp_path / "judge_cache")
        )
        judge.client = mock_client.return_value
        yield judge


@pytest.fixture
def sample_case():
    """Sample test case"""
    return GoldenQACase(
        id="TEST-001",
        question="What is the injection depth for Plinest treatments?",
        expected_doc_ids=["Plinest Factsheet"],
        expected_keywords=["intradermal", "depth", "injection"],
        should_refuse=False,
        max_chunks=5
    )


@pytest.fixture
def sample_output():
    """Sample RAG output"""
    return CaseOutput(
        answer="Plinest is injected at an intradermal depth of 1-2mm for optimal results.",
        retrieved_chunks=[
            {
                "id": "chunk_1",
                "text": "Plinest treatment protocol: Inject intradermally at 1-2mm depth using a fine needle.",
                "doc_id": "Plinest Factsheet",
                "score": 0.92
            },
            {
                "id": "chunk_2",
                "text": "The intradermal injection technique ensures proper product placement.",
                "doc_id": "Plinest Factsheet",
                "score": 0.85
            }
        ],
        sources=[{"citation": "Plinest Factsheet", "page": 3}],
        evidence={"sufficient": True}
    )


class TestLLMJudgeCaching:
    """Test caching functionality"""

    def test_cache_key_generation(self, mock_llm_judge):
        """Cache keys should be deterministic and unique"""
        key1 = mock_llm_judge._get_cache_key(
            "context_relevance",
            query="test query",
            chunk_ids=["chunk1", "chunk2"]
        )
        key2 = mock_llm_judge._get_cache_key(
            "context_relevance",
            query="test query",
            chunk_ids=["chunk1", "chunk2"]
        )
        key3 = mock_llm_judge._get_cache_key(
            "context_relevance",
            query="different query",
            chunk_ids=["chunk1", "chunk2"]
        )

        assert key1 == key2, "Same inputs should produce same cache key"
        assert key1 != key3, "Different inputs should produce different cache keys"
        assert len(key1) == 64, "Cache key should be SHA256 hash (64 chars)"

    def test_cache_save_and_load(self, mock_llm_judge, tmp_path):
        """Cache should save and load correctly"""
        mock_llm_judge.cache_enabled = True
        mock_llm_judge.cache_dir = tmp_path

        cache_key = "test_cache_key"
        test_data = {"score": 0.85, "details": "test"}

        # Save to cache
        mock_llm_judge._save_to_cache(cache_key, test_data)

        # Load from cache
        loaded_data = mock_llm_judge._load_from_cache(cache_key)

        assert loaded_data == test_data, "Loaded data should match saved data"

    def test_cache_disabled(self, mock_llm_judge):
        """When cache disabled, should not save or load"""
        mock_llm_judge.cache_enabled = False

        cache_key = "test_key"
        test_data = {"score": 0.9}

        # Try to save
        mock_llm_judge._save_to_cache(cache_key, test_data)

        # Try to load
        loaded = mock_llm_judge._load_from_cache(cache_key)

        assert loaded is None, "Should not load when cache disabled"


class TestContextRelevanceEvaluation:
    """Test context relevance evaluation"""

    @pytest.mark.asyncio
    async def test_context_relevance_evaluation(self, mock_llm_judge):
        """Should evaluate chunk relevance correctly"""
        query = "What is the injection depth for Plinest?"
        chunks = [
            {
                "id": "chunk1",
                "text": "Plinest is injected at 1-2mm depth intradermally",
                "doc_id": "Doc1",
                "score": 0.92
            },
            {
                "id": "chunk2",
                "text": "Use a fine needle for injection",
                "doc_id": "Doc1",
                "score": 0.75
            }
        ]

        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "chunk_scores": [
                {"chunk_number": 1, "relevance_score": 9, "reasoning": "Directly answers question"},
                {"chunk_number": 2, "relevance_score": 6, "reasoning": "Related but not direct"}
            ],
            "average_relevance": 7.5,
            "summary": "Good context quality"
        }))]
        mock_response.usage = MagicMock(input_tokens=500, output_tokens=100)

        mock_llm_judge.client.messages.create = AsyncMock(return_value=mock_response)

        # Evaluate
        result = await mock_llm_judge.evaluate_context_relevance(query, chunks)

        assert result["average_relevance"] == 7.5
        assert len(result["chunk_scores"]) == 2
        assert result["evaluation_type"] == "context_relevance"
        assert "timestamp" in result


class TestGroundednessEvaluation:
    """Test groundedness evaluation"""

    @pytest.mark.asyncio
    async def test_groundedness_evaluation(self, mock_llm_judge):
        """Should detect grounded and ungrounded claims"""
        query = "What is Plinest used for?"
        context = "Plinest is a polynucleotide-based treatment for skin rejuvenation."
        response = "Plinest is used for skin rejuvenation and contains polynucleotides."

        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "claims": [
                {
                    "claim": "Plinest is used for skin rejuvenation",
                    "support": "supported",
                    "evidence": "polynucleotide-based treatment for skin rejuvenation"
                },
                {
                    "claim": "contains polynucleotides",
                    "support": "supported",
                    "evidence": "polynucleotide-based treatment"
                }
            ],
            "groundedness_score": 1.0,
            "supported_count": 2,
            "total_claims": 2,
            "hallucinations": [],
            "summary": "All claims supported by context"
        }))]
        mock_response.usage = MagicMock(input_tokens=600, output_tokens=150)

        mock_llm_judge.client.messages.create = AsyncMock(return_value=mock_response)

        # Evaluate
        result = await mock_llm_judge.evaluate_groundedness(query, context, response)

        assert result["groundedness_score"] == 1.0
        assert result["supported_count"] == 2
        assert result["total_claims"] == 2
        assert len(result["hallucinations"]) == 0
        assert result["evaluation_type"] == "groundedness"

    @pytest.mark.asyncio
    async def test_hallucination_detection(self, mock_llm_judge):
        """Should detect hallucinated claims"""
        query = "What is Plinest?"
        context = "Plinest is a skin treatment."
        response = "Plinest is FDA-approved and costs $500 per session."

        # Mock response with hallucinations
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "claims": [
                {
                    "claim": "Plinest is FDA-approved",
                    "support": "not_supported",
                    "evidence": "none"
                },
                {
                    "claim": "costs $500 per session",
                    "support": "not_supported",
                    "evidence": "none"
                }
            ],
            "groundedness_score": 0.0,
            "supported_count": 0,
            "total_claims": 2,
            "hallucinations": ["FDA-approved", "costs $500"],
            "summary": "Contains unsupported claims"
        }))]
        mock_response.usage = MagicMock(input_tokens=550, output_tokens=140)

        mock_llm_judge.client.messages.create = AsyncMock(return_value=mock_response)

        # Evaluate
        result = await mock_llm_judge.evaluate_groundedness(query, context, response)

        assert result["groundedness_score"] == 0.0
        assert result["supported_count"] == 0
        assert len(result["hallucinations"]) == 2


class TestAnswerRelevanceEvaluation:
    """Test answer relevance evaluation"""

    @pytest.mark.asyncio
    async def test_relevant_answer(self, mock_llm_judge):
        """Should score highly relevant answers high"""
        query = "What is the injection depth for Plinest?"
        response = "Plinest is injected at a depth of 1-2mm intradermally."

        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "relevance_score": 9,
            "addresses_query": True,
            "completeness": "complete",
            "focus": "focused",
            "strengths": ["Directly answers the question", "Provides specific measurement"],
            "weaknesses": [],
            "summary": "Excellent answer that directly addresses the query"
        }))]
        mock_response.usage = MagicMock(input_tokens=400, output_tokens=80)

        mock_llm_judge.client.messages.create = AsyncMock(return_value=mock_response)

        # Evaluate
        result = await mock_llm_judge.evaluate_answer_relevance(query, response)

        assert result["relevance_score"] == 9
        assert result["addresses_query"] is True
        assert result["completeness"] == "complete"
        assert result["evaluation_type"] == "answer_relevance"

    @pytest.mark.asyncio
    async def test_off_topic_answer(self, mock_llm_judge):
        """Should score off-topic answers low"""
        query = "What is the injection depth?"
        response = "Plinest is a great product with many benefits for skin health."

        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "relevance_score": 2,
            "addresses_query": False,
            "completeness": "incomplete",
            "focus": "unfocused",
            "strengths": [],
            "weaknesses": ["Does not answer the specific question", "Talks about benefits instead of depth"],
            "summary": "Off-topic response"
        }))]
        mock_response.usage = MagicMock(input_tokens=400, output_tokens=80)

        mock_llm_judge.client.messages.create = AsyncMock(return_value=mock_response)

        # Evaluate
        result = await mock_llm_judge.evaluate_answer_relevance(query, response)

        assert result["relevance_score"] == 2
        assert result["addresses_query"] is False
        assert len(result["weaknesses"]) > 0


class TestOverallQualityEvaluation:
    """Test overall quality evaluation"""

    @pytest.mark.asyncio
    async def test_quality_without_ground_truth(self, mock_llm_judge):
        """Should evaluate quality without ground truth"""
        query = "What is Plinest?"
        response = "Plinest is a polynucleotide-based treatment for skin rejuvenation."

        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "accuracy_score": 9,
            "completeness_score": 8,
            "clarity_score": 9,
            "overall_score": 8.7,
            "key_strengths": ["Clear explanation", "Factual information"],
            "key_weaknesses": ["Could include more details"],
            "missing_information": [],
            "incorrect_information": [],
            "summary": "High quality response"
        }))]
        mock_response.usage = MagicMock(input_tokens=450, output_tokens=100)

        mock_llm_judge.client.messages.create = AsyncMock(return_value=mock_response)

        # Evaluate
        result = await mock_llm_judge.evaluate_overall_quality(query, response)

        assert result["overall_score"] == 8.7
        assert result["accuracy_score"] == 9
        assert result["has_ground_truth"] is False
        assert result["evaluation_type"] == "overall_quality"


class TestFullCaseEvaluation:
    """Test complete case evaluation"""

    @pytest.mark.asyncio
    async def test_full_case_evaluation(self, mock_llm_judge, sample_case, sample_output):
        """Should evaluate all dimensions for a full case"""
        # Mock all four evaluation methods
        mock_llm_judge.evaluate_context_relevance = AsyncMock(return_value={
            "average_relevance": 8.5,
            "evaluation_type": "context_relevance"
        })
        mock_llm_judge.evaluate_groundedness = AsyncMock(return_value={
            "groundedness_score": 0.95,
            "evaluation_type": "groundedness"
        })
        mock_llm_judge.evaluate_answer_relevance = AsyncMock(return_value={
            "relevance_score": 9,
            "evaluation_type": "answer_relevance"
        })
        mock_llm_judge.evaluate_overall_quality = AsyncMock(return_value={
            "overall_score": 8.8,
            "evaluation_type": "overall_quality"
        })

        # Evaluate
        result = await mock_llm_judge.evaluate_full_case(sample_case, sample_output)

        assert result["case_id"] == "TEST-001"
        assert result["query"] == sample_case.question
        assert "context_relevance" in result
        assert "groundedness" in result
        assert "answer_relevance" in result
        assert "overall_quality" in result
        assert "evaluated_at" in result
        assert result["judge_model"] == "claude-opus-4-5-20251101"

        # Verify all methods were called
        mock_llm_judge.evaluate_context_relevance.assert_called_once()
        mock_llm_judge.evaluate_groundedness.assert_called_once()
        mock_llm_judge.evaluate_answer_relevance.assert_called_once()
        mock_llm_judge.evaluate_overall_quality.assert_called_once()


class TestErrorHandling:
    """Test error handling in LLM judge"""

    @pytest.mark.asyncio
    async def test_json_parse_error(self, mock_llm_judge):
        """Should handle malformed JSON responses"""
        query = "test query"
        response = "test response"

        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is not valid JSON")]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=20)

        mock_llm_judge.client.messages.create = AsyncMock(return_value=mock_response)

        # Evaluate
        result = await mock_llm_judge.evaluate_answer_relevance(query, response)

        assert "error" in result
        assert result["relevance_score"] == 0
        assert result["addresses_query"] is False

    @pytest.mark.asyncio
    async def test_api_call_failure(self, mock_llm_judge):
        """Should handle API call failures gracefully"""
        query = "test query"
        chunks = [{"text": "test", "doc_id": "test", "score": 0.9}]

        # Mock API failure
        mock_llm_judge.client.messages.create = AsyncMock(side_effect=Exception("API Error"))

        # Should raise exception
        with pytest.raises(Exception):
            await mock_llm_judge.evaluate_context_relevance(query, chunks)
