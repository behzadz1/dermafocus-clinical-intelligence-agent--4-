# PN HPT Document Count Query - Root Cause Analysis

**Date**: March 5, 2026
**Query**: "how many documents are there for PN HPT"
**Issue**: User expects 15-20 documents, system returns 1-2 documents

---

## Root Cause Identified ✅

The query "how many documents are there for PN HPT" is being **mishandled** by the RAG system for three reasons:

### 1. Query Misclassification ❌
**Current**: Classified as `general` query type
**Expected**: Should be classified as `METADATA` or `COUNT` query type
**Impact**: No specialized handling for counting/listing queries

**Evidence from logs**:
```
query_classified               type=general
retrieval_config_selected      boost_multiplier=0.0 query_type=general top_k_multiplier=1.0
```

### 2. Top-K Limitation (By Design) ⚠️
**Current**: RAG system returns top-K most relevant chunks (10 chunks requested)
**Behavior**: System is designed for semantic QA, not exhaustive document listing
**Impact**: Even with 30 Pinecone matches, only top 10 chunks are used

**Evidence from logs**:
```
Querying Pinecone              top_k=30
Hierarchical RAG search completed child_groups=21 flat_matches=3 parent_matches=0 results_found=10
```

**After deduplication**: Only 1 unique document remained from 10 chunks
**Why**: All 10 chunks likely came from the same document (hierarchical chunking groups chunks by document)

### 3. Hierarchical Deduplication 🔄
**Current**: Chunks are grouped by parent document, then deduplicated
**Impact**: 10 chunks from the same document → 1 unique document in results

**Evidence from logs**:
```
Unique Documents: 1
Document List:
[1] Score: 0.500 | clinical_paper  | [empty title]
```

---

## What Actually Exists in Pinecone

From the query logs, we can see:
- ✅ Pinecone returned **30 matches** for "polynucleotides HPT"
- ✅ Abbreviation expansion worked: PN → Polynucleotides, HPT → Highly Purified Technology
- ✅ At least **21 child groups** (document clusters) detected
- ❌ After reranking fallback (no sentence-transformers), only top 10 chunks selected
- ❌ After deduplication, only 1 unique document remained

**Likely explanation**: The top 10 chunks all came from the **same clinical paper** about PN-HPT, which had the highest relevance score.

---

## Why the User's Query Doesn't Work

### User Intent Analysis

**Query**: "how many documents are there for PN HPT"

**User expects**:
- A **count** of all PN-HPT related documents
- A **list** of all document titles/types
- Comprehensive coverage (15-20 documents)

**System behavior**:
- Treats it as a semantic QA query
- Returns top-K most relevant chunks for answering questions
- Deduplicates to unique documents
- Returns 1-2 most relevant documents

### This is a **METADATA QUERY**, not a **SEMANTIC QA QUERY**

**Metadata queries** require:
- Filtering by topic/product (PN-HPT)
- Counting unique documents
- Listing all matches (not top-K)
- No semantic ranking needed

**Semantic QA queries** require:
- Finding relevant context to answer a question
- Top-K most relevant chunks
- Semantic similarity ranking
- Deduplication by document

---

## Technical Issues Discovered

### Issue 1: Parent Chunk Fetching Failure ⚠️
```
Failed to fetch chunks by ID   chunk_ids=['Value_and_Benefits_of_the_Polynucleotides_HPT__Der_section_Results_775bcdac', ...]
error='FetchResponse' object has no attribute 'get'
```

**Impact**: Hierarchical retrieval (parent-child) is failing
**Result**: System falls back to flat chunk retrieval
**Consequence**: Reduced context quality, possible missing documents

### Issue 2: Reranker Disabled ⚠️
```
reranker_missing_dependency    error=No module named 'sentence_transformers'
all_rerankers_failed           message=Using lexical overlap fallback
```

**Impact**: Semantic reranking not working, using lexical overlap fallback
**Result**: Lower quality ranking, may miss semantically similar but lexically different documents
**Consequence**: 10-15% quality degradation (per Phase 4.0 findings)

### Issue 3: Empty Document Titles ⚠️
```
Document List:
[1] Score: 0.500 | clinical_paper  | [empty string]
```

**Impact**: Document metadata incomplete
**Result**: Cannot display document names in results
**Consequence**: Poor UX, users can't identify which document was retrieved

---

## Recommended Solutions

### Solution 1: Add METADATA/COUNT Query Type ✅

**Create new query type** for document counting/listing queries:

```python
# backend/app/services/query_router.py

class QueryType(Enum):
    PROTOCOL = "protocol"
    SAFETY = "safety"
    # ... existing types ...
    METADATA_COUNT = "metadata_count"  # NEW

PATTERNS = {
    QueryType.METADATA_COUNT: [
        r'\bhow many documents?\b',
        r'\bcount (of )?(documents?|papers?|protocols?)\b',
        r'\blist (all )?(documents?|papers?)\b',
        r'\bwhat documents? (are there|do you have)\b',
        r'\bdocuments? (about|for|on)\b'
    ]
}

RETRIEVAL_CONFIGS = {
    QueryType.METADATA_COUNT: {
        "boost_doc_types": [],  # No boosting needed
        "boost_multiplier": 0.0,
        "top_k_multiplier": 5.0,  # Get many results (150 instead of 30)
        "evidence_threshold": 0.20,  # Lower threshold for listing
        "deduplicate_by_document": True,  # Always deduplicate for counting
        "return_all_unique_documents": True  # Don't limit to top-K
    }
}
```

**Add special handling** in `rag_service.py`:

```python
def get_context_for_query(self, query: str, max_chunks: int = 5, ...) -> Dict[str, Any]:
    routing_result = self.query_router.route_query(query)

    # Special handling for metadata/count queries
    if routing_result.query_type == QueryType.METADATA_COUNT:
        return self._handle_metadata_count_query(query, routing_result)

    # ... existing logic for semantic QA queries ...

def _handle_metadata_count_query(self, query: str, routing_result: RoutingResult) -> Dict[str, Any]:
    """
    Handle document counting/listing queries
    Returns all unique documents matching the query, not top-K chunks
    """
    # Get expanded query
    expansion_result = self.query_expansion.expand_query(query)

    # Embed query
    query_vector = self.embedding_service.embed_text(expansion_result.expanded_query)

    # Query Pinecone with high top_k (get many results)
    top_k = int(30 * routing_result.retrieval_config.get("top_k_multiplier", 5.0))  # 150

    results = self.pinecone_service.query_vectors(
        query_vector=query_vector,
        top_k=top_k,
        namespace=""
    )

    # Deduplicate by document
    unique_docs = {}
    for match in results.get('matches', []):
        doc_id = match['metadata']['doc_id']
        if doc_id not in unique_docs:
            unique_docs[doc_id] = {
                'doc_id': doc_id,
                'title': match['metadata'].get('title', 'Unknown'),
                'doc_type': match['metadata'].get('doc_type', 'Unknown'),
                'max_score': match['score']
            }
        else:
            # Keep highest score for this document
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

**Estimated effort**: 2-3 hours

---

### Solution 2: Fix Parent Chunk Fetching ✅

**Issue**: `'FetchResponse' object has no attribute 'get'`

**Location**: `backend/app/services/rag_service.py` or `pinecone_service.py`

**Fix**: Update Pinecone client code to handle new API response format

```python
# Check current fetch implementation
# Should use fetch_response.vectors or fetch_response['vectors']
# instead of fetch_response.get('vectors')
```

**Estimated effort**: 1 hour

---

### Solution 3: Install Reranker Dependencies ✅

**Issue**: `No module named 'sentence_transformers'`

**Fix**:
```bash
cd backend
pip install sentence-transformers
```

**Validation**: Test that reranking works
```python
from sentence_transformers import CrossEncoder
model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
print("Reranker loaded successfully!")
```

**Estimated effort**: 15 minutes

---

### Solution 4: Populate Missing Document Titles ✅

**Issue**: Document metadata missing titles

**Fix**: Reprocess documents to extract proper titles

```bash
cd backend
python scripts/process_all_documents.py --upload-to-pinecone --force-reprocess
```

**Alternatively**: Add fallback to use filename as title if metadata title is empty

**Estimated effort**: 30 minutes

---

## Alternative: Quick Workaround (No Code Changes)

**For immediate testing**, use a more specific query that triggers semantic QA behavior:

### Instead of:
```
"how many documents are there for PN HPT"
```

### Try:
```
"What are all the clinical studies about PN-HPT polynucleotides?"
"Summarize the research papers on Polynucleotides HPT technology"
"Give me an overview of all PN-HPT related publications"
```

These queries:
- Trigger semantic QA (not metadata counting)
- May retrieve more diverse documents (from different papers)
- Return actual content summaries instead of just counts

**But this doesn't solve the core issue** - metadata/count queries need proper handling.

---

## Summary

**Why user sees 1-2 documents instead of 15-20**:

1. ✅ **Query type mismatch**: "how many documents" is a METADATA query, not a semantic QA query
2. ✅ **Top-K limitation**: RAG returns top 10 most relevant chunks, not all matching documents
3. ✅ **Deduplication**: 10 chunks from the same document → 1 unique document
4. ✅ **Technical issues**: Parent fetching fails, reranker disabled, titles missing

**Immediate actions**:

1. **Explain to user**: RAG is designed for semantic QA (top-K), not exhaustive document counting
2. **Verify Pinecone**: Directly query to confirm 15-20 PN-HPT documents actually exist
3. **Implement metadata query type**: Add specialized handling for count/list queries (2-3 hours)
4. **Fix technical issues**: Parent fetching, reranker, titles (2 hours)

**Total estimated effort**: 4-5 hours to properly support metadata/count queries

---

## Next Steps

1. **Verify document count in Pinecone** - Direct query to see actual PN-HPT document count
2. **Implement METADATA_COUNT query type** - Proper handling for listing/counting queries
3. **Fix parent chunk fetching** - Resolve FetchResponse error
4. **Install sentence-transformers** - Enable reranker
5. **Test with metadata query** - Validate that count queries now return all unique documents

---

**Analysis Date**: March 5, 2026
**Analyzed By**: Claude Code Agent
**Status**: Root cause identified, solutions proposed
