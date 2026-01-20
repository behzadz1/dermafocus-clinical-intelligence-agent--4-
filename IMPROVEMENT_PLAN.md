# DermaFocus Improvement Plan

> Based on expert review feedback - Prioritized by clinical risk and business impact

---

## Executive Summary

The current system is a **well-structured prototype** with strong UX but gaps in:
1. Data pipeline (ingestion not connected to retrieval)
2. Security (no auth, PHI exposure risk)
3. Reliability (sync blocking, cache inconsistency)
4. Quality assurance (minimal testing, no retrieval benchmarks)

---

## Phase 1: Critical Fixes (Week 1-2)
**Goal:** Close the ingestion gap and fix blocking issues

### 1.1 End-to-End Ingestion Pipeline ⚠️ CRITICAL

**Current Problem:** Documents upload but vectors are never indexed to Pinecone.

**Solution:**

```python
# backend/app/api/routes/documents.py - MODIFY upload endpoint

@router.post("/upload")
async def upload_document(file: UploadFile):
    # 1. Save file (existing)
    # 2. Process/chunk (existing)
    # 3. ADD: Generate embeddings
    # 4. ADD: Upsert to Pinecone
    # 5. ADD: Store document metadata with status
    # 6. ADD: Invalidate related caches
```

**Tasks:**
- [ ] Connect `document_processor.py` output to `embedding_service.embed_chunks()`
- [ ] Call `pinecone_service.upsert_vectors()` after embedding
- [ ] Create `DocumentMetadata` table/store for status tracking
- [ ] Add deletion hooks that clean up Pinecone vectors
- [ ] Add document versioning (replace vs. append)

**Files to modify:**
- `backend/app/api/routes/documents.py`
- `backend/app/services/rag_service.py`
- `backend/app/models/schemas.py`

---

### 1.2 Fix Async/Sync Blocking 🔴 HIGH

**Current Problem:** Sync Anthropic/OpenAI clients block the event loop.

**Solution:**

```python
# backend/app/services/claude_service.py - Use async client

from anthropic import AsyncAnthropic

class ClaudeService:
    @property
    def client(self) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate_response(self, ...):  # Make async
        response = await self.client.messages.create(...)
```

**Tasks:**
- [ ] Replace `Anthropic` with `AsyncAnthropic` in claude_service.py
- [ ] Replace `OpenAI` with `AsyncOpenAI` in embedding_service.py
- [ ] Update all route handlers to `await` service calls
- [ ] Test streaming still works with async client

**Files to modify:**
- `backend/app/services/claude_service.py`
- `backend/app/services/embedding_service.py`
- `backend/app/api/routes/chat.py`

---

### 1.3 Fix Multi-Turn Conversation 🟡 MEDIUM

**Current Problem:** Frontend sends empty history array.

**Solution:**

```typescript
// frontend/src/components/Chat/ChatWindow.tsx

// Build history from messages state
const history = messages
  .filter(m => m.id !== 'welcome')
  .map(m => ({
    role: m.role === 'user' ? 'user' : 'assistant',
    content: m.text
  }));

// Pass to API
apiService.sendMessageStream(query, conversationId, history, ...)
```

**Tasks:**
- [ ] Build conversation history from messages state
- [ ] Pass history to sendMessageStream/sendMessage
- [ ] Limit to last 10 messages to control context size
- [ ] Store conversation_id in state for session continuity

---

## Phase 2: Security & Compliance (Week 3-4)
**Goal:** Make the system safe for clinical environments

### 2.1 Authentication & Authorization 🔴 HIGH

**Solution:** Add API key authentication (simple) or OAuth (enterprise)

```python
# backend/app/middleware/auth.py - NEW FILE

from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key not in settings.valid_api_keys:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Apply to routes
@router.post("/", dependencies=[Depends(verify_api_key)])
async def chat(request: ChatRequest):
    ...
```

**Tasks:**
- [ ] Create API key validation middleware
- [ ] Add `VALID_API_KEYS` to config (comma-separated list)
- [ ] Apply to all non-health endpoints
- [ ] Add rate limiting per API key
- [ ] Document API key provisioning process

---

### 2.2 PHI Logging Controls 🔴 HIGH

**Current Problem:** Query text logged without redaction.

**Solution:**

```python
# backend/app/utils/logging.py - NEW FILE

import re

PHI_PATTERNS = [
    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
    r'\b\d{10}\b',  # Phone
]

def redact_phi(text: str) -> str:
    for pattern in PHI_PATTERNS:
        text = re.sub(pattern, '[REDACTED]', text)
    return text

# In chat.py
logger.info("chat_request", question=redact_phi(request.question[:100]))
```

**Tasks:**
- [ ] Create PHI redaction utility
- [ ] Apply to all query logging
- [ ] Add configurable logging levels (FULL, REDACTED, MINIMAL)
- [ ] Add log retention policy configuration
- [ ] Create audit log for compliance (separate from app logs)

---

### 2.3 Request ID & Audit Trail 🟡 MEDIUM

**Solution:**

```python
# backend/app/middleware/request_id.py - NEW FILE

from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

**Tasks:**
- [ ] Add request ID middleware
- [ ] Include request_id in all log entries
- [ ] Return request_id in error responses
- [ ] Create audit log table for compliance queries

---

## Phase 3: Reliability & Observability (Week 5-6)
**Goal:** Production-ready monitoring and caching

### 3.1 Distributed Cache (Redis) 🟡 MEDIUM

**Current Problem:** In-memory cache is per-process.

**Solution:**

```python
# backend/app/services/cache_service.py - MODIFY

import redis.asyncio as redis

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(settings.redis_url)

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ttl: int = 3600):
        await self.redis.setex(key, ttl, value)
```

**Tasks:**
- [ ] Replace in-memory dict with Redis client
- [ ] Add Redis to docker-compose for local dev
- [ ] Update cache_service to use async Redis
- [ ] Add cache hit/miss metrics

---

### 3.2 Health Checks & Readiness 🟡 MEDIUM

**Current Problem:** Health checks don't verify dependencies.

**Solution:**

```python
# backend/app/api/routes/health.py - MODIFY

@router.get("/ready")
async def readiness_check():
    checks = {
        "pinecone": await pinecone_service.health_check(),
        "claude": await claude_service.health_check(),
        "embeddings": await embedding_service.health_check(),
        "redis": await cache_service.health_check(),
    }

    all_healthy = all(c["status"] == "healthy" for c in checks.values())

    if not all_healthy:
        raise HTTPException(status_code=503, detail=checks)

    return {"status": "ready", "checks": checks}
```

**Tasks:**
- [ ] Make all health_check methods async
- [ ] Add `/ready` endpoint for Kubernetes probes
- [ ] Add `/live` endpoint (always returns 200)
- [ ] Add timeout handling for dependency checks
- [ ] Return proper 503 on unhealthy

---

### 3.3 Metrics & LLM Cost Tracking 🟡 MEDIUM

**Solution:**

```python
# backend/app/utils/metrics.py - NEW FILE

from prometheus_client import Counter, Histogram

llm_requests = Counter('llm_requests_total', 'Total LLM requests', ['model', 'status'])
llm_tokens = Counter('llm_tokens_total', 'Total tokens used', ['model', 'type'])
llm_latency = Histogram('llm_latency_seconds', 'LLM request latency')
retrieval_latency = Histogram('retrieval_latency_seconds', 'RAG retrieval latency')

# In claude_service.py
llm_tokens.labels(model=self.model, type='input').inc(response.usage.input_tokens)
llm_tokens.labels(model=self.model, type='output').inc(response.usage.output_tokens)
```

**Tasks:**
- [ ] Add Prometheus metrics
- [ ] Track LLM token usage per model
- [ ] Track retrieval latency
- [ ] Track cache hit rates
- [ ] Add /metrics endpoint
- [ ] Create Grafana dashboard template

---

## Phase 4: Quality & Testing (Week 7-8)
**Goal:** Confidence in retrieval quality and system correctness

### 4.1 Test Suite Expansion 🟡 MEDIUM

**Tasks:**
- [ ] Add unit tests for all services (pytest)
- [ ] Add integration tests for chat endpoint
- [ ] Add streaming response tests
- [ ] Add document processing tests
- [ ] Target 70% code coverage

**Test structure:**
```
backend/tests/
├── unit/
│   ├── test_claude_service.py
│   ├── test_rag_service.py
│   ├── test_embedding_service.py
│   └── test_chunking.py
├── integration/
│   ├── test_chat_endpoint.py
│   ├── test_document_upload.py
│   └── test_streaming.py
└── conftest.py  # Fixtures, mocks
```

---

### 4.2 Retrieval Quality Benchmark 🟡 MEDIUM

**Solution:** Create golden answer test set

```python
# backend/tests/retrieval/golden_answers.json
[
    {
        "query": "What is the needle size for Plinest Eye?",
        "expected_sources": ["Mastelli_Portfolio"],
        "expected_keywords": ["30G", "needle"],
        "min_confidence": 0.7
    },
    ...
]

# backend/tests/retrieval/test_retrieval_quality.py
@pytest.mark.parametrize("case", load_golden_answers())
def test_retrieval_quality(case):
    response = chat(question=case["query"])
    assert any(s.document in case["expected_sources"] for s in response.sources)
    assert response.confidence >= case["min_confidence"]
```

**Tasks:**
- [ ] Create 20+ golden Q&A pairs from actual clinical docs
- [ ] Add retrieval regression test
- [ ] Track retrieval quality metrics over time
- [ ] Alert on quality degradation

---

### 4.3 Confidence Score Calibration 🟢 LOW

**Current Problem:** Confidence is heuristic, not calibrated.

**Solution:**
1. Collect ground truth ratings from clinicians
2. Plot predicted confidence vs. actual correctness
3. Apply calibration curve (Platt scaling)
4. Or: rename to "Evidence Strength" to avoid misleading

**Tasks:**
- [ ] Collect 100+ rated responses
- [ ] Analyze calibration curve
- [ ] Either calibrate or rename the metric
- [ ] Document what confidence means in UI

---

## Phase 5: Advanced Features (Week 9+)
**Goal:** Enhanced retrieval and clinical safety

### 5.1 Reranking & Diversity 🟢 LOW

**Solution:** Add cross-encoder reranking

```python
# backend/app/services/reranker_service.py - NEW FILE

from sentence_transformers import CrossEncoder

class RerankerService:
    def __init__(self):
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    def rerank(self, query: str, chunks: List[Dict]) -> List[Dict]:
        pairs = [(query, c["text"]) for c in chunks]
        scores = self.model.predict(pairs)

        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)

        return sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
```

**Tasks:**
- [ ] Add cross-encoder reranking
- [ ] Implement MMR for diversity
- [ ] A/B test retrieval quality improvement

---

### 5.2 Clinical Safety Boundaries 🟢 LOW

**Solution:** Add out-of-scope detection

```python
# Detect questions outside clinical scope
OUT_OF_SCOPE_PATTERNS = [
    "diagnose", "prescribe", "medical advice",
    "should I", "is it safe for me"
]

def check_clinical_safety(question: str) -> Optional[str]:
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if pattern in question.lower():
            return "I can provide information about Dermafocus products, but cannot provide personal medical advice. Please consult a healthcare professional."
    return None
```

---

## Implementation Priority Matrix

| Phase | Effort | Impact | Risk Reduction |
|-------|--------|--------|----------------|
| 1.1 Ingestion Pipeline | High | Critical | ⭐⭐⭐⭐⭐ |
| 1.2 Async/Sync Fix | Medium | High | ⭐⭐⭐⭐ |
| 1.3 Multi-Turn Chat | Low | Medium | ⭐⭐ |
| 2.1 Authentication | Medium | Critical | ⭐⭐⭐⭐⭐ |
| 2.2 PHI Logging | Low | Critical | ⭐⭐⭐⭐⭐ |
| 2.3 Request IDs | Low | Medium | ⭐⭐⭐ |
| 3.1 Redis Cache | Medium | Medium | ⭐⭐⭐ |
| 3.2 Health Checks | Low | High | ⭐⭐⭐⭐ |
| 3.3 Metrics | Medium | Medium | ⭐⭐⭐ |
| 4.1 Test Suite | High | High | ⭐⭐⭐⭐ |
| 4.2 Golden Answers | Medium | High | ⭐⭐⭐⭐ |
| 4.3 Calibration | Low | Low | ⭐⭐ |
| 5.1 Reranking | Medium | Medium | ⭐⭐ |
| 5.2 Safety Bounds | Low | Medium | ⭐⭐⭐ |

---

## Quick Wins (Can Do This Week)

1. **Fix multi-turn chat** - 2 hours
2. **Add request ID middleware** - 1 hour
3. **PHI redaction in logs** - 2 hours
4. **Proper health check status codes** - 1 hour
5. **Add API key auth (simple)** - 3 hours

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Document upload → searchable | Manual | Automatic |
| Test coverage | ~5% | 70% |
| Auth endpoints | 0% | 100% |
| P95 latency | Unknown | <3s |
| Retrieval accuracy | Unknown | >85% |
| Uptime | Unknown | 99.5% |

---

*Plan created: January 2025*
*Review cycle: Bi-weekly*
