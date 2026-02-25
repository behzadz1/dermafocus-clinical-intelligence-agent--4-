"""
LLM-as-a-Judge for RAG Evaluation
Uses Claude Opus 4.5 to evaluate RAG responses across multiple dimensions
"""

from typing import Dict, List, Any, Optional
import hashlib
import json
from pathlib import Path
from datetime import datetime
import structlog
from anthropic import AsyncAnthropic

from app.config import settings
from app.evaluation.rag_eval import GoldenQACase, CaseOutput
from app.services.cost_tracker import get_cost_tracker

logger = structlog.get_logger()


class LLMJudge:
    """
    LLM-as-a-Judge for automated RAG evaluation
    Uses Claude Opus 4.5 to score responses on multiple dimensions
    """

    def __init__(
        self,
        model: str = "claude-opus-4-5-20251101",
        cache_enabled: bool = True,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize LLM Judge

        Args:
            model: Claude model to use (default: Opus 4.5)
            cache_enabled: Enable caching of evaluations
            cache_dir: Directory for cache storage (default: data/judge_cache)
        """
        self.model = model
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.cache_enabled = cache_enabled

        # Use processed_dir parent as data dir
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            data_dir = Path(settings.processed_dir).parent
            self.cache_dir = data_dir / "judge_cache"

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cost_tracker = get_cost_tracker()

        logger.info(
            "LLM Judge initialized",
            model=model,
            cache_enabled=cache_enabled,
            cache_dir=str(self.cache_dir)
        )

    def _get_cache_key(self, evaluation_type: str, **kwargs) -> str:
        """
        Generate cache key from evaluation parameters

        Args:
            evaluation_type: Type of evaluation (context_relevance, groundedness, etc.)
            **kwargs: Evaluation parameters

        Returns:
            SHA256 hash as cache key
        """
        # Sort kwargs for consistent hashing
        sorted_items = sorted(kwargs.items())
        cache_string = f"{evaluation_type}|{json.dumps(sorted_items, sort_keys=True)}"
        return hashlib.sha256(cache_string.encode()).hexdigest()

    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Load evaluation result from cache

        Args:
            cache_key: Cache key

        Returns:
            Cached result or None if not found
        """
        if not self.cache_enabled:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                logger.debug("Cache hit", cache_key=cache_key[:8])
                return result
            except Exception as e:
                logger.warning("Cache read failed", cache_key=cache_key[:8], error=str(e))
                return None

        return None

    def _save_to_cache(self, cache_key: str, result: Dict[str, Any]) -> None:
        """
        Save evaluation result to cache

        Args:
            cache_key: Cache key
            result: Evaluation result
        """
        if not self.cache_enabled:
            return

        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.debug("Cache saved", cache_key=cache_key[:8])
        except Exception as e:
            logger.warning("Cache write failed", cache_key=cache_key[:8], error=str(e))

    async def _call_judge(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Call Claude judge with prompt

        Args:
            prompt: Evaluation prompt
            max_tokens: Maximum response tokens

        Returns:
            Judge response text
        """
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.0,  # Deterministic for evaluation
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Track cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.cost_tracker.record_claude_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

            return response.content[0].text.strip()

        except Exception as e:
            logger.error("Judge API call failed", error=str(e))
            raise

    async def evaluate_context_relevance(
        self,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate how relevant retrieved chunks are to the query

        Args:
            query: User query
            chunks: List of retrieved chunks with text and metadata

        Returns:
            Dictionary with relevance scores and details
        """
        # Check cache
        cache_key = self._get_cache_key(
            "context_relevance",
            query=query,
            chunk_ids=[c.get("id", "") for c in chunks]
        )
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        # Build prompt
        chunks_text = ""
        for i, chunk in enumerate(chunks, 1):
            text = chunk.get("text", "")[:500]  # Truncate long chunks
            doc_id = chunk.get("doc_id", "Unknown")
            score = chunk.get("score", 0.0)
            chunks_text += f"\n**Chunk {i}** (Doc: {doc_id}, Score: {score:.3f})\n{text}\n"

        prompt = f"""You are evaluating the relevance of retrieved document chunks for a RAG system query.

**Query**: {query}

**Retrieved Chunks**:
{chunks_text}

**Task**: For each chunk, rate its relevance to answering the query on a scale of 0-10.

**Relevance Scale**:
- 0-2: Irrelevant - Does not help answer the query
- 3-4: Minimally relevant - Contains some related terms but not helpful
- 5-6: Somewhat relevant - Contains relevant information but not directly on point
- 7-8: Relevant - Contains information that helps answer the query
- 9-10: Highly relevant - Directly addresses the query with key information

**Output Format** (JSON):
{{
  "chunk_scores": [
    {{"chunk_number": 1, "relevance_score": X, "reasoning": "brief explanation"}},
    {{"chunk_number": 2, "relevance_score": Y, "reasoning": "brief explanation"}},
    ...
  ],
  "average_relevance": Z.Z,
  "summary": "Overall assessment of context quality"
}}

Output only the JSON, no other text."""

        # Call judge
        response = await self._call_judge(prompt, max_tokens=1000)

        # Parse response
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            logger.error("Failed to parse judge response", response=response[:200])
            result = {
                "chunk_scores": [],
                "average_relevance": 0.0,
                "summary": "Error parsing response",
                "error": "JSON parse failed"
            }

        # Add metadata
        result["evaluation_type"] = "context_relevance"
        result["model"] = self.model
        result["timestamp"] = datetime.utcnow().isoformat()

        # Cache result
        self._save_to_cache(cache_key, result)

        logger.info(
            "Context relevance evaluated",
            avg_relevance=result.get("average_relevance", 0),
            num_chunks=len(chunks)
        )

        return result

    async def evaluate_groundedness(
        self,
        query: str,
        context: str,
        response: str
    ) -> Dict[str, Any]:
        """
        Evaluate if response claims are grounded in context

        Args:
            query: User query
            context: Retrieved context text
            response: Generated response

        Returns:
            Dictionary with groundedness score and claim analysis
        """
        # Check cache
        cache_key = self._get_cache_key(
            "groundedness",
            query=query,
            context=context[:1000],  # Truncate for cache key
            response=response
        )
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        # Truncate context if too long
        context_truncated = context[:3000] if len(context) > 3000 else context

        prompt = f"""You are evaluating whether a RAG system's response is grounded in the provided context.

**Query**: {query}

**Context** (retrieved from documents):
{context_truncated}

**Response** (generated by system):
{response}

**Task**: Extract factual claims from the response and verify if each is supported by the context.

**Groundedness Levels**:
- Supported: Claim is directly stated or clearly implied in context
- Partially supported: Claim is somewhat supported but with gaps or assumptions
- Not supported: Claim is not found in context (potential hallucination)

**Output Format** (JSON):
{{
  "claims": [
    {{"claim": "extracted claim", "support": "supported|partially|not_supported", "evidence": "quote from context or 'none'"}},
    ...
  ],
  "groundedness_score": X.X,
  "supported_count": N,
  "total_claims": M,
  "hallucinations": ["list of unsupported claims if any"],
  "summary": "Overall groundedness assessment"
}}

**Groundedness Score Calculation**:
- 1.0 = All claims supported
- 0.5-0.9 = Most claims supported, some partial
- 0.0-0.4 = Significant unsupported claims

Output only the JSON, no other text."""

        # Call judge
        response_text = await self._call_judge(prompt, max_tokens=1500)

        # Parse response
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse judge response", response=response_text[:200])
            result = {
                "claims": [],
                "groundedness_score": 0.0,
                "supported_count": 0,
                "total_claims": 0,
                "hallucinations": [],
                "summary": "Error parsing response",
                "error": "JSON parse failed"
            }

        # Add metadata
        result["evaluation_type"] = "groundedness"
        result["model"] = self.model
        result["timestamp"] = datetime.utcnow().isoformat()

        # Cache result
        self._save_to_cache(cache_key, result)

        logger.info(
            "Groundedness evaluated",
            score=result.get("groundedness_score", 0),
            total_claims=result.get("total_claims", 0),
            supported=result.get("supported_count", 0)
        )

        return result

    async def evaluate_answer_relevance(
        self,
        query: str,
        response: str
    ) -> Dict[str, Any]:
        """
        Evaluate how well the response addresses the query

        Args:
            query: User query
            response: Generated response

        Returns:
            Dictionary with answer relevance score and details
        """
        # Check cache
        cache_key = self._get_cache_key(
            "answer_relevance",
            query=query,
            response=response
        )
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        prompt = f"""You are evaluating how well a RAG system's response addresses the user's query.

**Query**: {query}

**Response**:
{response}

**Task**: Rate how relevant and responsive the answer is to the specific question asked.

**Relevance Scale** (0-10):
- 0-2: Off-topic - Does not address the query
- 3-4: Tangentially related - Mentions related topics but doesn't answer
- 5-6: Partially addresses - Answers some aspects but misses key points
- 7-8: Good answer - Addresses the query with relevant information
- 9-10: Excellent answer - Directly and completely addresses the query

**Evaluation Criteria**:
1. Does it answer the specific question asked?
2. Is the answer focused and on-topic?
3. Does it provide the information the user is seeking?
4. Is it appropriately scoped (not over/under-inclusive)?

**Output Format** (JSON):
{{
  "relevance_score": X,
  "addresses_query": true/false,
  "completeness": "complete|partial|incomplete",
  "focus": "focused|somewhat_focused|unfocused",
  "strengths": ["what the response does well"],
  "weaknesses": ["what could be improved"],
  "summary": "Overall relevance assessment"
}}

Output only the JSON, no other text."""

        # Call judge
        response_text = await self._call_judge(prompt, max_tokens=800)

        # Parse response
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse judge response", response=response_text[:200])
            result = {
                "relevance_score": 0,
                "addresses_query": False,
                "completeness": "unknown",
                "focus": "unknown",
                "strengths": [],
                "weaknesses": [],
                "summary": "Error parsing response",
                "error": "JSON parse failed"
            }

        # Add metadata
        result["evaluation_type"] = "answer_relevance"
        result["model"] = self.model
        result["timestamp"] = datetime.utcnow().isoformat()

        # Cache result
        self._save_to_cache(cache_key, result)

        logger.info(
            "Answer relevance evaluated",
            score=result.get("relevance_score", 0),
            addresses_query=result.get("addresses_query", False)
        )

        return result

    async def evaluate_overall_quality(
        self,
        query: str,
        response: str,
        ground_truth: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate overall response quality compared to ground truth

        Args:
            query: User query
            response: Generated response
            ground_truth: Expected answer (optional)

        Returns:
            Dictionary with quality scores and analysis
        """
        # Check cache
        cache_key = self._get_cache_key(
            "overall_quality",
            query=query,
            response=response,
            ground_truth=ground_truth or ""
        )
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        # Build prompt with or without ground truth
        if ground_truth:
            comparison_section = f"""
**Expected Answer** (ground truth):
{ground_truth}

**Evaluation Task**: Compare the system response to the ground truth and rate on:
1. **Accuracy**: Does it contain correct information? (0-10)
2. **Completeness**: Does it cover all key points from ground truth? (0-10)
3. **Clarity**: Is it well-written and easy to understand? (0-10)
"""
        else:
            comparison_section = """
**Evaluation Task**: Rate the system response on:
1. **Accuracy**: Does it appear factually correct? (0-10)
2. **Completeness**: Does it seem to fully answer the query? (0-10)
3. **Clarity**: Is it well-written and easy to understand? (0-10)
"""

        prompt = f"""You are evaluating the overall quality of a RAG system's response.

**Query**: {query}

**System Response**:
{response}
{comparison_section}

**Output Format** (JSON):
{{
  "accuracy_score": X,
  "completeness_score": Y,
  "clarity_score": Z,
  "overall_score": W,
  "key_strengths": ["strength 1", "strength 2"],
  "key_weaknesses": ["weakness 1", "weakness 2"],
  "missing_information": ["what's missing if ground truth provided"],
  "incorrect_information": ["any errors if detected"],
  "summary": "Overall quality assessment"
}}

**Overall Score**: Average of accuracy, completeness, clarity.

Output only the JSON, no other text."""

        # Call judge
        response_text = await self._call_judge(prompt, max_tokens=1000)

        # Parse response
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse judge response", response=response_text[:200])
            result = {
                "accuracy_score": 0,
                "completeness_score": 0,
                "clarity_score": 0,
                "overall_score": 0,
                "key_strengths": [],
                "key_weaknesses": [],
                "missing_information": [],
                "incorrect_information": [],
                "summary": "Error parsing response",
                "error": "JSON parse failed"
            }

        # Add metadata
        result["evaluation_type"] = "overall_quality"
        result["model"] = self.model
        result["timestamp"] = datetime.utcnow().isoformat()
        result["has_ground_truth"] = ground_truth is not None

        # Cache result
        self._save_to_cache(cache_key, result)

        logger.info(
            "Overall quality evaluated",
            overall_score=result.get("overall_score", 0),
            accuracy=result.get("accuracy_score", 0),
            completeness=result.get("completeness_score", 0)
        )

        return result

    async def evaluate_full_case(
        self,
        case: GoldenQACase,
        output: CaseOutput
    ) -> Dict[str, Any]:
        """
        Evaluate a complete test case with all metrics

        Args:
            case: Golden QA test case
            output: RAG system output for the case

        Returns:
            Dictionary with all evaluation results
        """
        logger.info("Evaluating full case", case_id=case.id)

        # Extract data from output
        query = case.question
        response = output.answer
        chunks = output.retrieved_chunks or []
        context = "\n\n".join([chunk.get("text", "") for chunk in chunks])

        # Run all evaluations concurrently
        import asyncio

        results = await asyncio.gather(
            self.evaluate_context_relevance(query, chunks),
            self.evaluate_groundedness(query, context, response),
            self.evaluate_answer_relevance(query, response),
            self.evaluate_overall_quality(query, response, ground_truth=None),
            return_exceptions=True
        )

        # Unpack results
        context_relevance_result = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
        groundedness_result = results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])}
        answer_relevance_result = results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])}
        overall_quality_result = results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])}

        # Compile full evaluation
        full_result = {
            "case_id": case.id,
            "query": query,
            "context_relevance": context_relevance_result,
            "groundedness": groundedness_result,
            "answer_relevance": answer_relevance_result,
            "overall_quality": overall_quality_result,
            "evaluated_at": datetime.utcnow().isoformat(),
            "judge_model": self.model
        }

        logger.info(
            "Full case evaluation complete",
            case_id=case.id,
            context_relevance=context_relevance_result.get("average_relevance", 0),
            groundedness=groundedness_result.get("groundedness_score", 0),
            answer_relevance=answer_relevance_result.get("relevance_score", 0)
        )

        return full_result
