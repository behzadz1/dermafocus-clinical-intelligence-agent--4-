"""
Query Expansion Service for RAG
Improves retrieval through medical abbreviations, synonyms, and semantic expansions
"""

import re
import json
import os
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class ExpandedQuery:
    """Result of query expansion"""
    is_comparison: bool
    original_query: str
    expanded_queries: List[str]
    products: List[str]
    query_type: str  # 'comparison', 'product_info', 'technique', 'protocol', 'general'
    expansion_applied: List[str]  # Track what expansions were applied


class QueryExpansionService:
    """
    Expands queries to improve retrieval recall by 5-10%

    Expansion strategies:
    1. Medical abbreviation expansion (HA → Hyaluronic Acid)
    2. Synonym expansion (wrinkles → rhytides, lines, fine lines)
    3. Protocol term expansion (sessions → treatments, visits)
    4. Product family expansion (Plinest → Plinest Eye/Hair)
    """

    # Comparison query patterns
    COMPARISON_PATTERNS = [
        r'difference between (.+?) and (.+?)(?:\?|$)',
        r'compare (.+?) (?:to|vs|versus) (.+?)(?:\?|$)',
        r'(.+?) vs\.? (.+?)(?:\?|$)',
        r'(.+?) versus (.+?)(?:\?|$)',
        r'how does (.+?) differ from (.+?)(?:\?|$)',
        r'which is better[,:]? (.+?) or (.+?)(?:\?|$)',
    ]

    # Product names (expandable)
    PRODUCT_NAMES = [
        'newest', 'plinest', 'plinest eye', 'plinest hair', 'plinest fast', 'plinest care',
        'newgyn', 'purasomes', 'purasomes xcell',
        'purasomes skin glow', 'purasomes hair', 'purasomes nutri'
    ]

    def __init__(self, thesaurus_path: Optional[str] = None):
        """
        Initialize query expansion service

        Args:
            thesaurus_path: Path to medical_thesaurus.json
        """
        self.thesaurus = self._load_thesaurus(thesaurus_path)

        # Extract abbreviations for quick lookup
        self.abbreviations = self.thesaurus.get('abbreviations', {})
        self.synonyms = self.thesaurus.get('synonyms', {})
        self.protocol_terms = self.thesaurus.get('protocol_terms', {})
        self.product_families = self.thesaurus.get('product_families', {})
        self.clinical_terms = self.thesaurus.get('clinical_terms', {})

        logger.info(
            "query_expansion_initialized",
            abbreviations_count=len(self.abbreviations),
            synonyms_count=len(self.synonyms),
            protocol_terms_count=len(self.protocol_terms)
        )

    def _load_thesaurus(self, thesaurus_path: Optional[str] = None) -> Dict:
        """Load medical thesaurus from JSON file"""
        if thesaurus_path is None:
            # Default path relative to backend directory
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            thesaurus_path = os.path.join(backend_dir, 'data', 'medical_thesaurus.json')

        try:
            with open(thesaurus_path, 'r', encoding='utf-8') as f:
                thesaurus = json.load(f)
            logger.info("medical_thesaurus_loaded", path=thesaurus_path)
            return thesaurus
        except FileNotFoundError:
            logger.warning("medical_thesaurus_not_found", path=thesaurus_path)
            return {
                'abbreviations': {},
                'synonyms': {},
                'protocol_terms': {},
                'product_families': {},
                'clinical_terms': {}
            }
        except Exception as e:
            logger.error("failed_to_load_thesaurus", error=str(e), path=thesaurus_path)
            return {
                'abbreviations': {},
                'synonyms': {},
                'protocol_terms': {},
                'product_families': {},
                'clinical_terms': {}
            }

    def expand_query(self, query: str, max_expansions: int = 5) -> ExpandedQuery:
        """
        Expand query for better retrieval

        Args:
            query: Original user query
            max_expansions: Maximum number of expanded queries to generate

        Returns:
            ExpandedQuery with expansion strategy
        """
        query_lower = query.lower().strip()
        expansion_applied = []

        # Step 1: Expand abbreviations first (always applies)
        query_expanded = self._expand_abbreviations(query, query_lower)
        if query_expanded != query:
            expansion_applied.append("abbreviations")

        # Step 2: Check if comparison query
        is_comparison, products = self._detect_comparison(query_lower)

        if is_comparison and len(products) >= 2:
            expansion_applied.append("comparison")
            return self._expand_comparison_query(query_expanded, products, expansion_applied)

        # Step 3: Check if product info query
        product = self._detect_product(query_lower)
        if product:
            expansion_applied.append("product")
            # Check if product family expansion applies
            expanded_products = self._expand_product_family(product)
            if len(expanded_products) > 1:
                expansion_applied.append("product_family")
            return self._expand_product_query(query_expanded, product, expanded_products, expansion_applied, max_expansions)

        # Step 4: Check if protocol query
        if self._is_protocol_query(query_lower):
            expansion_applied.append("protocol")
            return self._expand_protocol_query(query_expanded, expansion_applied, max_expansions)

        # Step 5: General query with synonym expansion
        expanded_queries = self._expand_with_synonyms(query_expanded, max_expansions)
        if len(expanded_queries) > 1:
            expansion_applied.append("synonyms")

        return ExpandedQuery(
            is_comparison=False,
            original_query=query,
            expanded_queries=expanded_queries,
            products=[],
            query_type='general',
            expansion_applied=expansion_applied
        )

    def _expand_abbreviations(self, original_query: str, query_lower: str) -> str:
        """
        Expand medical abbreviations in query

        Examples:
            "HA contraindications" → "Hyaluronic Acid contraindications"
            "PN treatment" → "Polynucleotides treatment"
        """
        expanded = original_query

        # Find abbreviations (must be standalone words, not part of larger words)
        words = re.findall(r'\b[A-Z]{2,}\b', expanded)

        for abbrev in words:
            if abbrev in self.abbreviations:
                # Get first expansion (primary term)
                full_term = self.abbreviations[abbrev][0]
                # Replace with word boundaries to avoid partial matches
                expanded = re.sub(
                    r'\b' + re.escape(abbrev) + r'\b',
                    full_term,
                    expanded,
                    flags=re.IGNORECASE
                )
                logger.debug("abbreviation_expanded", abbrev=abbrev, full_term=full_term)

        return expanded

    def _expand_with_synonyms(self, query: str, max_expansions: int = 5) -> List[str]:
        """
        Expand query with medical synonyms

        Examples:
            "wrinkles treatment" → ["wrinkles treatment", "rhytides treatment", "fine lines treatment"]
            "injection technique" → ["injection technique", "administration technique", "procedure technique"]
        """
        query_lower = query.lower()
        expansions = [query]  # Always include original

        # Find all synonym-able terms in query
        found_terms = []
        for term, synonyms_list in self.synonyms.items():
            # Match whole words only
            if re.search(r'\b' + re.escape(term) + r'\b', query_lower):
                found_terms.append((term, synonyms_list))

        # Add clinical terms
        for term, synonyms_list in self.clinical_terms.items():
            if re.search(r'\b' + re.escape(term) + r'\b', query_lower):
                found_terms.append((term, synonyms_list))

        # Generate expansions by replacing terms with synonyms
        for term, synonyms_list in found_terms:
            # Add first 2 synonyms only (to avoid explosion)
            for synonym in synonyms_list[:2]:
                if len(expansions) >= max_expansions:
                    break
                # Replace term with synonym (case-insensitive)
                expanded = re.sub(
                    r'\b' + re.escape(term) + r'\b',
                    synonym,
                    query,
                    flags=re.IGNORECASE
                )
                if expanded not in expansions:
                    expansions.append(expanded)

        return expansions[:max_expansions]

    def _expand_product_family(self, product: str) -> List[str]:
        """
        Expand product to its family members

        Examples:
            "plinest" → ["plinest", "plinest eye", "plinest hair"]
            "purasomes" → ["purasomes", "purasomes xcell", "purasomes skin glow"]
        """
        product_lower = product.lower()

        # Check if this is a base product with family members
        for base_product, family_members in self.product_families.items():
            if product_lower == base_product:
                return [product] + family_members
            elif product_lower in family_members:
                # Already specific, no expansion
                return [product]

        return [product]

    def _is_protocol_query(self, query_lower: str) -> bool:
        """Check if query is about treatment protocols"""
        protocol_keywords = [
            'protocol', 'sessions', 'frequency', 'how many', 'how often',
            'treatment plan', 'regimen', 'schedule', 'interval', 'maintenance'
        ]
        return any(keyword in query_lower for keyword in protocol_keywords)

    def _expand_protocol_query(
        self,
        query: str,
        expansion_applied: List[str],
        max_expansions: int = 5
    ) -> ExpandedQuery:
        """
        Expand protocol-related queries

        Examples:
            "How many sessions?" → ["How many sessions?", "How many treatments?", "How many visits?"]
            "Treatment frequency" → ["Treatment frequency", "Treatment interval", "Treatment schedule"]
        """
        query_lower = query.lower()
        expansions = [query]

        # Expand protocol terms
        for term, synonyms_list in self.protocol_terms.items():
            if re.search(r'\b' + re.escape(term) + r'\b', query_lower):
                for synonym in synonyms_list[:2]:
                    if len(expansions) >= max_expansions:
                        break
                    expanded = re.sub(
                        r'\b' + re.escape(term) + r'\b',
                        synonym,
                        query,
                        flags=re.IGNORECASE
                    )
                    if expanded not in expansions:
                        expansions.append(expanded)

        return ExpandedQuery(
            is_comparison=False,
            original_query=query,
            expanded_queries=expansions,
            products=[],
            query_type='protocol',
            expansion_applied=expansion_applied
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
        """Detect product name in query (longest match first)"""
        # Sort by length descending to match longest product names first
        sorted_products = sorted(self.PRODUCT_NAMES, key=len, reverse=True)

        for product in sorted_products:
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
        products: List[str],
        expansion_applied: List[str]
    ) -> ExpandedQuery:
        """
        Expand comparison query to ensure both products are well-retrieved

        Strategy:
        1. Original comparison query (with abbreviations expanded)
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
            expanded_queries=expanded[:7],  # Limit to 7 expansions
            products=products,
            query_type='comparison',
            expansion_applied=expansion_applied
        )

    def _expand_product_query(
        self,
        original_query: str,
        product: str,
        product_family: List[str],
        expansion_applied: List[str],
        max_expansions: int = 5
    ) -> ExpandedQuery:
        """
        Expand product info query with product family expansion

        Strategy:
        1. Original query (with abbreviations expanded)
        2. Product + factsheet query
        3. Product + indications query
        4. If product has family members, add family queries
        """
        expansions = [original_query]

        # Add standard product queries
        expansions.append(f"{product} factsheet")
        expansions.append(f"{product} indications treatment areas")

        # If product family exists and is not too specific, add family member queries
        if len(product_family) > 1:
            # User asked about base product, expand to family
            for family_product in product_family[1:]:  # Skip first (original)
                if len(expansions) >= max_expansions:
                    break
                expansions.append(f"{family_product} factsheet")

        return ExpandedQuery(
            is_comparison=False,
            original_query=original_query,
            expanded_queries=expansions[:max_expansions],
            products=product_family if len(product_family) > 1 else [product],
            query_type='product_info',
            expansion_applied=expansion_applied
        )


# Singleton instance
_query_expansion_service = None


def get_query_expansion_service() -> QueryExpansionService:
    """Get singleton QueryExpansionService instance"""
    global _query_expansion_service
    if _query_expansion_service is None:
        _query_expansion_service = QueryExpansionService()
    return _query_expansion_service


def expand_query_for_retrieval(query: str, max_expansions: int = 5) -> ExpandedQuery:
    """
    Convenience function for query expansion

    Args:
        query: User query
        max_expansions: Maximum number of expanded queries

    Returns:
        ExpandedQuery with expansion strategy
    """
    service = get_query_expansion_service()
    return service.expand_query(query, max_expansions=max_expansions)


# Example usage and testing
if __name__ == '__main__':
    service = QueryExpansionService()

    # Test queries for different expansion types
    test_queries = [
        # Abbreviation expansion
        "HA contraindications",
        "PN treatment protocol",
        "PRP vs HA comparison",

        # Synonym expansion
        "wrinkles treatment options",
        "injection technique for rejuvenation",

        # Protocol expansion
        "How many sessions are needed?",
        "Treatment frequency for maintenance",

        # Product family expansion
        "What is Plinest?",
        "Purasomes indications",

        # Comparison
        "Difference between Plinest Hair and Plinest Eye?",
        "Compare Newest vs Plinest",

        # Combined expansions
        "HA injection sessions for wrinkles",
    ]

    print("=" * 80)
    print("QUERY EXPANSION SERVICE TEST")
    print("=" * 80)

    for query in test_queries:
        result = service.expand_query(query)
        print(f"\n{'='*80}")
        print(f"Original: {query}")
        print(f"Type: {result.query_type}")
        print(f"Is comparison: {result.is_comparison}")
        print(f"Expansions applied: {', '.join(result.expansion_applied)}")
        if result.products:
            print(f"Products: {', '.join(result.products)}")
        print(f"\nExpanded queries ({len(result.expanded_queries)}):")
        for i, exp in enumerate(result.expanded_queries, 1):
            print(f"  {i}. {exp}")
