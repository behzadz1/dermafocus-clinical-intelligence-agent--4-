"""
Semantic Similarity Service
Computes sentence embeddings for semantic chunking
Uses lightweight model for fast boundary detection
"""

from typing import List, Optional
import numpy as np
import structlog

logger = structlog.get_logger()

# Lazy import to avoid startup overhead
_model = None
_model_name = "all-MiniLM-L6-v2"


def get_sentence_embedding_model():
    """
    Get or initialize the sentence embedding model
    Uses all-MiniLM-L6-v2 for speed and efficiency

    Returns:
        SentenceTransformer model instance
    """
    global _model

    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("loading_sentence_embedding_model", model=_model_name)
            _model = SentenceTransformer(_model_name)
            logger.info("sentence_embedding_model_loaded", model=_model_name)

        except ImportError:
            logger.warning(
                "sentence_transformers_not_installed",
                message="Install with: pip install sentence-transformers"
            )
            raise ImportError(
                "sentence-transformers library not installed. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as e:
            logger.error("failed_to_load_embedding_model", error=str(e))
            raise

    return _model


class SemanticSimilarityService:
    """
    Service for computing semantic similarity between text segments
    Used for intelligent chunk boundary detection
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize semantic similarity service

        Args:
            model_name: Name of sentence-transformers model to use
        """
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        """Lazy load the model"""
        if self._model is None:
            self._model = get_sentence_embedding_model()
        return self._model

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two text segments

        Args:
            text1: First text segment
            text2: Second text segment

        Returns:
            Similarity score between 0 and 1
        """
        try:
            model = self._get_model()

            # Generate embeddings
            embeddings = model.encode([text1, text2], convert_to_numpy=True)

            # Compute cosine similarity
            similarity = self._cosine_similarity(embeddings[0], embeddings[1])

            return float(similarity)

        except Exception as e:
            logger.error("failed_to_compute_similarity", error=str(e))
            # Return neutral similarity on error
            return 0.5

    def compute_pairwise_similarities(self, texts: List[str]) -> np.ndarray:
        """
        Compute pairwise similarities for a list of text segments

        Args:
            texts: List of text segments

        Returns:
            NxN similarity matrix
        """
        try:
            model = self._get_model()

            # Generate embeddings for all texts
            embeddings = model.encode(texts, convert_to_numpy=True)

            # Compute pairwise cosine similarities
            n = len(embeddings)
            similarities = np.zeros((n, n))

            for i in range(n):
                for j in range(i, n):
                    sim = self._cosine_similarity(embeddings[i], embeddings[j])
                    similarities[i, j] = sim
                    similarities[j, i] = sim

            return similarities

        except Exception as e:
            logger.error("failed_to_compute_pairwise_similarities", error=str(e))
            # Return identity matrix on error
            return np.eye(len(texts))

    def detect_semantic_boundaries(
        self,
        texts: List[str],
        threshold: float = 0.75
    ) -> List[int]:
        """
        Detect semantic boundaries in a sequence of text segments

        Args:
            texts: List of text segments (sentences or paragraphs)
            threshold: Similarity threshold below which a boundary is detected

        Returns:
            List of indices where semantic boundaries occur
        """
        if len(texts) < 2:
            return []

        boundaries = []

        try:
            model = self._get_model()

            # Generate embeddings
            embeddings = model.encode(texts, convert_to_numpy=True)

            # Compare consecutive segments
            for i in range(len(embeddings) - 1):
                similarity = self._cosine_similarity(embeddings[i], embeddings[i + 1])

                # If similarity drops below threshold, mark as boundary
                if similarity < threshold:
                    boundaries.append(i + 1)  # Boundary after segment i
                    logger.debug(
                        "semantic_boundary_detected",
                        position=i + 1,
                        similarity=round(similarity, 3)
                    )

        except Exception as e:
            logger.error("failed_to_detect_boundaries", error=str(e))
            # Return empty list on error (no boundaries detected)
            return []

        return boundaries

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity between 0 and 1
        """
        # Normalize vectors
        vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-10)
        vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-10)

        # Compute dot product
        similarity = np.dot(vec1_norm, vec2_norm)

        # Ensure result is in [0, 1] range
        # (cosine similarity is [-1, 1], but for similar texts it's typically [0, 1])
        similarity = max(0.0, min(1.0, similarity))

        return similarity

    def is_semantic_break(
        self,
        current_text: str,
        next_text: str,
        threshold: float = 0.75
    ) -> bool:
        """
        Check if there's a semantic break between two text segments

        Args:
            current_text: Current text segment
            next_text: Next text segment
            threshold: Similarity threshold

        Returns:
            True if semantic break detected (similarity < threshold)
        """
        similarity = self.compute_similarity(current_text, next_text)
        return similarity < threshold


# Singleton instance
_semantic_similarity_service = None


def get_semantic_similarity_service() -> SemanticSimilarityService:
    """Get singleton SemanticSimilarityService instance"""
    global _semantic_similarity_service
    if _semantic_similarity_service is None:
        _semantic_similarity_service = SemanticSimilarityService()
    return _semantic_similarity_service
