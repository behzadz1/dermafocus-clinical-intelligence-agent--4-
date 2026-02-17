"""
Query Router Service
Classifies queries and routes to specialized retrievers for optimal performance
"""

import re
from typing import Dict, Any, Optional, List
from enum import Enum
import structlog

logger = structlog.get_logger()


class QueryType(Enum):
    """Types of queries with specialized handling"""
    PROTOCOL = "protocol"                # "What is the Newest protocol?"
    SAFETY = "safety"                    # "What are contraindications?"
    TECHNIQUE = "technique"              # "How do you inject Plinest Eye?"
    COMPARISON = "comparison"            # "Compare Newest vs Plinest"
    PRODUCT_INFO = "product_info"        # "What is Plinest?"
    INDICATION = "indication"            # "What is Newest used for?"
    COMPOSITION = "composition"          # "What does Newest contain?"
    CLINICAL_EVIDENCE = "clinical_evidence"  # "What studies support Newest?"
    GENERAL = "general"                  # Fallback for unclassified


class QueryRouter:
    """
    Routes queries to specialized retrieval strategies based on query type
    """

    # Query type detection patterns (checked in priority order)
    PATTERNS = {
        QueryType.SAFETY: [
            # Check safety FIRST to avoid conflicts with indication patterns
            r'\bcontraindication[s]?\b',
            r'\bside effect[s]?\b',
            r'\badverse\b',
            r'\bsafety\b',
            r'\bprecaution[s]?\b',
            r'\bwarning[s]?\b',
            r'\b(?:risk|danger|avoid|not use|should not)\b',
            r'\b(?:safe|unsafe|caution)\b',
            r'\b(?:pregnancy|pregnant|breastfeeding)\b',  # Pregnancy is usually contraindication
        ],
        QueryType.PROTOCOL: [
            r'\bprotocol[s]?\b',
            r'\bprocedure[s]?\b',
            r'\bstep[s]?\b',
            r'\btreatment plan[s]?\b',
            r'\badministration\b',
            r'\badminister(?:ing|ed)?\b',
            r'\bhow to (?:use|apply)\b',
            r'\bhow many sessions?\b',
            r'\bfrequency\b',
            r'\bschedule\b',
            r'\btiming\b',
        ],
        QueryType.TECHNIQUE: [
            r'\btechnique[s]?\b',
            r'\bmethod[s]?\b',
            r'\bhow to inject\b',
            r'\binjection\b',
            r'\bneedle\b',
            r'\bdepth\b',
            r'\bangle\b',
            r'\bwhere to inject\b',
            r'\binjection point\b',
            r'\binjection site\b',
        ],
        QueryType.COMPARISON: [
            r'\bcompare\b',
            r'\bcomparison\b',
            r'\bversus\b',
            r'\bvs\.?\b',
            r'\bdiffer(?:ence|ent)?\b',
            r'\bbetter\b',
            r'\bwhich one\b',
            r'\bchoose between\b',
            r'\bsimilar\b',
            r'\balike\b',
        ],
        QueryType.CLINICAL_EVIDENCE: [
            # Check before PRODUCT_INFO to catch "studies" queries
            r'\bstud(?:y|ies)\b',
            r'\bresearch\b',
            r'\btrial[s]?\b',
            r'\bclinical evidence\b',
            r'\bclinical trial[s]?\b',
            r'\bprove[n]?\b',
            r'\befficacy\b',
            r'\beffectiveness\b',
            r'\bresult[s]?\b',
            r'\boutcome[s]?\b',
        ],
        QueryType.COMPOSITION: [
            r'\bcomposition\b',
            r'\bingredient[s]?\b',
            r'\bcomponent[s]?\b',
            r'\bcontain[s]?\b',
            r'\bmade of\b',
            r'\bwhat (?:is|are) in\b',
            r'\bformulation\b',
            r'\bformula\b',
        ],
        QueryType.INDICATION: [
            # IMPORTANT: Check after SAFETY to avoid "contraindication" matching "indication"
            # Use word boundaries carefully
            r'\bindication[s]?\b(?!.*contraindication)',  # Negative lookahead
            r'\bused for\b',
            r'\btreat(?:ment area)?\b(?!ment plan)',  # Avoid "treatment plan" (protocol)
            r'\bsuitable for\b',
            r'\bappropriate for\b',
            r'\brecommended for\b',
        ],
        QueryType.PRODUCT_INFO: [
            r'\bwhat is\b',
            r'\btell me about\b',
            r'\bexplain\b',
            r'\bdescribe\b',
        ],
    }

    # Type-specific retrieval parameters (all configs have same structure)
    RETRIEVAL_CONFIGS = {
        QueryType.PROTOCOL: {
            "boost_doc_types": ["protocol", "factsheet"],
            "boost_multiplier": 0.15,
            "prefer_sections": ["protocol", "treatment", "administration", "procedure"],
            "prefer_chunk_types": [],
            "top_k_multiplier": 1.2  # Retrieve 20% more for protocols
        },
        QueryType.SAFETY: {
            "boost_doc_types": ["factsheet", "clinical_paper"],
            "boost_multiplier": 0.20,  # Strong boost for safety queries
            "prefer_sections": ["contraindication", "safety", "precaution", "adverse", "warning"],
            "prefer_chunk_types": [],
            "top_k_multiplier": 1.0
        },
        QueryType.TECHNIQUE: {
            "boost_doc_types": ["protocol"],
            "boost_multiplier": 0.18,
            "prefer_sections": ["technique", "injection", "procedure", "method"],
            "prefer_chunk_types": ["image", "detail"],  # Images + detailed instructions
            "top_k_multiplier": 1.3  # More chunks for technique details
        },
        QueryType.COMPARISON: {
            "boost_doc_types": ["factsheet"],
            "boost_multiplier": 0.25,  # Already tuned in Phase 1.3
            "prefer_sections": ["indication", "composition", "protocol"],
            "prefer_chunk_types": [],
            "top_k_multiplier": 1.5  # Need more context for comparisons
        },
        QueryType.INDICATION: {
            "boost_doc_types": ["factsheet", "case_study"],
            "boost_multiplier": 0.12,
            "prefer_sections": ["indication", "treatment area", "use"],
            "prefer_chunk_types": [],
            "top_k_multiplier": 1.1
        },
        QueryType.COMPOSITION: {
            "boost_doc_types": ["factsheet"],
            "boost_multiplier": 0.15,
            "prefer_sections": ["composition", "ingredient", "formulation"],
            "prefer_chunk_types": ["table"],  # Composition often in tables
            "top_k_multiplier": 1.0
        },
        QueryType.CLINICAL_EVIDENCE: {
            "boost_doc_types": ["clinical_paper", "case_study"],
            "boost_multiplier": 0.20,
            "prefer_sections": ["result", "outcome", "study", "efficacy"],
            "prefer_chunk_types": [],
            "top_k_multiplier": 1.2
        },
        QueryType.PRODUCT_INFO: {
            "boost_doc_types": ["factsheet"],
            "boost_multiplier": 0.10,
            "prefer_sections": [],  # Accept all sections
            "prefer_chunk_types": [],
            "top_k_multiplier": 1.0
        },
        QueryType.GENERAL: {
            "boost_doc_types": [],
            "boost_multiplier": 0.0,
            "prefer_sections": [],
            "prefer_chunk_types": [],
            "top_k_multiplier": 1.0
        }
    }

    def classify_query(self, query: str) -> QueryType:
        """
        Classify query into a specific type

        Args:
            query: User query text

        Returns:
            QueryType enum value
        """
        query_lower = query.lower()

        # Check patterns in priority order to avoid classification conflicts
        # IMPORTANT: Safety MUST be checked before Indication to catch "contraindication"

        # 1. Safety queries (highest priority - critical, must check first)
        if self._matches_patterns(query_lower, self.PATTERNS[QueryType.SAFETY]):
            logger.debug("query_classified", type="safety")
            return QueryType.SAFETY

        # 2. Protocol queries (high priority - specific)
        if self._matches_patterns(query_lower, self.PATTERNS[QueryType.PROTOCOL]):
            logger.debug("query_classified", type="protocol")
            return QueryType.PROTOCOL

        # 3. Technique queries
        if self._matches_patterns(query_lower, self.PATTERNS[QueryType.TECHNIQUE]):
            logger.debug("query_classified", type="technique")
            return QueryType.TECHNIQUE

        # 4. Comparison queries (already well-handled)
        if self._matches_patterns(query_lower, self.PATTERNS[QueryType.COMPARISON]):
            logger.debug("query_classified", type="comparison")
            return QueryType.COMPARISON

        # 5. Clinical evidence queries (check before PRODUCT_INFO)
        if self._matches_patterns(query_lower, self.PATTERNS[QueryType.CLINICAL_EVIDENCE]):
            logger.debug("query_classified", type="clinical_evidence")
            return QueryType.CLINICAL_EVIDENCE

        # 6. Composition queries
        if self._matches_patterns(query_lower, self.PATTERNS[QueryType.COMPOSITION]):
            logger.debug("query_classified", type="composition")
            return QueryType.COMPOSITION

        # 7. Indication queries (after SAFETY to avoid conflicts)
        if self._matches_patterns(query_lower, self.PATTERNS[QueryType.INDICATION]):
            logger.debug("query_classified", type="indication")
            return QueryType.INDICATION

        # 8. Product info queries (broad, near the end)
        if self._matches_patterns(query_lower, self.PATTERNS[QueryType.PRODUCT_INFO]):
            logger.debug("query_classified", type="product_info")
            return QueryType.PRODUCT_INFO

        # 9. Default: general (fallback)
        logger.debug("query_classified", type="general")
        return QueryType.GENERAL

    def get_retrieval_config(self, query_type: QueryType) -> Dict[str, Any]:
        """
        Get retrieval configuration for a query type

        Args:
            query_type: Classified query type

        Returns:
            Configuration dictionary with boosting and filtering parameters
        """
        config = self.RETRIEVAL_CONFIGS.get(query_type, self.RETRIEVAL_CONFIGS[QueryType.GENERAL])

        logger.debug(
            "retrieval_config_selected",
            query_type=query_type.value,
            boost_multiplier=config["boost_multiplier"],
            top_k_multiplier=config["top_k_multiplier"]
        )

        return config.copy()

    def route_query(self, query: str) -> Dict[str, Any]:
        """
        Classify query and return routing information

        Args:
            query: User query text

        Returns:
            Dictionary with:
            - query_type: QueryType enum
            - config: Retrieval configuration
            - metadata: Additional routing metadata
        """
        # Classify query
        query_type = self.classify_query(query)

        # Get config
        config = self.get_retrieval_config(query_type)

        # Add metadata
        metadata = {
            "query_type": query_type.value,
            "specialized_routing": query_type != QueryType.GENERAL
        }

        logger.info(
            "query_routed",
            query_type=query_type.value,
            boost_multiplier=config["boost_multiplier"],
            specialized=metadata["specialized_routing"]
        )

        return {
            "query_type": query_type,
            "config": config,
            "metadata": metadata
        }

    @staticmethod
    def _matches_patterns(text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern in the list"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False


# Singleton instance
_query_router = None


def get_query_router() -> QueryRouter:
    """Get singleton QueryRouter instance"""
    global _query_router
    if _query_router is None:
        _query_router = QueryRouter()
    return _query_router
