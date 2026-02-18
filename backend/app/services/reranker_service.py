"""
Reranker service for hybrid retrieval.
Supports multiple providers: sentence_transformers (ms-marco), cohere, jina
Uses a cross-encoder when available, with a safe fallback.
"""

from __future__ import annotations

import os
from typing import List, Optional, Dict, Any
import structlog

from app.config import settings

logger = structlog.get_logger()


class RerankerService:
    """
    Multi-provider reranking service

    Supported providers:
    - sentence_transformers: ms-marco-MiniLM-L-6-v2 (local, free, fast)
    - cohere: Rerank API (hosted, medical-tuned, paid)
    - jina: Jina Reranker v2 (hosted/local, multilingual)
    """

    def __init__(self):
        self.provider = getattr(settings, "reranker_provider", "sentence_transformers")
        self.model_name = getattr(settings, "reranker_model", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self._model = None
        self._cohere_client = None
        self._jina_client = None

        # API keys
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        self.jina_api_key = os.getenv("JINA_API_KEY")

    def _load_cross_encoder(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import CrossEncoder  # type: ignore
        except Exception as e:
            logger.warning("reranker_missing_dependency", provider=self.provider, error=str(e))
            return None

        try:
            logger.info("loading_cross_encoder", model=self.model_name)
            self._model = CrossEncoder(self.model_name)
            return self._model
        except Exception as e:
            logger.warning("reranker_load_failed", model=self.model_name, error=str(e))
            return None

    def score(self, query: str, passages: List[str]) -> Optional[List[float]]:
        """
        Rerank passages for a query using configured provider

        Args:
            query: Search query
            passages: List of passage texts to rerank

        Returns:
            List of scores (higher is better), or None on failure
        """
        if not passages:
            return []

        # Try primary provider
        try:
            if self.provider == "cohere":
                scores = self._score_with_cohere(query, passages)
                if scores is not None:
                    logger.info("reranker_success", provider="cohere", passages_count=len(passages))
                    return scores
                # Fallback to ms-marco
                logger.warning("cohere_reranker_failed", message="Falling back to ms-marco")

            elif self.provider == "jina":
                scores = self._score_with_jina(query, passages)
                if scores is not None:
                    logger.info("reranker_success", provider="jina", passages_count=len(passages))
                    return scores
                # Fallback to ms-marco
                logger.warning("jina_reranker_failed", message="Falling back to ms-marco")

        except Exception as e:
            logger.error("reranker_error", provider=self.provider, error=str(e))
            # Continue to fallback

        # Default/fallback: sentence_transformers (ms-marco)
        model = self._load_cross_encoder()
        if model is not None:
            try:
                pairs = [(query, passage) for passage in passages]
                raw_scores = model.predict(pairs)  # type: ignore[attr-defined]

                # PHASE 4.0 FIX: MS-MARCO outputs raw logits (can be negative)
                # Apply sigmoid to normalize to 0-1 probability range
                import numpy as np
                normalized_scores = 1 / (1 + np.exp(-raw_scores))
                scores = normalized_scores.tolist()

                logger.info("reranker_success", provider="sentence_transformers", passages_count=len(passages))
                return [float(score) for score in scores]
            except Exception as e:
                logger.error("ms_marco_reranker_failed", error=str(e))

        # Final fallback: lexical overlap
        logger.warning("all_rerankers_failed", message="Using lexical overlap fallback")
        return [self._lexical_overlap_score(query, passage) for passage in passages]

    def _score_with_cohere(self, query: str, passages: List[str]) -> Optional[List[float]]:
        """
        Rerank using Cohere Rerank API
        Medical domain-tuned for better clinical term understanding
        """
        if not self.cohere_api_key:
            logger.warning("cohere_api_key_missing", message="COHERE_API_KEY not set")
            return None

        try:
            # Lazy import
            if self._cohere_client is None:
                import cohere
                self._cohere_client = cohere.Client(self.cohere_api_key)

            # Call Cohere Rerank API
            # Model options: rerank-english-v2.0, rerank-multilingual-v2.0
            results = self._cohere_client.rerank(
                query=query,
                documents=passages,
                top_n=len(passages),  # Return all, already filtered upstream
                model="rerank-english-v2.0"
            )

            # Extract scores (relevance_scores are 0-1)
            scores = [0.0] * len(passages)
            for result in results.results:
                scores[result.index] = result.relevance_score

            return scores

        except ImportError:
            logger.warning("cohere_library_missing", message="Install with: pip install cohere")
            return None
        except Exception as e:
            logger.error("cohere_rerank_failed", error=str(e))
            return None

    def _score_with_jina(self, query: str, passages: List[str]) -> Optional[List[float]]:
        """
        Rerank using Jina Reranker v2
        Multilingual, can be hosted or use API
        """
        if not self.jina_api_key:
            logger.warning("jina_api_key_missing", message="JINA_API_KEY not set")
            return None

        try:
            # Lazy import
            if self._jina_client is None:
                import requests
                self._jina_client = {"api_key": self.jina_api_key}

            # Call Jina Reranker API
            url = "https://api.jina.ai/v1/rerank"
            headers = {
                "Authorization": f"Bearer {self.jina_api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "jina-reranker-v2-base-multilingual",
                "query": query,
                "documents": passages,
                "top_n": len(passages)
            }

            import requests
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()

            results = response.json()

            # Extract scores
            scores = [0.0] * len(passages)
            for result in results.get("results", []):
                index = result.get("index")
                score = result.get("relevance_score", 0.0)
                if index is not None:
                    scores[index] = score

            return scores

        except ImportError:
            logger.warning("requests_library_missing", message="Install with: pip install requests")
            return None
        except Exception as e:
            logger.error("jina_rerank_failed", error=str(e))
            return None

    @staticmethod
    def _lexical_overlap_score(query: str, passage: str) -> float:
        """Fallback scoring based on lexical overlap"""
        query_tokens = set(_simple_tokenize(query))
        if not query_tokens:
            return 0.0
        passage_tokens = set(_simple_tokenize(passage))
        if not passage_tokens:
            return 0.0
        overlap = len(query_tokens & passage_tokens)
        return overlap / max(1, len(query_tokens))


def _simple_tokenize(text: str) -> List[str]:
    import re
    return re.findall(r"[a-z0-9]+", (text or "").lower())


_reranker_service: Optional[RerankerService] = None


def get_reranker_service() -> RerankerService:
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service
