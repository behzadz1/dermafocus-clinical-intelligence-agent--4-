# Phase 0: Observability & Monitoring - Implementation Progress

**Started:** 2026-02-17
**Status:** ✅ Foundation Complete, 🔄 Instrumentation In Progress

---

## ✅ Completed (Ready to Use)

### 1. Prometheus Metrics Infrastructure
**Files Created:**
- ✅ `backend/app/utils/metrics.py` - Complete metrics library with 25+ metrics

**Metrics Available:**
- **Request Metrics:**
  - `dermaai_requests_total` - Total requests by endpoint/method/status
  - `dermaai_request_duration_seconds` - Request latency histogram (p50, p95, p99)
  - `dermaai_requests_active` - Active requests gauge

- **Token Usage Metrics:**
  - `dermaai_claude_tokens_total` - Claude tokens (input/output)
  - `dermaai_claude_tokens_per_request` - Per-request Claude tokens
  - `dermaai_openai_tokens_total` - OpenAI embedding tokens
  - `dermaai_openai_tokens_per_request` - Per-request OpenAI tokens

- **Cache Metrics:**
  - `dermaai_cache_operations_total` - Cache operations (hit/miss/error)
  - `dermaai_cache_hit_rate` - Cache hit rate gauge

- **Retrieval Metrics:**
  - `dermaai_retrieval_confidence` - Confidence distribution
  - `dermaai_chunks_retrieved` - Chunks retrieved per query
  - `dermaai_strong_matches` - Strong matches (score > 0.35)
  - `dermaai_hierarchy_matches_total` - Hierarchy match types
  - `dermaai_evidence_sufficient_total` - Evidence sufficiency decisions
  - `dermaai_query_expansion_total` - Query expansion applied

- **Error Metrics:**
  - `dermaai_errors_total` - Total errors by type/endpoint
  - `dermaai_insufficient_evidence_total` - Insufficient evidence refusals
  - `dermaai_timeout_errors_total` - Timeout errors by service
  - `dermaai_rate_limit_errors_total` - Rate limit errors by service

- **Service-Specific Metrics:**
  - `dermaai_pinecone_queries_total` - Pinecone query count
  - `dermaai_pinecone_query_duration_seconds` - Pinecone latency
  - `dermaai_reranking_operations_total` - Reranking operations
  - `dermaai_reranking_duration_seconds` - Reranking latency
  - `dermaai_reranked_chunks` - Chunks reranked

**Helper Functions:**
```python
# Easy-to-use context managers and recording functions
metrics.track_request(endpoint, method)  # Track request metrics
metrics.track_operation(name, metric)    # Track operation latency
metrics.record_token_usage(service, input_tokens, output_tokens)
metrics.record_cache_operation(operation, result)
metrics.record_retrieval_metrics(confidence, chunks_count, ...)
metrics.record_insufficient_evidence()
metrics.record_timeout(service)
metrics.record_rate_limit(service)
```

### 2. Metrics Endpoint
**Files Modified:**
- ✅ `backend/app/main.py` - Added `/metrics` endpoint

**Endpoint Available:**
```
GET /metrics
```

**Features:**
- Returns Prometheus text format
- Not rate-limited (for continuous scraping)
- Not audit-logged (reduce noise)
- Content-Type: `text/plain; version=0.0.4; charset=utf-8`

**Test:**
```bash
curl http://localhost:8000/metrics
```

**Expected Output:**
```
# HELP dermaai_requests_total Total number of requests by endpoint and status
# TYPE dermaai_requests_total counter
dermaai_requests_total{endpoint="/api/chat",method="POST",status="success"} 42.0
...
```

### 3. Dependencies Installed
- ✅ `prometheus_client==0.24.1` installed
- ✅ Added to `requirements.txt`

---

## 🔄 In Progress (Needs Completion)

### Instrumentation Tasks Remaining

#### 1. Instrument chat.py (20% complete)
**What's Done:**
- ✅ Imported metrics module

**What's Needed:**
```python
# At the top of chat() and chat_stream() endpoints:
with metrics.track_request("/api/chat", "POST"):
    # existing code

    # After retrieval:
    metrics.record_retrieval_metrics(
        confidence=final_confidence,
        chunks_count=len(retrieved_chunks),
        strong_matches_count=evidence.get("strong_matches", 0),
        hierarchy_match_type="flat",  # or from chunks
        evidence_sufficient_flag=evidence.get("sufficient", False),
        expansion_type=detected_expansion_type
    )

    # If insufficient evidence:
    if not evidence.get("sufficient"):
        metrics.record_insufficient_evidence()

    # After Claude generation:
    metrics.record_token_usage(
        "claude",
        input_tokens=claude_response.get("usage", {}).get("input_tokens", 0),
        output_tokens=claude_response.get("usage", {}).get("output_tokens", 0)
    )
```

**Estimated Time:** 1 hour

#### 2. Instrument rag_service.py
**What's Needed:**
```python
# In hierarchical_search():
with metrics.track_operation("hierarchical_search", metrics.request_latency):
    # existing code

    # After reranking:
    if settings.reranker_enabled:
        metrics.record_reranking(
            enabled=True,
            latency=rerank_time,
            chunks_count=len(rerank_pool)
        )

    # For each hierarchy match:
    for chunk in enriched_chunks:
        match_type = chunk.get("hierarchy_match", "flat")
        # This will be aggregated automatically

# In _get_lexical_index():
metrics.record_cache_operation("get", "hit" if found else "miss")
```

**Estimated Time:** 1 hour

#### 3. Instrument claude_service.py
**What's Needed:**
```python
# In generate_response():
try:
    with metrics.track_operation("claude_generation"):
        response = await client.messages.create(...)

        # Record token usage
        metrics.record_token_usage(
            "claude",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens
        )

except TimeoutError:
    metrics.record_timeout("claude")
    raise
except RateLimitError:
    metrics.record_rate_limit("claude")
    raise
```

**Estimated Time:** 30 minutes

#### 4. Instrument embedding_service.py
**What's Needed:**
```python
# In get_embedding():
# Check cache first
cache_key = f"embedding:{text_hash}"
cached = cache.get(cache_key)
if cached:
    metrics.record_cache_operation("get", "hit")
    return cached
else:
    metrics.record_cache_operation("get", "miss")

try:
    response = openai_client.embeddings.create(...)

    # Record token usage
    metrics.record_token_usage(
        "openai",
        input_tokens=response.usage.total_tokens
    )

except TimeoutError:
    metrics.record_timeout("openai")
    raise
```

**Estimated Time:** 30 minutes

#### 5. Instrument pinecone_service.py
**What's Needed:**
```python
# In query():
start = time.time()
try:
    results = index.query(...)
    latency = time.time() - start
    metrics.record_pinecone_query(latency)

except TimeoutError:
    metrics.record_timeout("pinecone")
    raise
```

**Estimated Time:** 15 minutes

---

## ⏳ Not Started (Phase 0.2 & 0.3)

### Phase 0.2: Cost Tracking Dashboard (2 days)

**Files to Create:**
- `backend/app/services/cost_tracker.py` - Cost calculation service
- `backend/scripts/generate_cost_report.py` - Daily/weekly cost reports

**Integration Points:**
- Modify `embedding_service.py` - Track OpenAI costs
- Modify `claude_service.py` - Track Claude costs
- Use Pinecone query counts from metrics

**Cost Formulas:**
```python
# Claude API (claude-sonnet-4-20250514)
claude_cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000

# OpenAI Embeddings (text-embedding-3-small)
openai_cost = tokens * 0.00002 / 1000

# Pinecone Queries
pinecone_cost = query_count * 0.000002
```

### Phase 0.3: Quality Metrics Collection (2 days)

**Files to Create:**
- `backend/app/evaluation/quality_metrics.py` - Quality metrics aggregation
- Weekly quality report script

**Metrics to Track:**
- Top retrieval score distribution
- Evidence sufficiency rate
- Query expansion effectiveness
- Refusal rate trends
- Confidence score distribution

**Integration:**
- Log quality events in `rag_service.py`
- Aggregate in weekly reports

---

## 🧪 Testing & Validation

### Test Metrics Endpoint
```bash
# Start backend
cd backend && uvicorn app.main:app --reload

# Query metrics
curl http://localhost:8000/metrics

# Should see output like:
# dermaai_requests_total{endpoint="/api/chat",method="POST",status="success"} 0.0
# dermaai_request_duration_seconds_bucket{endpoint="/api/chat",le="0.5",method="POST"} 0.0
# ...
```

### Test Instrumented Endpoint
```bash
# Make a query
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Newest?"}'

# Check metrics again
curl http://localhost:8000/metrics | grep dermaai_requests_total

# Should show:
# dermaai_requests_total{endpoint="/api/chat",method="POST",status="success"} 1.0
```

### Grafana Dashboard Setup (Optional)

**1. Install Prometheus:**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'dermaai'
    static_configs:
      - targets: ['localhost:8000']
```

**2. Install Grafana:**
- Add Prometheus as data source
- Import dashboard or create custom panels

**Example Queries:**
```promql
# Request rate
rate(dermaai_requests_total[5m])

# p95 latency
histogram_quantile(0.95, dermaai_request_duration_seconds_bucket)

# Token usage rate
rate(dermaai_claude_tokens_total[1h])

# Cache hit rate
dermaai_cache_hit_rate

# Evidence sufficiency rate
rate(dermaai_evidence_sufficient_total{sufficient="true"}[5m])
/ rate(dermaai_evidence_sufficient_total[5m])
```

---

## 📊 Next Steps

### Immediate (Complete Phase 0.1):
1. ✅ **Done:** Created metrics infrastructure
2. ✅ **Done:** Added /metrics endpoint
3. 🔄 **In Progress:** Instrument chat.py endpoint
4. ⏳ **TODO:** Instrument rag_service.py (1 hour)
5. ⏳ **TODO:** Instrument claude_service.py (30 min)
6. ⏳ **TODO:** Instrument embedding_service.py (30 min)
7. ⏳ **TODO:** Instrument pinecone_service.py (15 min)
8. ⏳ **TODO:** Test metrics collection end-to-end (30 min)

**Total Remaining:** ~3 hours

### Then Move to Phase 0.2 & 0.3:
- Cost tracking dashboard (2 days)
- Quality metrics collection (2 days)

### After Phase 0 Complete:
Move to **Phase 1: Production Readiness**
- Redis caching (4 days)
- Conversation persistence (5 days)
- Enhanced query expansion (3 days)
- Cross-document linking (4 days)

---

## 🎯 Success Criteria for Phase 0

- [x] `/metrics` endpoint returns Prometheus format
- [x] Metrics library with 25+ metrics created
- [x] Helper functions for easy instrumentation
- [ ] All critical paths instrumented (chat, RAG, Claude, embeddings, Pinecone)
- [ ] Metrics collected for 100% of requests
- [ ] Cost tracking dashboard generating daily reports
- [ ] Quality metrics logged and weekly reports generated
- [ ] Grafana dashboard (optional but recommended)

---

## 💡 Quick Reference

### Adding Metrics to New Code

**Wrap endpoints:**
```python
with metrics.track_request("/api/new_endpoint", "POST"):
    # your code
    pass
```

**Track operations:**
```python
with metrics.track_operation("expensive_operation", metrics.request_latency):
    # your code
    pass
```

**Record events:**
```python
metrics.record_token_usage("claude", input_tokens=100, output_tokens=50)
metrics.record_cache_operation("get", "hit")
metrics.record_retrieval_metrics(confidence=0.95, chunks_count=5, ...)
```

**Record errors:**
```python
try:
    # risky operation
    pass
except TimeoutError:
    metrics.record_timeout("service_name")
    raise
```

---

**Status:** Foundation complete, instrumentation 20% done
**Next Focus:** Complete instrumentation of critical paths (3 hours)
**Blocker:** None - ready to continue
