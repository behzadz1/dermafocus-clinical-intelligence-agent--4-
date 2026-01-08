"""
RAG (Retrieval-Augmented Generation) Service
Orchestrates semantic search and context retrieval
"""

from typing import List, Dict, Any, Optional
import json
from pathlib import Path
import structlog

from app.services.embedding_service import get_embedding_service
from app.services.pinecone_service import get_pinecone_service
from app.config import settings

logger = structlog.get_logger()


class RAGService:
    """
    Service for RAG operations: search, retrieve, and prepare context
    """
    
    def __init__(self):
        """Initialize RAG service"""
        self.embedding_service = get_embedding_service()
        self.pinecone_service = get_pinecone_service()
        self.processed_dir = Path(settings.processed_dir)
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        namespace: str = "default",
        doc_type: Optional[str] = None,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for relevant context
        
        Args:
            query: Search query
            top_k: Number of results to return
            namespace: Pinecone namespace to search
            doc_type: Filter by document type (product, protocol, etc.)
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of relevant chunks with metadata
        """
        try:
            logger.info(
                "RAG search initiated",
                query_length=len(query),
                top_k=top_k,
                doc_type=doc_type
            )
            
            # Generate query embedding
            query_embedding = self.embedding_service.embed_query(query)
            
            # Build metadata filter
            metadata_filter = {}
            if doc_type:
                metadata_filter["doc_type"] = doc_type
            
            # Search Pinecone
            results = self.pinecone_service.query(
                query_vector=query_embedding,
                top_k=top_k * 2,  # Get more, filter by score later
                namespace=namespace,
                filter=metadata_filter if metadata_filter else None,
                include_metadata=True
            )
            
            # Filter by minimum score and enrich with full text
            relevant_chunks = []
            for match in results["matches"]:
                if match["score"] >= min_score:
                    chunk_data = {
                        "chunk_id": match["id"],
                        "score": match["score"],
                        "metadata": match["metadata"],
                        "text": match["metadata"].get("text", "")
                    }
                    relevant_chunks.append(chunk_data)
            
            # Limit to top_k after filtering
            relevant_chunks = relevant_chunks[:top_k]
            
            logger.info(
                "RAG search completed",
                results_found=len(relevant_chunks),
                avg_score=sum(c["score"] for c in relevant_chunks) / len(relevant_chunks) if relevant_chunks else 0
            )
            
            return relevant_chunks
            
        except Exception as e:
            logger.error(
                "RAG search failed",
                error=str(e),
                query=query[:100]
            )
            raise
    
    def get_context_for_query(
        self,
        query: str,
        max_chunks: int = 5,
        doc_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get context for a query to pass to LLM
        
        Args:
            query: User question
            max_chunks: Maximum chunks to retrieve
            doc_type: Filter by document type
            
        Returns:
            Context dictionary with chunks and metadata
        """
        try:
            # Search for relevant chunks
            chunks = self.search(
                query=query,
                top_k=max_chunks,
                doc_type=doc_type
            )
            
            if not chunks:
                logger.warning("No relevant context found", query=query[:100])
                return {
                    "chunks": [],
                    "context_text": "",
                    "sources": []
                }
            
            # Prepare context text
            context_parts = []
            sources = []
            
            for i, chunk in enumerate(chunks, 1):
                # Add chunk text to context
                context_parts.append(
                    f"[Source {i}]\n{chunk['text']}\n"
                )
                
                # Track source
                sources.append({
                    "source_id": i,
                    "doc_id": chunk["metadata"].get("doc_id"),
                    "doc_type": chunk["metadata"].get("doc_type"),
                    "page": chunk["metadata"].get("page_number"),
                    "relevance_score": chunk["score"]
                })
            
            context_text = "\n".join(context_parts)
            
            logger.info(
                "Context prepared",
                chunks_used=len(chunks),
                total_chars=len(context_text)
            )
            
            return {
                "chunks": chunks,
                "context_text": context_text,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(
                "Failed to get context",
                error=str(e),
                query=query[:100]
            )
            raise
    
    def rerank_results(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results for better relevance
        Simple implementation - can be enhanced with cross-encoder
        
        Args:
            query: Original query
            chunks: Retrieved chunks
            top_k: Number of top results to return
            
        Returns:
            Reranked chunks
        """
        # For now, just sort by score and return top_k
        # TODO: Implement cross-encoder reranking in future
        sorted_chunks = sorted(
            chunks,
            key=lambda x: x["score"],
            reverse=True
        )
        
        return sorted_chunks[:top_k]
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Combine semantic search with keyword search
        
        Args:
            query: Search query
            top_k: Number of results
            semantic_weight: Weight for semantic vs keyword (0-1)
            
        Returns:
            Hybrid search results
        """
        # TODO: Implement hybrid search in future
        # For now, just use semantic search
        logger.info("Hybrid search - using semantic only (keyword search not yet implemented)")
        return self.search(query, top_k)
    
    def get_document_context(
        self,
        doc_id: str
    ) -> Dict[str, Any]:
        """
        Get full context from a specific document
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document data with all chunks
        """
        try:
            processed_file = self.processed_dir / f"{doc_id}_processed.json"
            
            if not processed_file.exists():
                raise FileNotFoundError(f"Document not found: {doc_id}")
            
            with open(processed_file) as f:
                doc_data = json.load(f)
            
            return doc_data
            
        except Exception as e:
            logger.error(
                "Failed to get document context",
                error=str(e),
                doc_id=doc_id
            )
            raise
    
    def get_related_documents(
        self,
        doc_id: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find documents related to a given document
        
        Args:
            doc_id: Source document ID
            top_k: Number of related docs to return
            
        Returns:
            List of related documents
        """
        try:
            # Get document
            doc_data = self.get_document_context(doc_id)
            
            # Use first chunk as query
            if doc_data["chunks"]:
                query_text = doc_data["chunks"][0]["text"]
                
                # Search for similar content
                results = self.search(
                    query=query_text,
                    top_k=top_k * 3  # Get more to filter out same doc
                )
                
                # Filter out chunks from same document
                related = []
                seen_docs = set()
                
                for chunk in results:
                    chunk_doc_id = chunk["metadata"].get("doc_id")
                    if chunk_doc_id != doc_id and chunk_doc_id not in seen_docs:
                        related.append(chunk)
                        seen_docs.add(chunk_doc_id)
                        
                        if len(seen_docs) >= top_k:
                            break
                
                return related[:top_k]
            
            return []
            
        except Exception as e:
            logger.error(
                "Failed to get related documents",
                error=str(e),
                doc_id=doc_id
            )
            raise


# Singleton instance
_rag_service = None

def get_rag_service() -> RAGService:
    """Get singleton RAG service instance"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
