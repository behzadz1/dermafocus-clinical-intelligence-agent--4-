"""
Reranker service for hybrid retrieval.
Uses a cross-encoder when available, with a safe fallback.
"""

from __future__ import annotations

from typing import List, Optional
import structlog

from app.config import settings

logger = structlog.get_logger()


class RerankerService:
    def __init__(self):
        self.provider = getattr(settings, "reranker_provider", "sentence_transformers")
        self.model_name = getattr(settings, "reranker_model", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self._model = None

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
        if not passages:
            return []

        if self.provider == "sentence_transformers":
            model = self._load_cross_encoder()
            if model is None:
                return None
            pairs = [(query, passage) for passage in passages]
            scores = model.predict(pairs).tolist()  # type: ignore[attr-defined]
            return [float(score) for score in scores]

        # Fallback: lexical overlap as a lightweight reranker
        return [self._lexical_overlap_score(query, passage) for passage in passages]

    @staticmethod
    def _lexical_overlap_score(query: str, passage: str) -> float:
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
