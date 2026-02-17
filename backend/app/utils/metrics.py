"""
Prometheus Metrics for DermaFocus Clinical RAG System

Provides instrumentation for:
- Request latency (p50, p95, p99)
- Token usage (input/output)
- Cache hit/miss rates
- Retrieval confidence distribution
- Error rates by type
- Concurrent requests
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from typing import Optional
import time
from contextlib import contextmanager
import structlog

logger = structlog.get_logger()

# ==============================================================================
# REQUEST METRICS
# ==============================================================================

# Request count by endpoint and status
request_count = Counter(
    "dermaai_requests_total",
    "Total number of requests by endpoint and status",
    ["endpoint", "method", "status"],
)

# Request latency histogram (in seconds)
request_latency = Histogram(
    "dermaai_request_duration_seconds",
    "Request latency in seconds",
    ["endpoint", "method"],
    buckets=(0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0, 60.0),
)

# Active requests gauge
active_requests = Gauge(
    "dermaai_requests_active",
    "Number of requests currently being processed",
    ["endpoint"],
)

# ==============================================================================
# TOKEN USAGE METRICS
# ==============================================================================

# Claude token usage
claude_tokens_total = Counter(
    "dermaai_claude_tokens_total",
    "Total Claude tokens used",
    ["token_type"],  # input, output
)

claude_tokens_per_request = Histogram(
    "dermaai_claude_tokens_per_request",
    "Claude tokens per request",
    ["token_type"],  # input, output
    buckets=(100, 500, 1000, 2000, 3000, 5000, 10000),
)

# OpenAI embedding token usage
openai_tokens_total = Counter(
    "dermaai_openai_tokens_total",
    "Total OpenAI embedding tokens used",
)

openai_tokens_per_request = Histogram(
    "dermaai_openai_tokens_per_request",
    "OpenAI embedding tokens per request",
    buckets=(10, 50, 100, 200, 500, 1000),
)

# ==============================================================================
# CACHE METRICS
# ==============================================================================

cache_operations = Counter(
    "dermaai_cache_operations_total",
    "Cache operations by type and result",
    ["operation", "result"],  # operation: get, set; result: hit, miss, error
)

cache_hit_rate = Gauge(
    "dermaai_cache_hit_rate",
    "Cache hit rate (0-1)",
    ["cache_type"],  # embedding, context, pinecone
)

# ==============================================================================
# RETRIEVAL METRICS
# ==============================================================================

# Retrieval confidence distribution
retrieval_confidence = Histogram(
    "dermaai_retrieval_confidence",
    "Retrieval confidence scores",
    buckets=(0.0, 0.1, 0.2, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
)

# Number of chunks retrieved
chunks_retrieved = Histogram(
    "dermaai_chunks_retrieved",
    "Number of chunks retrieved per query",
    buckets=(0, 1, 3, 5, 10, 15, 20, 30, 50),
)

# Strong matches (score > 0.35)
strong_matches = Histogram(
    "dermaai_strong_matches",
    "Number of strong matches per query",
    buckets=(0, 1, 2, 3, 5, 10, 15),
)

# Hierarchy matches
hierarchy_matches = Counter(
    "dermaai_hierarchy_matches_total",
    "Hierarchy match types",
    ["match_type"],  # parent_only, child_only, both, flat
)

# Evidence sufficiency
evidence_sufficient = Counter(
    "dermaai_evidence_sufficient_total",
    "Evidence sufficiency decisions",
    ["sufficient"],  # true, false
)

# Query expansion
query_expansion_applied = Counter(
    "dermaai_query_expansion_total",
    "Query expansion applied",
    ["expansion_type"],  # comparison, product, safety, none
)

# ==============================================================================
# ERROR METRICS
# ==============================================================================

errors_total = Counter(
    "dermaai_errors_total",
    "Total errors by type",
    ["error_type", "endpoint"],
)

# Specific error types
insufficient_evidence_count = Counter(
    "dermaai_insufficient_evidence_total",
    "Requests refused due to insufficient evidence",
)

timeout_errors = Counter(
    "dermaai_timeout_errors_total",
    "Timeout errors by service",
    ["service"],  # claude, openai, pinecone
)

rate_limit_errors = Counter(
    "dermaai_rate_limit_errors_total",
    "Rate limit errors by service",
    ["service"],
)

# ==============================================================================
# PINECONE METRICS
# ==============================================================================

pinecone_queries = Counter(
    "dermaai_pinecone_queries_total",
    "Total Pinecone queries",
)

pinecone_query_latency = Histogram(
    "dermaai_pinecone_query_duration_seconds",
    "Pinecone query latency in seconds",
    buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0),
)

# ==============================================================================
# RERANKING METRICS
# ==============================================================================

reranking_operations = Counter(
    "dermaai_reranking_operations_total",
    "Reranking operations",
    ["enabled"],  # true, false
)

reranking_latency = Histogram(
    "dermaai_reranking_duration_seconds",
    "Reranking latency in seconds",
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0),
)

reranked_chunks = Histogram(
    "dermaai_reranked_chunks",
    "Number of chunks reranked",
    buckets=(5, 10, 15, 20, 30, 50, 100),
)

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


@contextmanager
def track_request(endpoint: str, method: str = "POST"):
    """
    Context manager to track request metrics.

    Usage:
        with track_request("/api/chat", "POST"):
            # process request
            pass
    """
    start_time = time.time()
    active_requests.labels(endpoint=endpoint).inc()

    try:
        yield
        status = "success"
    except Exception as e:
        status = "error"
        error_type = type(e).__name__
        errors_total.labels(error_type=error_type, endpoint=endpoint).inc()
        logger.error("Request error", error=str(e), error_type=error_type, endpoint=endpoint)
        raise
    finally:
        duration = time.time() - start_time
        active_requests.labels(endpoint=endpoint).dec()
        request_latency.labels(endpoint=endpoint, method=method).observe(duration)
        request_count.labels(endpoint=endpoint, method=method, status=status).inc()


@contextmanager
def track_operation(operation_name: str, metric: Optional[Histogram] = None):
    """
    Context manager to track operation latency.

    Usage:
        with track_operation("pinecone_query", pinecone_query_latency):
            # perform operation
            pass
    """
    start_time = time.time()

    try:
        yield
    finally:
        duration = time.time() - start_time
        if metric is not None:
            metric.observe(duration)


def record_token_usage(service: str, input_tokens: int, output_tokens: int = 0):
    """
    Record token usage for LLM services.

    Args:
        service: "claude" or "openai"
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens (0 for embeddings)
    """
    if service == "claude":
        claude_tokens_total.labels(token_type="input").inc(input_tokens)
        claude_tokens_per_request.labels(token_type="input").observe(input_tokens)

        if output_tokens > 0:
            claude_tokens_total.labels(token_type="output").inc(output_tokens)
            claude_tokens_per_request.labels(token_type="output").observe(output_tokens)

    elif service == "openai":
        openai_tokens_total.inc(input_tokens)
        openai_tokens_per_request.observe(input_tokens)


def record_cache_operation(operation: str, result: str):
    """
    Record cache operation.

    Args:
        operation: "get" or "set"
        result: "hit", "miss", or "error"
    """
    cache_operations.labels(operation=operation, result=result).inc()


def record_retrieval_metrics(
    confidence: float,
    chunks_count: int,
    strong_matches_count: int,
    hierarchy_match_type: str,
    evidence_sufficient_flag: bool,
    expansion_type: str = "none",
):
    """
    Record retrieval quality metrics.

    Args:
        confidence: Final confidence score (0-1)
        chunks_count: Number of chunks retrieved
        strong_matches_count: Number of chunks with score > 0.35
        hierarchy_match_type: "parent_only", "child_only", "both", or "flat"
        evidence_sufficient_flag: Whether evidence was sufficient
        expansion_type: Query expansion type applied
    """
    retrieval_confidence.observe(confidence)
    chunks_retrieved.observe(chunks_count)
    strong_matches.observe(strong_matches_count)
    hierarchy_matches.labels(match_type=hierarchy_match_type).inc()
    evidence_sufficient.labels(sufficient=str(evidence_sufficient_flag).lower()).inc()
    query_expansion_applied.labels(expansion_type=expansion_type).inc()


def record_insufficient_evidence():
    """Record when request is refused due to insufficient evidence."""
    insufficient_evidence_count.inc()


def record_timeout(service: str):
    """Record timeout error for a service."""
    timeout_errors.labels(service=service).inc()


def record_rate_limit(service: str):
    """Record rate limit error for a service."""
    rate_limit_errors.labels(service=service).inc()


def update_cache_hit_rate(cache_type: str, hit_rate: float):
    """
    Update cache hit rate gauge.

    Args:
        cache_type: "embedding", "context", or "pinecone"
        hit_rate: Hit rate between 0 and 1
    """
    cache_hit_rate.labels(cache_type=cache_type).set(hit_rate)


def record_pinecone_query(latency: float):
    """Record Pinecone query metrics."""
    pinecone_queries.inc()
    pinecone_query_latency.observe(latency)


def record_reranking(enabled: bool, latency: Optional[float] = None, chunks_count: Optional[int] = None):
    """
    Record reranking metrics.

    Args:
        enabled: Whether reranking was enabled
        latency: Reranking latency in seconds (if enabled)
        chunks_count: Number of chunks reranked (if enabled)
    """
    reranking_operations.labels(enabled=str(enabled).lower()).inc()

    if enabled and latency is not None:
        reranking_latency.observe(latency)

    if enabled and chunks_count is not None:
        reranked_chunks.observe(chunks_count)


def get_metrics_text():
    """
    Get metrics in Prometheus text format.

    Returns:
        Metrics as text string in Prometheus format
    """
    return generate_latest().decode("utf-8")


def get_metrics_content_type():
    """
    Get the content type for Prometheus metrics.

    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST


# ==============================================================================
# SUMMARY STATISTICS (for debugging/logging)
# ==============================================================================

def get_metrics_summary() -> dict:
    """
    Get a summary of current metrics (for debugging).

    Returns:
        Dictionary with metric summaries
    """
    # This is a simplified summary for debugging
    # In production, use Prometheus/Grafana for visualization
    return {
        "requests": {
            "total": "See prometheus_client.REGISTRY",
            "active": "See active_requests gauge",
        },
        "tokens": {
            "claude_total": "See claude_tokens_total",
            "openai_total": "See openai_tokens_total",
        },
        "cache": {
            "operations": "See cache_operations",
        },
        "retrieval": {
            "confidence": "See retrieval_confidence histogram",
            "evidence_sufficient": "See evidence_sufficient counter",
        },
        "errors": {
            "total": "See errors_total counter",
            "insufficient_evidence": "See insufficient_evidence_count",
        },
    }
