"""
RAG (Retrieval-Augmented Generation) Service
Orchestrates semantic search and context retrieval
Supports hierarchical chunking with parent-child relationships
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import json
from pathlib import Path
from collections import defaultdict
import structlog

from app.services.embedding_service import get_embedding_service
from app.services.pinecone_service import get_pinecone_service
from app.config import settings

logger = structlog.get_logger()


# Chunk type constants
CHUNK_TYPE_SECTION = "section"  # Parent chunks (section summaries)
CHUNK_TYPE_DETAIL = "detail"    # Child chunks (detailed content)
CHUNK_TYPE_FLAT = "flat"        # Non-hierarchical chunks


class RAGService:
    """
    Service for RAG operations: search, retrieve, and prepare context
    """
    
    def __init__(self):
        """Initialize RAG service"""
        self.embedding_service = get_embedding_service()
        self.pinecone_service = get_pinecone_service()
        self.processed_dir = Path(settings.processed_dir)

    def infer_doc_type_for_intent(self, intent: str) -> Optional[str]:
        """
        Map an intent to a document type filter for retrieval.

        Args:
            intent: Classified intent label

        Returns:
            doc_type string or None for no filtering
        """
        intent_map = {
            "product_info": "product",
            "protocol": "protocol",
            "dosing": "protocol",
            "scheduling": "protocol",
            "equipment": "protocol",
            "contraindications": "clinical_paper",
            "safety": "clinical_paper"
        }
        return intent_map.get(intent)

    def _extract_product_terms(self, query: str) -> List[str]:
        """
        Identify product terms mentioned in the query for lexical boosting.
        """
        query_lower = query.lower()
        product_terms = [
            "newest",
            "plinest",
            "plinest eye",
            "plinest hair",
            "newgyn",
            "purasomes",
            "purasomes xcell",
            "purasomes skin glow",
            "sgc100",
            "sgc100+"
        ]
        return [term for term in product_terms if term in query_lower]
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        namespace: str = "default",
        doc_type: Optional[str] = None,
        min_score: float = 0.25
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for relevant context
        
        Args:
            query: Search query
            top_k: Number of results to return
            namespace: Pinecone namespace to search
            doc_type: Filter by document type (product, protocol, etc.)
            min_score: Minimum similarity score (0-1), lowered to 0.25 for better recall
            
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

            # Apply lightweight lexical boost for explicit product mentions
            product_terms = self._extract_product_terms(query)
            if product_terms:
                for chunk in relevant_chunks:
                    text_blob = " ".join([
                        chunk.get("text", ""),
                        str(chunk.get("metadata", {}).get("doc_id", "")),
                        str(chunk.get("metadata", {}).get("title", ""))
                    ]).lower()
                    boost = 0.0
                    if any(term in text_blob for term in product_terms):
                        boost += 0.08
                    if chunk.get("metadata", {}).get("doc_type") in {"product", "protocol"}:
                        boost += 0.03
                    chunk["adjusted_score"] = min(chunk["score"] + boost, 1.0)
            else:
                for chunk in relevant_chunks:
                    chunk["adjusted_score"] = chunk["score"]

            # Limit to top_k after reranking
            relevant_chunks = sorted(
                relevant_chunks,
                key=lambda c: c.get("adjusted_score", c["score"]),
                reverse=True
            )[:top_k]
            
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

    def hierarchical_search(
        self,
        query: str,
        top_k: int = 5,
        namespace: str = "default",
        doc_type: Optional[str] = None,
        min_score: float = 0.25,
        include_parent_context: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Hierarchical search that handles parent-child chunk relationships.

        When a child chunk matches:
        - Fetches the parent chunk for additional context
        - Boosts confidence when both parent and child match

        Args:
            query: Search query
            top_k: Number of results to return
            namespace: Pinecone namespace to search
            doc_type: Filter by document type
            min_score: Minimum similarity score
            include_parent_context: Whether to fetch parent context for child chunks

        Returns:
            List of relevant chunks with hierarchical context
        """
        try:
            logger.info(
                "Hierarchical RAG search initiated",
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

            # Search Pinecone - get more results to account for hierarchy
            results = self.pinecone_service.query(
                query_vector=query_embedding,
                top_k=top_k * 3,  # Get more for hierarchical processing
                namespace=namespace,
                filter=metadata_filter if metadata_filter else None,
                include_metadata=True
            )

            # Process results with hierarchy awareness
            chunks_by_parent: Dict[str, List[Dict]] = defaultdict(list)
            parent_chunks: Dict[str, Dict] = {}
            flat_chunks: List[Dict] = []

            for match in results["matches"]:
                if match["score"] < min_score:
                    continue

                chunk_data = {
                    "chunk_id": match["id"],
                    "score": match["score"],
                    "metadata": match["metadata"],
                    "text": match["metadata"].get("text", ""),
                    "chunk_type": match["metadata"].get("chunk_type", CHUNK_TYPE_FLAT),
                    "parent_id": match["metadata"].get("parent_id"),
                    "section": match["metadata"].get("section", "")
                }

                chunk_type = chunk_data["chunk_type"]

                if chunk_type == CHUNK_TYPE_SECTION:
                    # This is a parent chunk
                    parent_chunks[match["id"]] = chunk_data
                elif chunk_type == CHUNK_TYPE_DETAIL and chunk_data["parent_id"]:
                    # This is a child chunk - group by parent
                    chunks_by_parent[chunk_data["parent_id"]].append(chunk_data)
                else:
                    # Flat chunk
                    flat_chunks.append(chunk_data)

            # Fetch missing parent chunks for matched children
            if include_parent_context:
                missing_parents = set(chunks_by_parent.keys()) - set(parent_chunks.keys())
                if missing_parents:
                    fetched_parents = self._fetch_chunks_by_ids(list(missing_parents), namespace)
                    parent_chunks.update(fetched_parents)

            # Build enriched results with parent context
            enriched_chunks = []

            # Process children with their parents
            for parent_id, children in chunks_by_parent.items():
                parent = parent_chunks.get(parent_id)

                for child in children:
                    enriched_chunk = child.copy()

                    # Add parent context
                    if parent:
                        enriched_chunk["parent_context"] = parent.get("text", "")
                        enriched_chunk["parent_score"] = parent.get("score", 0)

                        # Boost score when both parent and child match
                        if parent.get("score", 0) >= min_score:
                            # Both matched - higher confidence
                            parent_child_boost = 0.05
                            enriched_chunk["adjusted_score"] = min(
                                child["score"] + parent_child_boost,
                                1.0
                            )
                            enriched_chunk["hierarchy_match"] = "both"
                        else:
                            enriched_chunk["adjusted_score"] = child["score"]
                            enriched_chunk["hierarchy_match"] = "child_only"
                    else:
                        enriched_chunk["adjusted_score"] = child["score"]
                        enriched_chunk["hierarchy_match"] = "child_only"

                    enriched_chunks.append(enriched_chunk)

            # Add parent-only matches (broad queries matching section summaries)
            for parent_id, parent in parent_chunks.items():
                if parent_id not in chunks_by_parent:
                    # Parent matched but no children - include for broad context
                    enriched_parent = parent.copy()
                    enriched_parent["adjusted_score"] = parent["score"]
                    enriched_parent["hierarchy_match"] = "parent_only"
                    enriched_chunks.append(enriched_parent)

            # Add flat chunks
            for chunk in flat_chunks:
                chunk["adjusted_score"] = chunk["score"]
                chunk["hierarchy_match"] = "flat"
                enriched_chunks.append(chunk)

            # Apply product term boosting
            product_terms = self._extract_product_terms(query)
            if product_terms:
                for chunk in enriched_chunks:
                    text_blob = " ".join([
                        chunk.get("text", ""),
                        chunk.get("parent_context", ""),
                        str(chunk.get("metadata", {}).get("doc_id", "")),
                    ]).lower()

                    if any(term in text_blob for term in product_terms):
                        chunk["adjusted_score"] = min(chunk["adjusted_score"] + 0.08, 1.0)

            # Sort by adjusted score and return top_k
            enriched_chunks = sorted(
                enriched_chunks,
                key=lambda c: c.get("adjusted_score", c["score"]),
                reverse=True
            )[:top_k]

            logger.info(
                "Hierarchical RAG search completed",
                results_found=len(enriched_chunks),
                parent_matches=len(parent_chunks),
                child_groups=len(chunks_by_parent),
                flat_matches=len(flat_chunks)
            )

            return enriched_chunks

        except Exception as e:
            logger.error(
                "Hierarchical RAG search failed",
                error=str(e),
                query=query[:100]
            )
            raise

    def _fetch_chunks_by_ids(
        self,
        chunk_ids: List[str],
        namespace: str = "default"
    ) -> Dict[str, Dict]:
        """
        Fetch specific chunks by their IDs.

        Args:
            chunk_ids: List of chunk IDs to fetch
            namespace: Pinecone namespace

        Returns:
            Dictionary mapping chunk_id to chunk data
        """
        try:
            if not chunk_ids:
                return {}

            # Use Pinecone fetch API
            result = self.pinecone_service.index.fetch(
                ids=chunk_ids,
                namespace=namespace
            )

            chunks = {}
            for chunk_id, vector_data in result.get("vectors", {}).items():
                chunks[chunk_id] = {
                    "chunk_id": chunk_id,
                    "score": 0,  # No score for fetched chunks
                    "metadata": vector_data.get("metadata", {}),
                    "text": vector_data.get("metadata", {}).get("text", ""),
                    "chunk_type": vector_data.get("metadata", {}).get("chunk_type", CHUNK_TYPE_FLAT),
                    "section": vector_data.get("metadata", {}).get("section", "")
                }

            return chunks

        except Exception as e:
            logger.warning(
                "Failed to fetch chunks by ID",
                error=str(e),
                chunk_ids=chunk_ids[:5]  # Log first 5 IDs
            )
            return {}
    
    def get_context_for_query(
        self,
        query: str,
        max_chunks: int = 5,
        doc_type: Optional[str] = None,
        use_hierarchical: bool = True
    ) -> Dict[str, Any]:
        """
        Get context for a query to pass to LLM.
        Uses hierarchical search when available for better context.

        Args:
            query: User question
            max_chunks: Maximum chunks to retrieve
            doc_type: Filter by document type
            use_hierarchical: Use hierarchical search with parent context

        Returns:
            Context dictionary with chunks, context text, and metadata
        """
        try:
            # Search for relevant chunks
            if use_hierarchical:
                chunks = self.hierarchical_search(
                    query=query,
                    top_k=max_chunks,
                    doc_type=doc_type,
                    include_parent_context=True
                )
            else:
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
                    "sources": [],
                    "hierarchy_stats": {}
                }

            # Prepare context text with hierarchical awareness
            context_parts = []
            sources = []
            hierarchy_stats = {
                "parent_matches": 0,
                "child_matches": 0,
                "flat_matches": 0,
                "both_matches": 0
            }

            for i, chunk in enumerate(chunks, 1):
                hierarchy_match = chunk.get("hierarchy_match", "flat")

                # Track hierarchy stats
                if hierarchy_match == "both":
                    hierarchy_stats["both_matches"] += 1
                elif hierarchy_match == "parent_only":
                    hierarchy_stats["parent_matches"] += 1
                elif hierarchy_match == "child_only":
                    hierarchy_stats["child_matches"] += 1
                else:
                    hierarchy_stats["flat_matches"] += 1

                # Build context with section info
                section = chunk.get("section", "")
                section_prefix = f"[{section}] " if section else ""

                # Include parent context for child chunks
                parent_context = chunk.get("parent_context", "")
                if parent_context and hierarchy_match in ["both", "child_only"]:
                    context_parts.append(
                        f"[Source {i} - {section_prefix}Context]\n{parent_context[:500]}...\n\n"
                        f"[Source {i} - {section_prefix}Detail]\n{chunk['text']}\n"
                    )
                else:
                    context_parts.append(
                        f"[Source {i}]{section_prefix}\n{chunk['text']}\n"
                    )

                # Track source with hierarchy info
                sources.append({
                    "source_id": i,
                    "doc_id": chunk["metadata"].get("doc_id"),
                    "doc_type": chunk["metadata"].get("doc_type"),
                    "section": section,
                    "page": chunk["metadata"].get("page_number"),
                    "relevance_score": chunk.get("adjusted_score", chunk["score"]),
                    "hierarchy_match": hierarchy_match,
                    "chunk_type": chunk.get("chunk_type", "flat")
                })

            context_text = "\n".join(context_parts)

            logger.info(
                "Hierarchical context prepared",
                chunks_used=len(chunks),
                total_chars=len(context_text),
                hierarchy_stats=hierarchy_stats
            )

            return {
                "chunks": chunks,
                "context_text": context_text,
                "sources": sources,
                "hierarchy_stats": hierarchy_stats
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
