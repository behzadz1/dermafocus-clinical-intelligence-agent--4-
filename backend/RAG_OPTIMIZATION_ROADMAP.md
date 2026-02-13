# RAG Optimization Roadmap: Achieving 85%+ Confidence

**Goal**: Get confidence scores above 85% for EVERY query type
**Current State**: 48-88% (highly variable)
**Target**: 85%+ consistent performance

---

## 📊 Current Performance Analysis

| Query Type | Current Score | Gap to 85% | Priority |
|------------|--------------|------------|----------|
| **Protocol details** | 48.0% | **+37.0%** | 🔴 CRITICAL |
| **Comparisons** | 50.7% | **+34.3%** | 🔴 CRITICAL |
| **Safety/Contraindications** | 71.6% | +13.4% | 🟡 HIGH |
| **Product info** | 75.4% | +9.6% | 🟡 HIGH |
| **Technique queries** | 79.0% | +6.0% | 🟢 MEDIUM |
| **Specific indications** | 88.5% | ✅ GOOD | ✅ MAINTAIN |

**Overall Status**: ⚠️ NOT production-ready for 85%+ standard

---

## 🎯 Improvement Strategy: 10 Proven Techniques

### **Phase 1: Quick Wins (1-2 weeks) - Expected +10-15% improvement**

#### 1. **Fine-Tune Embeddings** 🔴 HIGHEST IMPACT
**Problem**: Generic OpenAI embeddings not optimized for dermatology domain
**Solution**: Fine-tune embedding model on your specific documents

**Implementation**:
```python
# Create training data from your documents
training_pairs = [
    ("What is Newest?", "Newest® Factsheet chunk 1"),
    ("perioral rejuvenation protocol", "Perioral protocol chunk 3"),
    # ... 100-1000 query-document pairs
]

# Fine-tune with OpenAI
from openai import OpenAI
client = OpenAI()

# Prepare fine-tuning dataset
with open("training_data.jsonl", "w") as f:
    for query, doc in training_pairs:
        f.write(json.dumps({
            "messages": [
                {"role": "user", "content": query},
                {"role": "assistant", "content": doc}
            ]
        }) + "\n")

# Fine-tune
job = client.fine_tuning.jobs.create(
    training_file="file-abc123",
    model="text-embedding-3-small"
)
```

**Expected Impact**: +8-12% confidence improvement
**Cost**: ~$50-200 for fine-tuning
**Time**: 2-3 days

---

#### 2. **Reranking Layer** 🔴 HIGH IMPACT
**Problem**: Initial retrieval misses best matches, ranks them poorly
**Solution**: Add neural reranker (Cohere, Jina, or cross-encoder)

**Implementation**:
```python
from app.services.reranker_service import get_reranker_service

def search_with_reranking(query: str, top_k: int = 5):
    # Initial retrieval (get more candidates)
    candidates = rag.search(query, top_k=50)

    # Rerank with neural model
    reranker = get_reranker_service()
    reranked = reranker.rerank(
        query=query,
        documents=[c['text'] for c in candidates],
        top_n=top_k
    )

    # Return top reranked results
    return [candidates[r.index] for r in reranked]
```

**Models to try**:
- Cohere rerank-english-v3.0 (best, paid)
- Jina AI reranker (good, free tier)
- sentence-transformers/ms-marco-MiniLM-L-12-v2 (local)

**Expected Impact**: +5-10% confidence
**Cost**: $0-100/month depending on volume
**Time**: 1-2 days

---

#### 3. **Query Classification & Routing** 🟡 MEDIUM IMPACT
**Problem**: Different query types need different retrieval strategies
**Solution**: Classify query → route to specialized retrieval

**Implementation**:
```python
class QueryRouter:
    def classify_and_route(self, query: str):
        query_type = self.classify(query)  # LLM or rules

        if query_type == "protocol_detail":
            # Use metadata filter for protocols
            return rag.search(query, doc_type="protocol", top_k=10)

        elif query_type == "safety":
            # Expand with safety terms, prioritize factsheets
            expanded = query + " contraindications warnings precautions"
            results = rag.search(expanded, top_k=20)
            # Boost factsheets
            for r in results:
                if "factsheet" in r['metadata'].get('doc_id', '').lower():
                    r['score'] *= 1.3
            return sorted(results, key=lambda x: x['score'], reverse=True)[:10]

        elif query_type == "comparison":
            # Already handled by query_expansion
            return rag.search(query, top_k=15)

        else:
            return rag.search(query, top_k=10)
```

**Expected Impact**: +3-7% confidence
**Time**: 2-3 days

---

#### 4. **Improve Chunking for Protocol Queries** 🔴 CRITICAL for 48% gap
**Problem**: Protocol details (sessions, dosage) split across chunks
**Solution**: Semantic chunking + keep protocol sections together

**Current Issue**:
```
Chunk 1: "Plinest Hair treatment..."
Chunk 2: "...sessions recommended..."  ← SPLIT!
Chunk 3: "...every 2-3 weeks for..."
```

**Better Approach**:
```python
class ProtocolAwareChunker:
    def chunk_protocol(self, text):
        # Detect protocol sections
        sections = self.extract_protocol_sections(text)

        chunks = []
        for section in sections:
            # Keep complete protocol info together
            if len(section) < 800:  # Fits in one chunk
                chunks.append(section)
            else:
                # Split but repeat protocol header
                sub_chunks = self.split_with_context(section)
                chunks.extend(sub_chunks)

        return chunks
```

**Expected Impact**: +15-20% for protocol queries (48% → 68%+)
**Time**: 3-4 days

---

### **Phase 2: Medium-Term (2-4 weeks) - Expected +10-12% improvement**

#### 5. **Hybrid Search (BM25 + Semantic)** 🟡 HIGH IMPACT
**Problem**: Pure semantic search misses exact keyword matches
**Solution**: Combine BM25 (keyword) + vector search

**You already have this partially!** Just needs tuning:
```python
# In rag_service.py - adjust weights
def hybrid_search(query, top_k=10):
    # Semantic search
    vector_results = pinecone.query(embedding, top_k=20)

    # BM25 search
    bm25_results = lexical_index.search(query, top_k=20)

    # Combine with tuned weights
    combined = self.rrf_fusion(
        vector_results,
        bm25_results,
        vector_weight=0.7,  # Tune this!
        bm25_weight=0.3      # Tune this!
    )

    return combined[:top_k]
```

**Tuning Strategy**:
- Protocol queries: More BM25 weight (0.5/0.5) - exact terms matter
- Conceptual queries: More vector weight (0.8/0.2)

**Expected Impact**: +4-8% confidence
**Time**: 2-3 days to tune weights

---

#### 6. **Metadata-Driven Retrieval** 🟡 MEDIUM IMPACT
**Problem**: Not using rich metadata (anatomy, product, treatment)
**Solution**: Combine semantic search + metadata filtering

**Implementation**:
```python
def smart_search(query: str):
    # Extract entities from query
    product = extract_product(query)  # "Newest"
    anatomy = extract_anatomy(query)  # "perioral"
    query_type = classify_query(query)  # "protocol"

    # Build metadata filter
    metadata_filter = {}
    if product:
        metadata_filter['product'] = product
    if anatomy:
        metadata_filter['anatomy'] = anatomy

    # Search with filter
    results = rag.search(query, metadata_filter=metadata_filter, top_k=20)

    # If too few results, broaden search
    if len(results) < 5:
        results = rag.search(query, top_k=20)  # No filter

    # Boost documents matching query type
    if query_type == "protocol":
        for r in results:
            if r['metadata'].get('doc_type') == 'protocol':
                r['score'] *= 1.25

    return sorted(results, key=lambda x: x['score'], reverse=True)[:10]
```

**Expected Impact**: +5-8% confidence
**Time**: 3-4 days

---

#### 7. **Document Quality & Consolidation** 🟡 HIGH IMPACT
**Problem**: Information fragmented, factsheets incomplete
**Solution**: Create consolidated master documents

**Approach**:
```
backend/data/consolidated/
├── newest_complete_profile.md       # ALL Newest info in one place
├── plinest_hair_complete.md         # ALL Plinest Hair info
├── plinest_eye_complete.md
└── ...

Content Structure:
# Newest® - Complete Clinical Profile

## Composition (from factsheet + studies)
- PN-HPT: 20mg/2ml
- HA: 20mg/2ml
- Mannitol: 200mM/L

## Indications (synthesized from ALL sources)
- Face, neck, décolleté (factsheet)
- Perioral (protocol XYZ, clinical study A)
- Hand rejuvenation (case study B)
- Periocular (clinical study A)

## Protocols by Indication
### Face/Neck/Décolleté
- Dosage: 2ml intradermal
- Frequency: Every 2-3 weeks
- Sessions: 3-4 total
- Technique: Microdroplet or linear retrograde

### Perioral
- [Complete protocol from protocol doc]

[etc - comprehensive synthesis]
```

**Expected Impact**: +8-12% confidence (single source of truth)
**Time**: 1 week to create, ongoing maintenance

---

### **Phase 3: Advanced (1-2 months) - Expected +8-10% improvement**

#### 8. **Contextual Compression** 🟢 MEDIUM IMPACT
**Problem**: Retrieved context has irrelevant parts diluting answer
**Solution**: Use LLM to extract only relevant parts

**Implementation**:
```python
async def compress_context(query: str, retrieved_docs: List[str]):
    """Extract only query-relevant parts from each document"""
    compressed = []

    for doc in retrieved_docs:
        # Use fast model (Haiku) to extract relevant sentences
        prompt = f"""Extract ONLY the sentences from this document that are relevant to: "{query}"

Document:
{doc}

Return only the relevant sentences, maintaining original wording."""

        relevant = await claude.generate_response(
            prompt,
            model="claude-haiku"
        )
        compressed.append(relevant)

    return compressed
```

**Expected Impact**: +3-5% confidence (less noise)
**Cost**: ~2x API calls, but using cheap Haiku
**Time**: 2-3 days

---

#### 9. **Query Expansion with LLM** 🟢 MEDIUM IMPACT
**Problem**: User query may not match document phrasing
**Solution**: Generate multiple query variations

**Implementation**:
```python
async def expand_query_llm(query: str):
    """Generate semantically similar query variations"""
    prompt = f"""Generate 3 alternative phrasings of this medical query:
"{query}"

Return variations that might match different document styles (clinical, technical, patient-friendly)."""

    variations = await claude.generate_response(prompt)

    # Search with all variations
    all_results = []
    for variant in [query] + variations:
        results = rag.search(variant, top_k=10)
        all_results.extend(results)

    # Deduplicate and rerank
    unique_results = deduplicate_by_chunk_id(all_results)
    return rank_by_frequency_and_score(unique_results)[:10]
```

**Expected Impact**: +3-6% confidence
**Time**: 2-3 days

---

#### 10. **Answer Validation & Self-Critique** 🟢 HIGH QUALITY
**Problem**: No check if answer actually addresses query
**Solution**: LLM validates its own answer

**Implementation**:
```python
async def validated_answer(query: str, answer: str, context: str):
    """Validate answer quality and confidence"""

    validation_prompt = f"""Evaluate this answer:

Query: {query}
Answer: {answer}
Context used: {context[:1000]}...

Rate 1-10 on:
1. Completeness: Does it fully answer the question?
2. Accuracy: Is it supported by the context?
3. Confidence: How certain are you?

If score < 7, explain what's missing and suggest improvement."""

    validation = await claude.generate_response(validation_prompt)

    # If low confidence, try different retrieval strategy
    if validation.confidence < 7:
        # Retry with expanded query
        improved_answer = await retry_with_strategy(query)
        return improved_answer

    return answer
```

**Expected Impact**: Prevents low-quality answers, maintains 85%+ standard
**Time**: 3-4 days

---

## 📊 Expected Cumulative Impact

| Phase | Improvements | Expected Gain | Cumulative | Timeline |
|-------|-------------|---------------|------------|----------|
| **Baseline** | Current system | - | 48-78% | Now |
| **Phase 1** | Fine-tuning, Reranking, Routing, Chunking | **+25-35%** | **73-85%** | 1-2 weeks |
| **Phase 2** | Hybrid search, Metadata, Consolidation | **+10-12%** | **83-90%** | 2-4 weeks |
| **Phase 3** | Compression, Expansion, Validation | **+8-10%** | **85-95%+** | 1-2 months |

---

## 🎯 Priority Implementation Order

### **Week 1-2: Critical Fixes**
1. ✅ **Improve protocol chunking** (fixes 48% protocol gap)
2. ✅ **Add reranking** (universal +5-10% boost)
3. ✅ **Fine-tune embeddings** (biggest single impact)

**Expected**: Protocol 48% → 70%, Overall +15%

### **Week 3-4: High-Impact**
4. ✅ **Query classification & routing**
5. ✅ **Document consolidation** (create master profiles)
6. ✅ **Tune hybrid search weights**

**Expected**: Overall +10%, hitting 85% on most query types

### **Month 2: Polish**
7. ✅ **Metadata-driven retrieval**
8. ✅ **Contextual compression**
9. ✅ **Answer validation**

**Expected**: Consistent 85-90%+ across ALL query types

---

## 🔧 Quick Start: Highest ROI Improvements

### **This Week (DO FIRST)**

#### A. Fix Protocol Chunking (3 days)
```bash
# Update hierarchical_chunking.py StepAwareChunker
# Keep protocol sections together, don't split session info
```

#### B. Add Reranking (1 day)
```bash
pip install cohere  # or sentence-transformers

# Update rag_service.py to add reranking step
```

#### C. Create Consolidated Documents (3 days)
```bash
# Manually create consolidated profiles for top 5 products
# Ingest these as high-priority documents
```

**Expected Impact**: +20-25% improvement in 1 week

---

## 📈 Measuring Success

### Track These Metrics Weekly:
```python
# Run this test suite weekly
test_queries_by_type = {
    "protocol": [
        "How many sessions for Plinest Hair?",
        "What is the treatment frequency for Newest?",
        "Dosage for NewGyn treatment?"
    ],
    "comparison": [
        "Newest vs Plinest difference",
        "Compare Plinest Hair and Plinest Eye"
    ],
    # ... etc
}

for query_type, queries in test_queries_by_type.items():
    scores = [rag.search(q)[0]['score'] for q in queries]
    avg_score = sum(scores) / len(scores)
    print(f"{query_type}: {avg_score:.1%} (target: 85%)")
```

### Success Criteria:
- ✅ ALL query types above 85%
- ✅ No query type below 80%
- ✅ Average across all types: 87%+

---

## 💡 Key Insights

### What Drives 85%+ Confidence:
1. **Domain-specific embeddings** (fine-tuned > generic)
2. **Complete, consolidated documents** (single source of truth)
3. **Query-aware retrieval** (different strategies for different needs)
4. **Reranking** (fixes initial retrieval mistakes)
5. **Quality validation** (catch and retry low-confidence answers)

### What Doesn't Work:
- ❌ Just increasing top_k (more noise)
- ❌ Generic prompt engineering (needs domain knowledge)
- ❌ Over-filtering with metadata (too restrictive)
- ❌ Overly large chunks (dilutes relevance)

---

## ✅ Next Steps

**Immediate Actions (This Week)**:
1. Fix protocol chunking
2. Add reranking layer
3. Create 3 consolidated product profiles
4. Measure baseline improvement

**Expected Result**: Protocol queries 48% → 70%+, Overall +15-20%

**Month 1 Goal**: 85%+ on 5/6 query types
**Month 2 Goal**: 85%+ on ALL query types, 87%+ average

---

**Status**: Roadmap ready for implementation
**Estimated effort**: 1-2 months to 85%+ consistent performance
**ROI**: Transform from 48-78% (inconsistent) to 85-95% (production-grade)
