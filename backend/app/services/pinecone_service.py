"""
Pinecone Vector Database Service
Handles vector storage and semantic search
"""

import os
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
import structlog

from app.config import settings

logger = structlog.get_logger()


class PineconeService:
    """
    Service for interacting with Pinecone vector database
    """
    
    def __init__(self):
        """Initialize Pinecone connection"""
        self.api_key = settings.pinecone_api_key
        self.environment = settings.pinecone_environment
        self.index_name = settings.pinecone_index_name
        self.dimension = settings.embedding_dimension
        
        self._client = None
        self._index = None
    
    @property
    def client(self) -> Pinecone:
        """Lazy load Pinecone client"""
        if self._client is None:
            if not self.api_key:
                raise ValueError("PINECONE_API_KEY not configured")
            
            logger.info("Initializing Pinecone client")
            self._client = Pinecone(api_key=self.api_key)
        
        return self._client
    
    @property
    def index(self):
        """Get or create Pinecone index"""
        if self._index is None:
            self._index = self._get_or_create_index()
        
        return self._index
    
    def _get_or_create_index(self):
        """Get existing index or create new one"""
        try:
            # Check if index exists
            existing_indexes = self.client.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            if self.index_name not in index_names:
                logger.info(
                    "Creating new Pinecone index",
                    index_name=self.index_name,
                    dimension=self.dimension
                )
                
                # Create serverless index
                self.client.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.environment or "us-east-1"
                    )
                )
                
                logger.info("Pinecone index created successfully")
            else:
                logger.info(
                    "Using existing Pinecone index",
                    index_name=self.index_name
                )
            
            # Return index connection
            return self.client.Index(self.index_name)
            
        except Exception as e:
            logger.error("Failed to initialize Pinecone index", error=str(e))
            raise
    
    def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Upload vectors to Pinecone
        
        Args:
            vectors: List of vector dictionaries with id, values, metadata
            namespace: Namespace to organize vectors
            
        Returns:
            Upsert response with count
        """
        try:
            logger.info(
                "Upserting vectors to Pinecone",
                count=len(vectors),
                namespace=namespace
            )
            
            # Format vectors for Pinecone
            formatted_vectors = []
            for vec in vectors:
                formatted_vectors.append({
                    "id": vec["id"],
                    "values": vec["values"],
                    "metadata": vec.get("metadata", {})
                })
            
            # Upsert in batches of 100
            batch_size = 100
            total_upserted = 0
            
            for i in range(0, len(formatted_vectors), batch_size):
                batch = formatted_vectors[i:i + batch_size]
                response = self.index.upsert(
                    vectors=batch,
                    namespace=namespace
                )
                total_upserted += response.upserted_count
            
            logger.info(
                "Vectors upserted successfully",
                total=total_upserted,
                namespace=namespace
            )
            
            return {
                "upserted_count": total_upserted,
                "namespace": namespace
            }
            
        except Exception as e:
            logger.error(
                "Failed to upsert vectors",
                error=str(e),
                namespace=namespace
            )
            raise
    
    def query(
        self,
        query_vector: List[float],
        top_k: int = 10,
        namespace: str = "default",
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Query Pinecone for similar vectors
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            namespace: Namespace to query
            filter: Metadata filter dictionary
            include_metadata: Whether to include metadata in results
            
        Returns:
            Query results with matches
        """
        try:
            logger.info(
                "Querying Pinecone",
                top_k=top_k,
                namespace=namespace,
                has_filter=filter is not None
            )
            
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter,
                include_metadata=include_metadata
            )
            
            logger.info(
                "Query completed",
                matches=len(results.matches)
            )
            
            return {
                "matches": [
                    {
                        "id": match.id,
                        "score": match.score,
                        "metadata": match.metadata if include_metadata else {}
                    }
                    for match in results.matches
                ]
            }
            
        except Exception as e:
            logger.error(
                "Query failed",
                error=str(e),
                namespace=namespace
            )
            raise
    
    def delete_vectors(
        self,
        ids: List[str] = None,
        namespace: str = "default",
        delete_all: bool = False,
        filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Delete vectors from Pinecone
        
        Args:
            ids: List of vector IDs to delete
            namespace: Namespace to delete from
            delete_all: Delete all vectors in namespace
            filter: Metadata filter for deletion
            
        Returns:
            Deletion response
        """
        try:
            if delete_all:
                logger.warning(
                    "Deleting all vectors",
                    namespace=namespace
                )
                self.index.delete(delete_all=True, namespace=namespace)
                return {"deleted": "all", "namespace": namespace}
            
            elif ids:
                logger.info(
                    "Deleting vectors by ID",
                    count=len(ids),
                    namespace=namespace
                )
                self.index.delete(ids=ids, namespace=namespace)
                return {"deleted_count": len(ids), "namespace": namespace}
            
            elif filter:
                logger.info(
                    "Deleting vectors by filter",
                    filter=filter,
                    namespace=namespace
                )
                self.index.delete(filter=filter, namespace=namespace)
                return {"deleted": "filtered", "namespace": namespace}
            
            else:
                raise ValueError("Must provide ids, filter, or delete_all=True")
            
        except Exception as e:
            logger.error(
                "Deletion failed",
                error=str(e),
                namespace=namespace
            )
            raise
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Pinecone index
        
        Returns:
            Index statistics
        """
        try:
            stats = self.index.describe_index_stats()
            
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "namespaces": {
                    name: {"vector_count": ns.vector_count}
                    for name, ns in (stats.namespaces or {}).items()
                }
            }
            
        except Exception as e:
            logger.error("Failed to get index stats", error=str(e))
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if Pinecone is accessible
        
        Returns:
            Health status
        """
        try:
            # Try to get index stats as health check
            stats = self.get_index_stats()
            
            return {
                "status": "healthy",
                "index_name": self.index_name,
                "vector_count": stats["total_vector_count"],
                "dimension": stats["dimension"]
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Singleton instance
_pinecone_service = None

def get_pinecone_service() -> PineconeService:
    """Get singleton Pinecone service instance"""
    global _pinecone_service
    if _pinecone_service is None:
        _pinecone_service = PineconeService()
    return _pinecone_service
