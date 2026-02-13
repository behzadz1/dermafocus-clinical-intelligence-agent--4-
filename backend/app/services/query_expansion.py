"""
Query Expansion Service for RAG
Improves retrieval for comparison and complex queries
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ExpandedQuery:
    """Result of query expansion"""
    is_comparison: bool
    original_query: str
    expanded_queries: List[str]
    products: List[str]
    query_type: str  # 'comparison', 'product_info', 'technique', 'general'


class QueryExpansionService:
    """
    Expands queries to improve retrieval, especially for comparisons
    """

    # Comparison query patterns
    COMPARISON_PATTERNS = [
        r'difference between (.+?) and (.+?)[\?]?',
        r'compare (.+?) (?:to|vs|versus) (.+?)[\?]?',
        r'(.+?) vs\.? (.+?)[\?]?',
        r'(.+?) versus (.+?)[\?]?',
        r'how does (.+?) differ from (.+?)[\?]?',
        r'which is better[,:]? (.+?) or (.+?)[\?]?',
    ]

    # Product names (expandable)
    PRODUCT_NAMES = [
        'newest', 'plinest', 'plinest eye', 'plinest hair',
        'newgyn', 'purasomes', 'purasomes xcell',
        'purasomes skin glow', 'purasomes hair', 'purasomes nutri'
    ]

    def __init__(self):
        pass

    def expand_query(self, query: str) -> ExpandedQuery:
        """
        Expand query for better retrieval

        Args:
            query: Original user query

        Returns:
            ExpandedQuery with expansion strategy
        """
        query_lower = query.lower().strip()

        # Check if comparison query
        is_comparison, products = self._detect_comparison(query_lower)

        if is_comparison and len(products) >= 2:
            return self._expand_comparison_query(query, products)

        # Check if product info query
        product = self._detect_product(query_lower)
        if product:
            return self._expand_product_query(query, product)

        # Default: no expansion
        return ExpandedQuery(
            is_comparison=False,
            original_query=query,
            expanded_queries=[query],
            products=[],
            query_type='general'
        )

    def _detect_comparison(self, query_lower: str) -> Tuple[bool, List[str]]:
        """
        Detect if query is a comparison and extract products

        Returns:
            (is_comparison, [product1, product2])
        """
        for pattern in self.COMPARISON_PATTERNS:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                # Extract the two items being compared
                item1 = match.group(1).strip()
                item2 = match.group(2).strip()

                # Clean up common words
                item1 = self._clean_product_name(item1)
                item2 = self._clean_product_name(item2)

                return True, [item1, item2]

        return False, []

    def _detect_product(self, query_lower: str) -> Optional[str]:
        """Detect product name in query"""
        for product in self.PRODUCT_NAMES:
            if product in query_lower:
                return product
        return None

    def _clean_product_name(self, name: str) -> str:
        """Clean product name from query"""
        # Remove common filler words
        name = re.sub(r'\b(the|a|an)\b', '', name, flags=re.IGNORECASE)
        name = name.strip()

        # Handle variations (e.g., "plinest for hair" -> "plinest hair")
        name = re.sub(r'plinest for hair', 'plinest hair', name, flags=re.IGNORECASE)
        name = re.sub(r'plinest for eye', 'plinest eye', name, flags=re.IGNORECASE)

        return name

    def _expand_comparison_query(
        self,
        original_query: str,
        products: List[str]
    ) -> ExpandedQuery:
        """
        Expand comparison query to ensure both products are well-retrieved

        Strategy:
        1. Original comparison query
        2. Individual queries for each product (to get factsheets)
        3. Combined query for both products
        """
        expanded = [original_query]

        # Add individual product queries to ensure factsheets are retrieved
        for product in products:
            expanded.append(f"{product} factsheet composition indications")
            expanded.append(f"what is {product}")

        # Add combined query
        expanded.append(f"{products[0]} and {products[1]} comparison")

        return ExpandedQuery(
            is_comparison=True,
            original_query=original_query,
            expanded_queries=expanded,
            products=products,
            query_type='comparison'
        )

    def _expand_product_query(
        self,
        original_query: str,
        product: str
    ) -> ExpandedQuery:
        """
        Expand product info query

        Strategy:
        1. Original query
        2. Product + factsheet query
        3. Product + indications query
        """
        expanded = [
            original_query,
            f"{product} factsheet",
            f"{product} indications treatment areas"
        ]

        return ExpandedQuery(
            is_comparison=False,
            original_query=original_query,
            expanded_queries=expanded,
            products=[product],
            query_type='product_info'
        )


def expand_query_for_retrieval(query: str) -> ExpandedQuery:
    """
    Convenience function for query expansion

    Args:
        query: User query

    Returns:
        ExpandedQuery with expansion strategy
    """
    service = QueryExpansionService()
    return service.expand_query(query)


# Example usage
if __name__ == '__main__':
    service = QueryExpansionService()

    # Test comparison queries
    test_queries = [
        "What is the difference between Plinest Hair and Plinest Eye?",
        "Compare Newest vs Plinest",
        "Which is better: Newest or NewGyn?",
        "What is Newest?",
        "Plinest Hair indications"
    ]

    for query in test_queries:
        result = service.expand_query(query)
        print(f"\nQuery: {query}")
        print(f"Type: {result.query_type}")
        print(f"Is comparison: {result.is_comparison}")
        if result.products:
            print(f"Products: {result.products}")
        print(f"Expanded queries:")
        for i, exp in enumerate(result.expanded_queries, 1):
            print(f"  {i}. {exp}")
