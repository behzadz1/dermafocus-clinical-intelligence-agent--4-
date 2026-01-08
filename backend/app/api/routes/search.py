"""
Search Routes
Endpoints for direct vector search and semantic retrieval
"""

from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
import structlog

from app.config import settings

router = APIRouter()
logger = structlog.get_logger()


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class SearchResult(BaseModel):
    """Single search result"""
    doc_id: str = Field(..., description="Document identifier")
    chunk_id: str = Field(..., description="Chunk identifier")
    text: str = Field(..., description="Retrieved text content")
    score: float = Field(..., ge=0, le=1, description="Relevance score")
    metadata: dict = Field(..., description="Document metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "doc_plinest_factsheet_001",
                "chunk_id": "chunk_001_003",
                "text": "Plinest contains PN-HPT® 40mg/2ml...",
                "score": 0.92,
                "metadata": {
                    "document": "Mastelli_Portfolio",
                    "page": 9,
                    "section": "Product Specifications",
                    "doc_type": "product"
                }
            }
        }


class SearchResponse(BaseModel):
    """Search results response"""
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results found")
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")


class NamespaceStats(BaseModel):
    """Statistics for a Pinecone namespace"""
    namespace: str
    vector_count: int
    dimension: int


class IndexStats(BaseModel):
    """Pinecone index statistics"""
    index_name: str
    total_vectors: int
    dimension: int
    namespaces: List[NamespaceStats]


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.post("/semantic", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def semantic_search(
    query: str = Query(..., description="Search query", min_length=1, max_length=1000),
    namespace: Optional[str] = Query("default", description="Pinecone namespace to search"),
    top_k: int = Query(10, ge=1, le=50, description="Number of results to return"),
    filter_metadata: Optional[dict] = None
):
    """
    Semantic search using vector similarity
    
    Process:
    1. Generate query embedding
    2. Search Pinecone for similar vectors
    3. Return top-k results with metadata
    
    Args:
        query: Natural language search query
        namespace: Optional namespace filter (default)
        top_k: Number of results to return (1-50)
        filter_metadata: Optional metadata filters
    
    Returns: Ranked search results with relevance scores
    """
    import time
    start_time = time.time()
    
    logger.info(
        "semantic_search_request",
        query=query[:100],
        namespace=namespace,
        top_k=top_k
    )
    
    try:
        from app.services.rag_service import get_rag_service
        
        rag_service = get_rag_service()
        
        # Extract doc_type from filter_metadata if present
        doc_type = None
        if filter_metadata and "doc_type" in filter_metadata:
            doc_type = filter_metadata["doc_type"]
        
        # Perform semantic search
        chunks = rag_service.search(
            query=query,
            top_k=top_k,
            namespace=namespace,
            doc_type=doc_type,
            min_score=0.6  # Lower threshold for search endpoint
        )
        
        # Format results
        search_results = []
        for chunk in chunks:
            search_results.append(SearchResult(
                doc_id=chunk["metadata"].get("doc_id", "unknown"),
                chunk_id=chunk["chunk_id"],
                text=chunk["text"],
                score=chunk["score"],
                metadata=chunk["metadata"]
            ))
        
        search_time = (time.time() - start_time) * 1000
        
        logger.info(
            "semantic_search_completed",
            query=query[:100],
            results_found=len(search_results),
            time_ms=search_time
        )
        
        return SearchResponse(
            query=query,
            results=search_results,
            total_results=len(search_results),
            search_time_ms=search_time
        )
    
    except Exception as e:
        logger.error("semantic_search_failed", query=query[:100], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/similar/{doc_id}", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def find_similar_documents(
    doc_id: str,
    top_k: int = Query(5, ge=1, le=20, description="Number of similar documents to return")
):
    """
    Find documents similar to a given document
    
    Uses the document's content to find similar content
    
    Args:
        doc_id: Document identifier
        top_k: Number of similar documents to return
    
    Returns: Similar documents ranked by similarity
    """
    logger.info(
        "similar_documents_request",
        doc_id=doc_id,
        top_k=top_k
    )
    
    try:
        from app.services.rag_service import get_rag_service
        
        rag_service = get_rag_service()
        similar = rag_service.get_related_documents(doc_id, top_k=top_k)
        
        # Format results
        search_results = []
        for chunk in similar:
            search_results.append(SearchResult(
                doc_id=chunk["metadata"].get("doc_id", "unknown"),
                chunk_id=chunk["chunk_id"],
                text=chunk["text"],
                score=chunk["score"],
                metadata=chunk["metadata"]
            ))
        
        return SearchResponse(
            query=f"Similar to {doc_id}",
            results=search_results,
            total_results=len(search_results),
            search_time_ms=0
        )
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {doc_id}"
        )
    except Exception as e:
        logger.error("similar_documents_failed", doc_id=doc_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find similar documents: {str(e)}"
        )


@router.get("/stats", response_model=IndexStats, status_code=status.HTTP_200_OK)
async def get_index_stats():
    """
    Get Pinecone index statistics
    
    Returns:
        - Total vector count
        - Vectors per namespace
        - Index configuration
    """
    logger.info("index_stats_request")
    
    try:
        from app.services.pinecone_service import get_pinecone_service
        
        pinecone_service = get_pinecone_service()
        stats = pinecone_service.get_index_stats()
        
        # Format namespaces
        namespaces = []
        for ns_name, ns_data in stats["namespaces"].items():
            namespaces.append(NamespaceStats(
                namespace=ns_name,
                vector_count=ns_data["vector_count"],
                dimension=stats["dimension"]
            ))
        
        return IndexStats(
            index_name=settings.pinecone_index_name,
            total_vectors=stats["total_vector_count"],
            dimension=stats["dimension"],
            namespaces=namespaces
        )
    
    except Exception as e:
        logger.error("index_stats_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get index stats: {str(e)}"
        )


@router.post("/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_all_documents():
    """
    Reindex all documents in the knowledge base
    
    This is a heavy operation that:
    1. Deletes all vectors from Pinecone
    2. Reprocesses all documents
    3. Regenerates embeddings
    4. Uploads to Pinecone
    
    Use with caution!
    
    NOTE: This is a placeholder. Implementation in Phase 3.
    """
    logger.warning("reindex_all_requested")
    
    # TODO: Phase 3 - Implement reindexing
    # from app.services.embedding_service import EmbeddingService
    # from app.services.document_service import DocumentService
    # 
    # embedding_service = EmbeddingService()
    # doc_service = DocumentService()
    # 
    # # Clear Pinecone index
    # await embedding_service.clear_index()
    # 
    # # Reprocess all documents
    # documents = await doc_service.get_all_documents()
    # for doc in documents:
    #     await doc_service.reprocess_document(doc.doc_id)
    # 
    # return {
    #     "status": "reindexing_started",
    #     "total_documents": len(documents)
    # }
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Reindexing not yet implemented."
    )


@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_index():
    """
    Clear all vectors from Pinecone index
    
    ⚠️ WARNING: This is a destructive operation!
    All vectors will be deleted and cannot be recovered.
    
    Use only for testing or when rebuilding the knowledge base from scratch.
    
    NOTE: This is a placeholder. Implementation in Phase 3.
    """
    logger.warning("clear_index_requested")
    
    # TODO: Phase 3 - Implement index clearing
    # from app.services.embedding_service import EmbeddingService
    # 
    # embedding_service = EmbeddingService()
    # await embedding_service.clear_index()
    # 
    # logger.warning("index_cleared")
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Index clearing not yet implemented."
    )
