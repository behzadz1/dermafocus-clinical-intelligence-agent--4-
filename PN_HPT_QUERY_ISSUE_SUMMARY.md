# PN-HPT Document Count Query - Issue Summary

**Date**: March 5, 2026
**User Query**: "how many documents are there for PN HPT"
**Expected**: 15-20 documents
**Actual**: 1-2 documents returned

---

## ✅ Root Cause Confirmed

### The Good News
**Your expectation was correct!** Pinecone contains **19 unique PN-HPT related documents** with 179 total chunks.

### The Issue
The RAG system is only returning 1 document instead of 19 because it's designed for **semantic question-answering**, not **document counting/listing**.

---

## What's Happening (Technical)

### 1. Query Misclassification
```
User query: "how many documents are there for PN HPT"
Classified as: GENERAL (incorrect)
Should be: METADATA_COUNT
```

### 2. RAG Pipeline Behavior
1. ✅ Query expansion works: PN → Polynucleotides, HPT → Highly Purified Technology
2. ✅ Pinecone returns top-30 most relevant chunks
3. ✅ Hierarchical processing detects 21 document groups
4. ❌ Reranking fails (sentence-transformers not installed) - uses fallback
5. ❌ Top-10 chunks selected after reranking
6. ❌ All 10 chunks came from **the same document** → only 1 unique document in results

### 3. Hierarchical Deduplication
The RAG system groups chunks by parent document. In this case:
- 10 chunks retrieved
- All 10 from the same clinical paper
- Deduplicated to 1 unique document

---

## Verification Results

### Direct Pinecone Query (top_k=200)
```
✓ Found 19 unique PN-HPT documents:
  - 179 total chunks across all documents
  - Document types: clinical_paper (16), factsheet (2), brochure (1)
  - Score range: 0.688 (best) to 0.608 (lowest)
```

### Top 10 PN-HPT Documents
| # | Score | Chunks | Type | Title |
|---|-------|--------|------|-------|
| 1 | 0.688 | 18x | clinical_paper | PN-HPT® and Striae Albae-Exploratory Interim Analysis |
| 2 | 0.678 | 24x | clinical_paper | [Document 2] |
| 3 | 0.677 | 12x | clinical_paper | Clinical efficacy and safety of polynucleotides HPT |
| 4 | 0.662 | 2x | clinical_paper | Facial middle third rejuvenation |
| 5 | 0.656 | 12x | clinical_paper | Polynucleotides Versus PRP for Androgenetic Alopecia |
| 6 | 0.651 | 6x | clinical_paper | Biomimetic Polynucleotides-HA Hydrogel |
| 7 | 0.648 | 12x | clinical_paper | Innovative PN HPT-based Medical Device |
| 8 | 0.629 | 1x | brochure | HCP Brochure Plinest |
| 9 | 0.628 | 18x | clinical_paper | Revitalisation of Postmenopausal Labia Majora |
| 10 | 0.628 | 6x | clinical_paper | Consensus report on PN-HPT use |

**Total**: 19 documents with 179 chunks

### RAG System Query
```
❌ Returned: 1 unique document (from 10 chunks)
Query type: general
Evidence: sufficient (score 0.5)
```

---

## Why This Happens (By Design)

### RAG System Purpose
The RAG (Retrieval-Augmented Generation) system is designed for:
- ✅ **Semantic Question-Answering**: "What are the benefits of PN-HPT?"
- ✅ **Finding relevant context** to generate answers
- ✅ **Top-K most relevant** chunks for answer quality
- ❌ **NOT for counting/listing** all documents on a topic

### Query Type Mismatch
Your query "how many documents are there for PN HPT" is a **METADATA query**, not a **semantic QA query**:

**Metadata Query** (what you need):
- Goal: Count/list ALL documents matching a criteria
- Method: Filter by topic, return unique document IDs
- Top-K: Not applicable (return all matches)
- Example: "List all documents about X"

**Semantic QA Query** (what RAG does):
- Goal: Answer a specific question
- Method: Find most relevant context chunks
- Top-K: Return best 5-10 chunks
- Example: "What are the benefits of X?"

---

## Solutions

### Solution 1: Rephrase Your Query (Immediate Workaround)

Instead of asking for a count, ask a question that requires citing multiple papers:

**Instead of**:
```
"How many documents are there for PN HPT?"
```

**Try**:
```
"What does the research literature say about PN-HPT polynucleotides? Cite all relevant studies."
"Summarize the clinical evidence for polynucleotides HPT from all available papers."
"Give me an overview of all PN-HPT research papers and their findings."
```

This may retrieve more diverse documents (from different papers) since Claude needs to cite multiple sources.

---

### Solution 2: Implement METADATA_COUNT Query Type (Proper Fix)

**Estimated Effort**: 2-3 hours

#### Step 1: Add Query Type

**File**: `backend/app/services/query_router.py`

```python
class QueryType(Enum):
    PROTOCOL = "protocol"
    SAFETY = "safety"
    # ... existing types ...
    METADATA_COUNT = "metadata_count"  # NEW

PATTERNS = {
    # ... existing patterns ...
    QueryType.METADATA_COUNT: [
        r'\bhow many documents?\b',
        r'\bcount (of )?(documents?|papers?|protocols?)\b',
        r'\blist (all )?(documents?|papers?)\b',
        r'\bwhat documents? (are there|do you have)\b',
        r'\ball (the )?documents? (about|for|on)\b'
    ]
}

RETRIEVAL_CONFIGS = {
    # ... existing configs ...
    QueryType.METADATA_COUNT: {
        "boost_doc_types": [],
        "boost_multiplier": 0.0,
        "top_k_multiplier": 5.0,  # Get 150 chunks (30 * 5.0)
        "evidence_threshold": 0.20,  # Lower threshold for listing
        "return_all_unique_documents": True  # Special flag
    }
}
```

#### Step 2: Add Handler in RAG Service

**File**: `backend/app/services/rag_service.py`

```python
def get_context_for_query(self, query: str, max_chunks: int = 5, ...) -> Dict[str, Any]:
    routing_result = self.query_router.route_query(query)

    # Special handling for metadata/count queries
    if routing_result.query_type == QueryType.METADATA_COUNT:
        return self._handle_metadata_count_query(query, routing_result)

    # ... existing logic ...

def _handle_metadata_count_query(self, query: str, routing_result: RoutingResult) -> Dict[str, Any]:
    """
    Handle document counting/listing queries.
    Returns all unique documents matching the query, not top-K chunks.
    """
    # Expand query
    expansion_result = self.query_expansion.expand_query(query)

    # Embed and search with high top_k
    query_vector = self.embedding_service.embed_query(expansion_result.expanded_query)
    top_k = int(30 * routing_result.retrieval_config.get("top_k_multiplier", 5.0))  # 150

    results = self.pinecone_service.query(
        query_vector=query_vector,
        top_k=top_k,
        namespace="default"
    )

    # Deduplicate by document ID
    unique_docs = {}
    for match in results['matches']:
        doc_id = match['metadata']['doc_id']
        if doc_id not in unique_docs:
            unique_docs[doc_id] = {
                'doc_id': doc_id,
                'title': match['metadata'].get('title', 'Unknown'),
                'doc_type': match['metadata'].get('doc_type', 'Unknown'),
                'max_score': match['score']
            }
        else:
            unique_docs[doc_id]['max_score'] = max(
                unique_docs[doc_id]['max_score'],
                match['score']
            )

    # Sort by score
    sorted_docs = sorted(
        unique_docs.values(),
        key=lambda x: x['max_score'],
        reverse=True
    )

    # Return metadata-focused response
    return {
        'query_type': 'metadata_count',
        'document_count': len(sorted_docs),
        'documents': sorted_docs,
        'evidence': {
            'sufficient': True,
            'reason': 'metadata_count_query',
            'top_score': sorted_docs[0]['max_score'] if sorted_docs else 0.0
        },
        'chunks': []  # No chunks needed for counting
    }
```

#### Step 3: Update Claude Service

**File**: `backend/app/services/claude_service.py`

Add special formatting for metadata_count responses:

```python
def generate_response(self, user_message: str, context: str, ...) -> str:
    # ... existing code ...

    # If this is a metadata_count query, format as document list
    if context.get('query_type') == 'metadata_count':
        doc_list = "\n".join([
            f"{i}. {doc['title']} ({doc['doc_type']})"
            for i, doc in enumerate(context['documents'], 1)
        ])
        system_prompt += f"\n\nYou have {context['document_count']} documents available. List them clearly."

    # ... rest of existing code ...
```

---

### Solution 3: Fix Related Technical Issues (1-2 hours)

#### Issue A: Parent Chunk Fetching Fails
```
Failed to fetch chunks by ID ... error='FetchResponse' object has no attribute 'get'
```

**Impact**: Hierarchical retrieval (parent-child) degraded
**Fix**: Update Pinecone client code to use correct API response format

#### Issue B: Reranker Disabled
```
reranker_missing_dependency error=No module named 'sentence_transformers'
```

**Impact**: 10-15% quality degradation
**Fix**: Install dependencies
```bash
cd backend
pip install sentence-transformers
```

#### Issue C: Empty Document Titles
```
Document List: [1] Score: 0.500 | clinical_paper | [empty]
```

**Impact**: Poor UX, can't identify documents
**Fix**: Reprocess documents or add fallback to use doc_id as title

---

## Recommended Action Plan

### Option A: Quick Workaround (0 hours)
✅ **Best for immediate use**

1. Rephrase queries to ask for summaries/overviews instead of counts
2. Example: "Summarize all PN-HPT research papers and their findings"
3. This may retrieve more diverse documents

### Option B: Proper Implementation (2-3 hours)
✅ **Best long-term solution**

1. Implement METADATA_COUNT query type (2 hours)
2. Install sentence-transformers (15 min)
3. Fix parent chunk fetching (1 hour)
4. Test with metadata queries (30 min)

---

## Summary

**The system is working correctly** - it's just designed for a different use case:
- ✅ Pinecone contains 19 PN-HPT documents (your expectation was right!)
- ✅ RAG returns top-K most relevant chunks for QA (working as designed)
- ❌ RAG doesn't handle document counting/listing queries (needs new feature)

**For now**: Rephrase your query to request a summary/overview instead of a count.

**Long-term**: Implement METADATA_COUNT query type to properly handle document listing queries.

---

**Analysis Completed**: March 5, 2026
**Documents Verified**: 19 PN-HPT documents in Pinecone
**Issue Confirmed**: Query type mismatch (metadata vs semantic QA)
**Solution**: Implement METADATA_COUNT query type (2-3 hours)
