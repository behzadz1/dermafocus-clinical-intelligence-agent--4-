"""
Embedding Service
Generates vector embeddings using OpenAI
"""

from typing import List, Dict, Any
from openai import OpenAI
import structlog

from app.config import settings

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
        Generate embedding for a single text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        try:
            # Clean text
            text = text.replace("\n", " ").strip()
            
            if not text:
                raise ValueError("Empty text provided")
            
            # Generate embedding
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            
            embedding = response.data[0].embedding
            
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
    ) -> List[List[float]]:
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
            
            all_embeddings = []
            
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                # Clean texts
                cleaned_batch = [
                    text.replace("\n", " ").strip()
                    for text in batch
                ]
                
                # Filter out empty texts
                non_empty = [t for t in cleaned_batch if t]
                
                if not non_empty:
                    logger.warning(
                        "Empty batch skipped",
                        batch_index=i // batch_size
                    )
                    continue
                
                # Generate embeddings
                response = self.client.embeddings.create(
                    model=self.model,
                    input=non_empty
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                logger.info(
                    "Batch processed",
                    batch_index=i // batch_size,
                    embeddings_generated=len(batch_embeddings)
                )
            
            logger.info(
                "All embeddings generated",
                total=len(all_embeddings)
            )
            
            return all_embeddings
            
        except Exception as e:
            logger.error(
                "Batch embedding generation failed",
                error=str(e),
                total_texts=len(texts)
            )
            raise
    
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
            for chunk, embedding in zip(chunks, embeddings):
                chunk["embedding"] = embedding
            
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
