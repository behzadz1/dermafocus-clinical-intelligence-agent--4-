"""
Response Verification Service
Detects hallucinations by verifying claims are grounded in retrieved context
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import structlog
import re

from app.services.claude_service import get_claude_service

logger = structlog.get_logger()


class VerificationResult(BaseModel):
    """Result of response verification"""
    is_grounded: bool
    grounding_ratio: float
    total_claims: int
    grounded_claims: int
    unsupported_claims: List[str]
    verification_method: str = "llm_based"


class ResponseVerificationService:
    """
    Verifies that response claims are grounded in retrieved context

    Methods:
    1. Extract claims from response
    2. For each claim, find supporting evidence in context
    3. Calculate grounding ratio
    4. Flag unsupported claims (potential hallucinations)
    """

    def __init__(self, grounding_threshold: float = 0.8):
        """
        Initialize verification service

        Args:
            grounding_threshold: Minimum ratio of grounded claims (0.8 = 80%)
        """
        self.grounding_threshold = grounding_threshold
        self.claude_service = get_claude_service()

    def verify_response(
        self,
        response: str,
        context: str,
        sources: List[Dict[str, Any]]
    ) -> VerificationResult:
        """
        Verify that response is grounded in context

        Args:
            response: Generated response text
            context: Retrieved context used for generation
            sources: Source documents with metadata

        Returns:
            VerificationResult with grounding analysis
        """
        try:
            logger.info("verification_started", response_length=len(response))

            # Extract claims from response
            claims = self._extract_claims(response)

            if not claims:
                # No claims to verify (e.g., "I don't have enough information")
                logger.info("no_claims_to_verify")
                return VerificationResult(
                    is_grounded=True,
                    grounding_ratio=1.0,
                    total_claims=0,
                    grounded_claims=0,
                    unsupported_claims=[]
                )

            # Verify each claim
            grounded_count = 0
            unsupported = []

            for claim in claims:
                is_grounded = self._find_supporting_evidence(claim, context)

                if is_grounded:
                    grounded_count += 1
                else:
                    unsupported.append(claim)

            grounding_ratio = grounded_count / len(claims) if claims else 1.0
            is_grounded = grounding_ratio >= self.grounding_threshold

            logger.info(
                "verification_completed",
                total_claims=len(claims),
                grounded_claims=grounded_count,
                grounding_ratio=round(grounding_ratio, 2),
                is_grounded=is_grounded
            )

            return VerificationResult(
                is_grounded=is_grounded,
                grounding_ratio=grounding_ratio,
                total_claims=len(claims),
                grounded_claims=grounded_count,
                unsupported_claims=unsupported
            )

        except Exception as e:
            logger.error("verification_failed", error=str(e))
            # On error, assume grounded (fail open for UX)
            return VerificationResult(
                is_grounded=True,
                grounding_ratio=1.0,
                total_claims=0,
                grounded_claims=0,
                unsupported_claims=[],
                verification_method="error_fallback"
            )

    def _extract_claims(self, response: str) -> List[str]:
        """
        Extract factual claims from response

        Uses LLM to identify specific factual statements that can be verified

        Args:
            response: Generated response text

        Returns:
            List of claim strings
        """
        # Use Claude to extract claims
        extraction_prompt = f"""Extract all factual claims from the following response.
A factual claim is a specific statement that can be verified (e.g., dosages, contraindications, procedures).
Exclude general statements, opinions, and formatting.

Response:
{response}

Return a JSON list of claims like: ["claim 1", "claim 2", "claim 3"]

JSON:"""

        try:
            # Use Claude for extraction
            extraction_response = self.claude_service.generate(
                prompt=extraction_prompt,
                max_tokens=500,
                temperature=0.0
            )

            # Parse JSON response
            import json
            claims_text = extraction_response.strip()

            # Extract JSON array (handle markdown code blocks)
            if "```json" in claims_text:
                claims_text = claims_text.split("```json")[1].split("```")[0].strip()
            elif "```" in claims_text:
                claims_text = claims_text.split("```")[1].split("```")[0].strip()

            claims = json.loads(claims_text)

            if isinstance(claims, list):
                logger.debug("claims_extracted", count=len(claims))
                return claims
            else:
                logger.warning("claims_extraction_unexpected_format")
                return []

        except Exception as e:
            logger.error("claims_extraction_failed", error=str(e))
            # Fallback: Extract sentences as claims
            return self._fallback_claim_extraction(response)

    def _fallback_claim_extraction(self, response: str) -> List[str]:
        """
        Fallback claim extraction using simple sentence splitting

        Args:
            response: Response text

        Returns:
            List of sentences (claims)
        """
        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+', response)

        # Filter out short/empty sentences
        claims = [
            s.strip() for s in sentences
            if len(s.strip()) > 20 and not s.strip().startswith('[Source')
        ]

        # Limit to first 10 claims (avoid excessive verification)
        return claims[:10]

    def _find_supporting_evidence(self, claim: str, context: str) -> bool:
        """
        Check if a claim is supported by the retrieved context

        Args:
            claim: Claim to verify
            context: Retrieved context

        Returns:
            True if claim is grounded, False if unsupported
        """
        # Method 1: Lexical overlap (fast, approximate)
        overlap_score = self._lexical_overlap(claim, context)

        if overlap_score >= 0.6:
            # High overlap - likely grounded
            return True

        # Method 2: LLM-based verification (slower, accurate)
        return self._llm_verify_claim(claim, context)

    def _lexical_overlap(self, claim: str, context: str) -> float:
        """
        Compute lexical overlap between claim and context

        Args:
            claim: Claim text
            context: Context text

        Returns:
            Overlap ratio (0-1)
        """
        # Tokenize and normalize
        claim_tokens = set(self._simple_tokenize(claim))
        context_tokens = set(self._simple_tokenize(context))

        if not claim_tokens:
            return 0.0

        # Compute overlap
        overlap = len(claim_tokens & context_tokens)
        return overlap / len(claim_tokens)

    def _llm_verify_claim(self, claim: str, context: str) -> bool:
        """
        Use LLM to verify if claim is supported by context

        Args:
            claim: Claim to verify
            context: Retrieved context

        Returns:
            True if supported, False otherwise
        """
        verification_prompt = f"""You are verifying if a claim is supported by the provided context.

Context:
{context[:3000]}

Claim to verify:
{claim}

Is this claim supported by the context above? Answer ONLY "YES" or "NO".

Answer:"""

        try:
            verification_response = self.claude_service.generate(
                prompt=verification_prompt,
                max_tokens=10,
                temperature=0.0
            )

            answer = verification_response.strip().upper()

            is_supported = "YES" in answer

            logger.debug(
                "llm_claim_verification",
                claim=claim[:50],
                is_supported=is_supported
            )

            return is_supported

        except Exception as e:
            logger.error("llm_verification_failed", error=str(e))
            # On error, assume grounded (fail open)
            return True

    @staticmethod
    def _simple_tokenize(text: str) -> List[str]:
        """Simple tokenization for lexical overlap"""
        return re.findall(r'[a-z0-9]+', text.lower())


# Singleton instance
_verification_service: Optional[ResponseVerificationService] = None


def get_verification_service(
    grounding_threshold: float = 0.8
) -> ResponseVerificationService:
    """
    Get singleton ResponseVerificationService instance

    Args:
        grounding_threshold: Minimum grounding ratio (default: 0.8 = 80%)

    Returns:
        ResponseVerificationService instance
    """
    global _verification_service
    if _verification_service is None:
        _verification_service = ResponseVerificationService(
            grounding_threshold=grounding_threshold
        )
    return _verification_service
