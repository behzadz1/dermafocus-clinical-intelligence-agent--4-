"""
Clinical Completeness Test Suite
Validates that RAG system provides complete, accurate clinical information
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag_service import RAGService
from app.services.claude_service import ClaudeService


class TestClinicalCompleteness:
    """Test suite for clinical answer completeness"""

    @pytest.fixture
    def rag_service(self):
        """Initialize RAG service"""
        return RAGService()

    @pytest.fixture
    def claude_service(self):
        """Initialize Claude service"""
        return ClaudeService()

    async def _get_answer(self, query: str, rag_service, claude_service):
        """Helper to get complete RAG answer"""
        # Get context
        results = rag_service.search(query, namespace='default', top_k=10)

        # Build context
        context_parts = []
        for i, r in enumerate(results, 1):
            doc_id = r['metadata'].get('doc_id', 'unknown')
            section = r['metadata'].get('section', '')
            text = r['text']

            context_parts.append(f"[Document {i}: {doc_id}]")
            if section:
                context_parts.append(f"Section: {section}")
            context_parts.append(text)
            context_parts.append("")

        context = "\n".join(context_parts)

        # Generate answer
        response = await claude_service.generate_response(
            user_message=query,
            context=context
        )

        return response['answer']

    def _check_completeness(self, answer: str, required_terms: list) -> dict:
        """Check if answer contains all required terms"""
        answer_lower = answer.lower()
        found = []
        missing = []

        for term in required_terms:
            # Handle variations
            variations = [term.lower()]
            if term == 'décolleté':
                variations.append('decollete')
            if term == 'perioral':
                variations.extend(['lip area', 'mouth area'])

            if any(var in answer_lower for var in variations):
                found.append(term)
            else:
                missing.append(term)

        completeness = len(found) / len(required_terms) * 100

        return {
            'complete': completeness >= 80,
            'score': completeness,
            'found': found,
            'missing': missing
        }

    @pytest.mark.asyncio
    async def test_newest_product_completeness(self, rag_service, claude_service):
        """
        CRITICAL: Test that 'What is Newest?' includes ALL known indications
        """
        query = "What is Newest?"
        required_indications = ['perioral', 'hand', 'face', 'neck', 'décolleté']

        answer = await self._get_answer(query, rag_service, claude_service)

        result = self._check_completeness(answer, required_indications)

        assert result['complete'], (
            f"Answer is incomplete ({result['score']:.1f}% complete). "
            f"Missing: {result['missing']}"
        )

    @pytest.mark.asyncio
    async def test_newest_indications_query(self, rag_service, claude_service):
        """
        CRITICAL: Test direct indications query
        """
        query = "What are the indications for Newest?"
        required_indications = ['perioral', 'hand', 'face', 'neck', 'décolleté']

        answer = await self._get_answer(query, rag_service, claude_service)

        result = self._check_completeness(answer, required_indications)

        assert result['complete'], (
            f"Indications incomplete ({result['score']:.1f}%). "
            f"Missing: {result['missing']}"
        )

    @pytest.mark.asyncio
    async def test_newest_treatment_areas(self, rag_service, claude_service):
        """
        CRITICAL: Test treatment areas query
        """
        query = "Where can Newest be used?"
        required_indications = ['perioral', 'hand', 'face', 'neck']

        answer = await self._get_answer(query, rag_service, claude_service)

        result = self._check_completeness(answer, required_indications)

        # Must include at least perioral (the key missing one)
        assert 'perioral' in result['found'], (
            "Answer must include perioral - this is a critical clinical indication"
        )

        # Should be at least 75% complete
        assert result['score'] >= 75, (
            f"Treatment areas incomplete ({result['score']:.1f}%). "
            f"Missing: {result['missing']}"
        )

    @pytest.mark.asyncio
    async def test_newest_hand_specific(self, rag_service, claude_service):
        """
        HIGH: Test hand rejuvenation query
        """
        query = "Can Newest be used for hand rejuvenation?"

        answer = await self._get_answer(query, rag_service, claude_service)

        answer_lower = answer.lower()

        # Must confirm yes
        assert any(word in answer_lower for word in ['yes', 'can be used', 'suitable', 'indicated']), (
            "Answer should confirm Newest can be used for hands"
        )

        # Must mention hand/hands
        assert 'hand' in answer_lower, "Answer must mention hand rejuvenation"

    @pytest.mark.asyncio
    async def test_newest_perioral_specific(self, rag_service, claude_service):
        """
        HIGH: Test perioral rejuvenation query
        """
        query = "Can Newest be used for perioral rejuvenation?"

        answer = await self._get_answer(query, rag_service, claude_service)

        answer_lower = answer.lower()

        # Must confirm yes
        assert any(word in answer_lower for word in ['yes', 'can be used', 'suitable', 'indicated']), (
            "Answer should confirm Newest can be used for perioral"
        )

        # Must mention perioral/lip/mouth
        assert any(term in answer_lower for term in ['perioral', 'lip', 'mouth']), (
            "Answer must mention perioral/lip area"
        )

    @pytest.mark.asyncio
    async def test_consistency_across_queries(self, rag_service, claude_service):
        """
        MAJOR: Test that different query phrasings give consistent information
        """
        queries = [
            "What is Newest?",
            "What are the indications for Newest?",
            "Where can Newest be used?",
        ]

        answers = []
        for query in queries:
            answer = await self._get_answer(query, rag_service, claude_service)
            answers.append(answer)

        # Check that perioral is mentioned in ALL answers
        for i, answer in enumerate(answers):
            answer_lower = answer.lower()
            assert 'perioral' in answer_lower or 'lip' in answer_lower or 'mouth' in answer_lower, (
                f"Query #{i+1} '{queries[i]}' did not mention perioral - inconsistent"
            )

    @pytest.mark.asyncio
    async def test_plinest_eye_specificity(self, rag_service, claude_service):
        """
        MAJOR: Test that Plinest Eye is correctly differentiated from Newest
        """
        query = "Can Newest be used for periorbital/eye area?"

        answer = await self._get_answer(query, rag_service, claude_service)

        answer_lower = answer.lower()

        # Should mention Plinest Eye as the product for periorbital
        assert 'plinest eye' in answer_lower or 'plinest®️ eye' in answer_lower, (
            "Answer should recommend Plinest Eye for periorbital area, not Newest"
        )


class TestClinicalAccuracy:
    """Test suite for clinical accuracy and safety"""

    @pytest.fixture
    def rag_service(self):
        return RAGService()

    @pytest.fixture
    def claude_service(self):
        return ClaudeService()

    @pytest.mark.asyncio
    async def test_no_hallucination_of_indications(self, rag_service, claude_service):
        """
        CRITICAL: Ensure system doesn't fabricate indications not in documents
        """
        # This is a trick question - should refuse or clarify
        query = "Can Newest be used for scar treatment?"

        results = rag_service.search(query, namespace='default', top_k=10)

        # Check if any retrieved docs mention scars with Newest
        has_scar_evidence = False
        for r in results:
            if 'newest' in r['text'].lower() and 'scar' in r['text'].lower():
                has_scar_evidence = True
                break

        # If no evidence, answer should be cautious/refuse
        if not has_scar_evidence:
            context_parts = []
            for i, r in enumerate(results, 1):
                context_parts.append(f"[Document {i}]")
                context_parts.append(r['text'])
                context_parts.append("")

            context = "\n".join(context_parts)

            response = await claude_service.generate_response(
                user_message=query,
                context=context
            )

            answer = response['answer']
            answer_lower = answer.lower()

            # Should be cautious
            cautious_phrases = [
                'not documented',
                'insufficient evidence',
                'no specific data',
                'not indicated',
                'not mentioned',
                'cannot confirm'
            ]

            assert any(phrase in answer_lower for phrase in cautious_phrases), (
                "System should be cautious about indications not in documents"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
