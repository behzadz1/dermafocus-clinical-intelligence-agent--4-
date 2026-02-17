"""
Embedding Service
Generates vector embeddings using OpenAI
"""

from typing import List, Dict, Any, Optional
from openai import OpenAI
import structlog
import re

from app.config import settings
from app.utils import metrics
from app.services.cost_tracker import get_cost_tracker
from app.services.cache_service import get_cache, set_cache
import hashlib

logger = structlog.get_logger()


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI
    """
    
    def __init__(self):
        """Initialize OpenAI client"""
        self.api_key = settings.openai_api_key
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension
        # Conservative char cap to avoid embedding token overflows.
        self.max_chars_per_input = 20000
        self.max_segments_per_text = 8
        
        self._client = None
    
    @property
    def client(self) -> OpenAI:
        """Lazy load OpenAI client"""
        if self._client is None:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            
            logger.info("Initializing OpenAI client")
            self._client = OpenAI(api_key=self.api_key)
        
        return self._client
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text with caching

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        try:
            # Clean text
            text = self._normalize_text(text)

            if not text:
                raise ValueError("Empty text provided")

            # Check cache first (24hr TTL for embeddings)
            cache_key = f"embedding:{hashlib.sha256(text.encode()).hexdigest()}"
            cached_embedding = get_cache(cache_key)

            if cached_embedding is not None:
                logger.debug("embedding_cache_hit", text_length=len(text))
                return cached_embedding

            # Generate embedding
            segments = self._split_text_for_embedding(text)
            if len(segments) == 1:
                embedding = self._embed_single_with_retry(segments[0])
            else:
                segment_embeddings = self._embed_inputs_with_retry(segments)
                embedding = self._mean_pool_embeddings(segment_embeddings)

            # Cache the result (24 hours)
            set_cache(cache_key, embedding, ttl_seconds=86400)

            return embedding
            
        except Exception as e:
            logger.error(
                "Failed to generate embedding",
                error=str(e),
                text_length=len(text) if text else 0
            )
            raise
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batches
        
        Args:
            texts: List of input texts
            batch_size: Number of texts per batch
            
        Returns:
            List of embedding vectors
        """
        try:
            logger.info(
                "Generating embeddings batch",
                total_texts=len(texts),
                batch_size=batch_size
            )
            
            all_embeddings: List[Optional[List[float]]] = [None] * len(texts)

            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                expanded_inputs: List[str] = []
                expanded_to_global_idx: List[int] = []
                split_count = 0

                for local_idx, text in enumerate(batch):
                    normalized = self._normalize_text(text)
                    if not normalized:
                        continue

                    segments = self._split_text_for_embedding(normalized)
                    if len(segments) > 1:
                        split_count += 1

                    for segment in segments:
                        expanded_inputs.append(segment)
                        expanded_to_global_idx.append(i + local_idx)

                if not expanded_inputs:
                    logger.warning(
                        "Empty batch skipped",
                        batch_index=i // batch_size
                    )
                    continue

                embeddings_by_idx: Dict[int, List[List[float]]] = {}
                for j in range(0, len(expanded_inputs), batch_size):
                    input_slice = expanded_inputs[j:j + batch_size]
                    idx_slice = expanded_to_global_idx[j:j + batch_size]

                    output_embeddings = self._embed_inputs_with_retry(input_slice)

                    for global_idx, embedding in zip(idx_slice, output_embeddings):
                        embeddings_by_idx.setdefault(global_idx, []).append(embedding)

                for global_idx, segment_embeddings in embeddings_by_idx.items():
                    all_embeddings[global_idx] = self._mean_pool_embeddings(segment_embeddings)

                logger.info(
                    "Batch processed",
                    batch_index=i // batch_size,
                    embeddings_generated=len(embeddings_by_idx),
                    split_texts=split_count
                )
            
            logger.info(
                "All embeddings generated",
                total=len(all_embeddings)
            )
            
            missing = sum(1 for emb in all_embeddings if emb is None)
            if missing:
                logger.warning(
                    "Empty texts skipped during embedding",
                    skipped=missing
                )
            
            return all_embeddings
            
        except Exception as e:
            logger.error(
                "Batch embedding generation failed",
                error=str(e),
                total_texts=len(texts)
            )
            raise

    def _normalize_text(self, text: str) -> str:
        """Normalize text before embedding."""
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _split_text_for_embedding(self, text: str) -> List[str]:
        """
        Split long text into safe-size segments for embedding.
        """
        if len(text) <= self.max_chars_per_input:
            return [text]

        segments: List[str] = []
        remaining = text
        while remaining and len(segments) < self.max_segments_per_text:
            if len(remaining) <= self.max_chars_per_input:
                segments.append(remaining.strip())
                break

            split_at = remaining.rfind("\n", 0, self.max_chars_per_input)
            if split_at < int(self.max_chars_per_input * 0.5):
                split_at = remaining.rfind(" ", 0, self.max_chars_per_input)
            if split_at < int(self.max_chars_per_input * 0.5):
                split_at = self.max_chars_per_input

            chunk = remaining[:split_at].strip()
            if chunk:
                segments.append(chunk)
            remaining = remaining[split_at:].strip()

        if remaining and len(segments) >= self.max_segments_per_text:
            logger.warning(
                "Embedding text truncated after max segments",
                original_chars=len(text),
                kept_chars=sum(len(seg) for seg in segments)
            )

        return segments or [text[:self.max_chars_per_input]]

    def _mean_pool_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """Average multiple segment embeddings into one vector."""
        if not embeddings:
            raise ValueError("Cannot mean-pool empty embeddings")
        if len(embeddings) == 1:
            return embeddings[0]

        dims = len(embeddings[0])
        pooled = [0.0] * dims
        for embedding in embeddings:
            for idx, value in enumerate(embedding):
                pooled[idx] += value

        count = float(len(embeddings))
        return [value / count for value in pooled]

    def _embed_inputs_with_retry(self, inputs: List[str]) -> List[List[float]]:
        """
        Embed a list of inputs; fallback to per-input retries on length errors.
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=inputs
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            if not self._is_context_length_error(e):
                raise

            logger.warning(
                "Embedding batch exceeded model context, retrying per input",
                input_count=len(inputs)
            )
            return [self._embed_single_with_retry(text) for text in inputs]

    def _embed_single_with_retry(self, text: str, depth: int = 0) -> List[float]:
        """
        Embed one input with recursive split fallback when context is too long.
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )

            # Record token usage
            if hasattr(response, 'usage') and response.usage:
                metrics.record_token_usage("openai", input_tokens=response.usage.total_tokens)

                # Track cost
                cost_tracker = get_cost_tracker()
                cost_tracker.record_openai_cost(tokens=response.usage.total_tokens)

            return response.data[0].embedding
        except Exception as e:
            if not self._is_context_length_error(e) or depth >= 4 or len(text) < 800:
                raise

            split_at = self._find_split_point(text, max(400, len(text) // 2))
            left = text[:split_at].strip()
            right = text[split_at:].strip()
            segments = [part for part in (left, right) if part]
            if len(segments) < 2:
                raise

            logger.warning(
                "Retrying long embedding input with recursive split",
                depth=depth,
                text_length=len(text)
            )
            segment_embeddings = [self._embed_single_with_retry(part, depth + 1) for part in segments]
            return self._mean_pool_embeddings(segment_embeddings)

    def _is_context_length_error(self, error: Exception) -> bool:
        return "maximum context length" in str(error).lower()

    def _find_split_point(self, text: str, target: int) -> int:
        """
        Find a natural split near target index.
        """
        if target <= 0 or target >= len(text):
            return max(1, min(len(text) - 1, target))

        split_at = text.rfind("\n", 0, target)
        if split_at < int(target * 0.5):
            split_at = text.rfind(" ", 0, target)
        if split_at < int(target * 0.5):
            split_at = target

        return max(1, min(len(text) - 1, split_at))
    
    def embed_chunks(
        self,
        chunks: List[Dict[str, Any]],
        text_field: str = "text"
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for document chunks
        
        Args:
            chunks: List of chunk dictionaries
            text_field: Field name containing text to embed
            
        Returns:
            Chunks with embeddings added
        """
        try:
            logger.info(
                "Embedding chunks",
                total_chunks=len(chunks)
            )
            
            # Extract texts
            texts = [chunk[text_field] for chunk in chunks]
            
            # Generate embeddings
            embeddings = self.generate_embeddings_batch(texts)
            
            # Add embeddings to chunks
            skipped = 0
            for chunk, embedding in zip(chunks, embeddings):
                if embedding is None:
                    skipped += 1
                    continue
                chunk["embedding"] = embedding
            
            if skipped:
                logger.warning(
                    "Skipped empty chunks during embedding",
                    skipped=skipped
                )
            
            logger.info(
                "Chunks embedded successfully",
                total=len(chunks)
            )
            
            return chunks
            
        except Exception as e:
            logger.error(
                "Failed to embed chunks",
                error=str(e),
                chunk_count=len(chunks)
            )
            raise
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for search query
        
        Args:
            query: Search query text
            
        Returns:
            Query embedding vector
        """
        try:
            logger.info(
                "Embedding query",
                query_length=len(query)
            )
            
            embedding = self.generate_embedding(query)
            
            return embedding
            
        except Exception as e:
            logger.error(
                "Failed to embed query",
                error=str(e),
                query=query[:100]
            )
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if OpenAI API is accessible
        
        Returns:
            Health status
        """
        try:
            # Try to generate a simple embedding
            test_embedding = self.generate_embedding("health check")
            
            return {
                "status": "healthy",
                "model": self.model,
                "dimension": len(test_embedding)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Singleton instance
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get singleton Embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
