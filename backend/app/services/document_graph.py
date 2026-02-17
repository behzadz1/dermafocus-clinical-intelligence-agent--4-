"""
Document Graph Service
Manages relationships between documents based on product mentions and content similarity
"""

import re
import json
from typing import List, Dict, Set, Optional
import structlog
from collections import defaultdict

from app.services.cache_service import get_redis_client

logger = structlog.get_logger()

# Document graph TTL: 30 days (2592000 seconds)
# Longer than cache TTL because documents don't change often
GRAPH_TTL = 2592000


class DocumentGraph:
    """
    Manages cross-document relationships for comprehensive retrieval

    Graph Structure:
    - product→documents mapping (e.g., "Plinest Eye" → [factsheet, protocol, case_study])
    - document→products mapping (e.g., "Plinest_Eye_Factsheet" → ["Plinest Eye"])
    - document_type→documents mapping (e.g., "factsheet" → [all factsheet doc_ids])
    """

    # Product names to detect (aligned with query expansion)
    PRODUCT_NAMES = [
        'Newest', 'newest',
        'Plinest', 'plinest', 'Plinest Eye', 'plinest eye', 'Plinest Hair', 'plinest hair',
        'Plinest Fast', 'plinest fast', 'Plinest Care', 'plinest care',
        'NewGyn', 'newgyn',
        'Purasomes', 'purasomes', 'Purasomes Xcell', 'purasomes xcell',
        'Purasomes Skin Glow', 'purasomes skin glow', 'Purasomes Hair', 'purasomes hair',
        'Purasomes Nutri', 'purasomes nutri',
        'Polynucleotides', 'polynucleotides', 'PN', 'HPT',
        'Hyaluronic Acid', 'hyaluronic acid', 'HA'
    ]

    # Document type patterns
    DOC_TYPE_PATTERNS = {
        'factsheet': r'factsheet|fact\s*sheet|product\s*sheet',
        'protocol': r'protocol|clinical\s*protocol|treatment\s*protocol',
        'case_study': r'case\s*study|case\s*report',
        'brochure': r'brochure|marketing',
        'clinical_paper': r'clinical\s*paper|study|research|trial'
    }

    def __init__(self):
        self.redis_client = None

    def _get_client(self):
        """Get Redis client (lazy load)"""
        if self.redis_client is None:
            try:
                self.redis_client = get_redis_client()
            except Exception as e:
                logger.error("Failed to connect to Redis for document graph", error=str(e))
                # Return None - methods will check and skip Redis operations
                return None
        return self.redis_client

    def extract_product_mentions(self, text: str, doc_id: str) -> List[str]:
        """
        Extract product names mentioned in document text

        Args:
            text: Document text (full_text or chunk text)
            doc_id: Document ID for context

        Returns:
            List of unique product names found in text
        """
        # Normalize text for matching
        text_lower = text.lower()

        # Sort products by length (descending) to match longest names first
        sorted_products = sorted(
            self.PRODUCT_NAMES,
            key=lambda x: len(x),
            reverse=True
        )

        products_found = set()

        for product in sorted_products:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(product.lower()) + r'\b'
            if re.search(pattern, text_lower):
                # Store in canonical form (title case for products)
                canonical = product.title() if product.islower() else product
                products_found.add(canonical)

        products_list = sorted(list(products_found))

        if products_list:
            logger.debug(
                "products_extracted_from_document",
                doc_id=doc_id,
                products=products_list,
                count=len(products_list)
            )

        return products_list

    def infer_document_type(self, doc_id: str, doc_type: Optional[str] = None) -> str:
        """
        Infer document type from doc_id or provided doc_type

        Args:
            doc_id: Document ID (filename-based)
            doc_type: Explicit document type (if available)

        Returns:
            Document type string
        """
        if doc_type and doc_type != "document":
            return doc_type

        doc_id_lower = doc_id.lower()

        for doc_type_name, pattern in self.DOC_TYPE_PATTERNS.items():
            if re.search(pattern, doc_id_lower):
                return doc_type_name

        return "document"

    def add_document(
        self,
        doc_id: str,
        full_text: str,
        doc_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, List[str]]:
        """
        Add document to graph with product mentions

        Args:
            doc_id: Unique document identifier
            full_text: Full document text for product extraction
            doc_type: Document type (factsheet, protocol, case_study, etc.)
            metadata: Optional metadata

        Returns:
            Dictionary with:
            - products: List of products mentioned
            - related_docs: List of related document IDs
        """
        # Extract product mentions
        products = self.extract_product_mentions(full_text, doc_id)

        # Infer doc_type
        doc_type = self.infer_document_type(doc_id, doc_type)

        # Build document node
        doc_node = {
            "doc_id": doc_id,
            "products": products,
            "doc_type": doc_type,
            "metadata": metadata or {}
        }

        # Save to Redis
        client = self._get_client()
        if client is None:
            logger.warning("Redis unavailable, skipping document graph storage")
            return {"products": products, "related_docs": []}

        try:
            # Store document node
            doc_key = f"doc_graph:doc:{doc_id}"
            client.setex(doc_key, GRAPH_TTL, json.dumps(doc_node))

            # Update product→documents mappings
            for product in products:
                product_key = f"doc_graph:product:{product.lower()}"

                # Get existing doc list
                existing = client.get(product_key)
                doc_ids = json.loads(existing) if existing else []

                # Add this doc if not already present
                if doc_id not in doc_ids:
                    doc_ids.append(doc_id)
                    client.setex(product_key, GRAPH_TTL, json.dumps(doc_ids))

            # Update doc_type→documents mapping
            type_key = f"doc_graph:type:{doc_type}"
            existing = client.get(type_key)
            doc_ids = json.loads(existing) if existing else []
            if doc_id not in doc_ids:
                doc_ids.append(doc_id)
                client.setex(type_key, GRAPH_TTL, json.dumps(doc_ids))

            # Find related documents (same products)
            related_docs = self.get_related_documents(doc_id, products)

            logger.info(
                "document_added_to_graph",
                doc_id=doc_id,
                products=products,
                doc_type=doc_type,
                related_docs_count=len(related_docs)
            )

            return {
                "products": products,
                "related_docs": related_docs
            }

        except Exception as e:
            logger.error("failed_to_add_document_to_graph", doc_id=doc_id, error=str(e))
            return {"products": products, "related_docs": []}

    def get_related_documents(
        self,
        doc_id: str,
        products: Optional[List[str]] = None,
        max_related: int = 10
    ) -> List[Dict[str, any]]:
        """
        Get documents related to this document by shared products

        Args:
            doc_id: Document ID to find related docs for
            products: List of products (if already extracted)
            max_related: Maximum number of related docs to return

        Returns:
            List of related document dicts with:
            - doc_id: Related document ID
            - shared_products: Products shared with original doc
            - doc_type: Document type
        """
        client = self._get_client()
        if client is None:
            return []

        try:
            # Get document products if not provided
            if products is None:
                doc_key = f"doc_graph:doc:{doc_id}"
                doc_data = client.get(doc_key)
                if not doc_data:
                    return []
                doc_node = json.loads(doc_data)
                products = doc_node.get("products", [])

            if not products:
                return []

            # Find all documents that mention these products
            related_docs_map = defaultdict(lambda: {"doc_id": None, "shared_products": [], "doc_type": None})

            for product in products:
                product_key = f"doc_graph:product:{product.lower()}"
                doc_ids = client.get(product_key)

                if doc_ids:
                    doc_ids_list = json.loads(doc_ids)
                    for related_doc_id in doc_ids_list:
                        # Skip self
                        if related_doc_id == doc_id:
                            continue

                        # Get doc_type
                        related_doc_key = f"doc_graph:doc:{related_doc_id}"
                        related_doc_data = client.get(related_doc_key)

                        if related_doc_data:
                            related_doc_node = json.loads(related_doc_data)
                            related_docs_map[related_doc_id]["doc_id"] = related_doc_id
                            related_docs_map[related_doc_id]["shared_products"].append(product)
                            related_docs_map[related_doc_id]["doc_type"] = related_doc_node.get("doc_type")

            # Convert to list and sort by number of shared products
            related_docs = list(related_docs_map.values())
            related_docs.sort(key=lambda x: len(x["shared_products"]), reverse=True)

            return related_docs[:max_related]

        except Exception as e:
            logger.error("failed_to_get_related_documents", doc_id=doc_id, error=str(e))
            return []

    def get_documents_for_product(self, product_name: str, max_docs: int = 20) -> List[str]:
        """
        Get all documents that mention a specific product

        Args:
            product_name: Product name (case-insensitive)
            max_docs: Maximum number of documents to return

        Returns:
            List of document IDs
        """
        client = self._get_client()
        if client is None:
            return []

        try:
            product_key = f"doc_graph:product:{product_name.lower()}"
            doc_ids = client.get(product_key)

            if doc_ids:
                doc_ids_list = json.loads(doc_ids)
                return doc_ids_list[:max_docs]

            return []

        except Exception as e:
            logger.error("failed_to_get_documents_for_product", product=product_name, error=str(e))
            return []

    def get_documents_by_type(self, doc_type: str, max_docs: int = 50) -> List[str]:
        """
        Get all documents of a specific type

        Args:
            doc_type: Document type (factsheet, protocol, case_study, etc.)
            max_docs: Maximum number of documents to return

        Returns:
            List of document IDs
        """
        client = self._get_client()
        if client is None:
            return []

        try:
            type_key = f"doc_graph:type:{doc_type}"
            doc_ids = client.get(type_key)

            if doc_ids:
                doc_ids_list = json.loads(doc_ids)
                return doc_ids_list[:max_docs]

            return []

        except Exception as e:
            logger.error("failed_to_get_documents_by_type", doc_type=doc_type, error=str(e))
            return []

    def get_graph_stats(self) -> Dict[str, any]:
        """
        Get statistics about the document graph

        Returns:
            Dictionary with graph statistics
        """
        client = self._get_client()
        if client is None:
            return {"connected": False, "total_documents": 0, "total_products": 0}

        try:
            # Count documents
            doc_keys = list(client.scan_iter(match="doc_graph:doc:*", count=1000))
            total_documents = len(doc_keys)

            # Count products
            product_keys = list(client.scan_iter(match="doc_graph:product:*", count=1000))
            total_products = len(product_keys)

            # Count document types
            type_keys = list(client.scan_iter(match="doc_graph:type:*", count=1000))
            total_types = len(type_keys)

            logger.info(
                "document_graph_stats",
                total_documents=total_documents,
                total_products=total_products,
                total_types=total_types
            )

            return {
                "connected": True,
                "total_documents": total_documents,
                "total_products": total_products,
                "total_doc_types": total_types
            }

        except Exception as e:
            logger.error("failed_to_get_graph_stats", error=str(e))
            return {"connected": False, "error": str(e)}

    def clear_graph(self):
        """
        Clear all document graph data from Redis

        WARNING: This deletes all document relationships
        """
        client = self._get_client()
        if client is None:
            logger.warning("Redis unavailable, cannot clear graph")
            return

        try:
            # Delete all doc_graph keys
            keys = list(client.scan_iter(match="doc_graph:*", count=1000))
            if keys:
                client.delete(*keys)
                logger.info("document_graph_cleared", keys_deleted=len(keys))
            else:
                logger.info("document_graph_already_empty")

        except Exception as e:
            logger.error("failed_to_clear_graph", error=str(e))


# Singleton instance
_document_graph = None


def get_document_graph() -> DocumentGraph:
    """Get singleton DocumentGraph instance"""
    global _document_graph
    if _document_graph is None:
        _document_graph = DocumentGraph()
    return _document_graph
