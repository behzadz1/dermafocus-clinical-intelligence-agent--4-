#!/usr/bin/env python3
"""Minimal live RAG probe using only stdlib HTTP clients.

This script intentionally avoids third-party dependencies so it can run in
constrained environments where backend requirements are not installed.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

QUERIES = [
    "What is Newest?",
    "What are contraindications for Plinest Eye?",
    "periorbital treatment protocol",
]


def _json_request(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=45, context=ctx) as response:
        return json.loads(response.read().decode("utf-8"))


def embed_query(query: str) -> List[float]:
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if base.endswith(":18080"):
        base = f"{base}/v1"

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")

    url = f"{base}/embeddings"
    payload = {
        "model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        "input": query,
    }
    result = _json_request(
        url,
        payload,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    if "error" in result:
        raise RuntimeError(f"Embedding failed: {result['error']}")
    return result["data"][0]["embedding"]


def resolve_pinecone_host() -> str:
    direct = os.getenv("PINECONE_INDEX_HOST", "").strip()
    if direct:
        return direct

    index = os.getenv("PINECONE_INDEX_NAME", "").strip()
    if not index:
        raise RuntimeError("PINECONE_INDEX_NAME missing")

    api_key = os.getenv("PINECONE_API_KEY", "")
    if not api_key:
        raise RuntimeError("PINECONE_API_KEY missing")

    describe_url = f"https://api.pinecone.io/indexes/{index}"
    req = urllib.request.Request(
        describe_url,
        headers={
            "Api-Key": api_key,
            "X-Pinecone-API-Version": "2025-04",
        },
        method="GET",
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
        desc = json.loads(response.read().decode("utf-8"))
    host = desc.get("host", "")
    if not host:
        raise RuntimeError(f"Could not resolve Pinecone host from describe-index response: {desc}")
    return host


def query_pinecone(vector: List[float], top_k: int = 3) -> Dict[str, Any]:
    host = resolve_pinecone_host()
    api_key = os.getenv("PINECONE_API_KEY", "")
    namespace = os.getenv("PINECONE_NAMESPACE", "default")

    url = f"https://{host}/query"
    payload = {
        "vector": vector,
        "topK": top_k,
        "namespace": namespace,
        "includeMetadata": True,
    }
    return _json_request(
        url,
        payload,
        {
            "Api-Key": api_key,
            "Content-Type": "application/json",
            "X-Pinecone-API-Version": "2025-04",
        },
    )


def main() -> int:
    print("=" * 80)
    print("LIVE RAG PROBE (OpenAI embeddings + Pinecone query)")
    print("=" * 80)

    ok = 0
    for idx, query in enumerate(QUERIES, start=1):
        print(f"\n[{idx}] Query: {query}")
        try:
            embedding = embed_query(query)
            print(f"  - embedding: ok (dim={len(embedding)})")
            result = query_pinecone(embedding, top_k=3)
            matches = result.get("matches", [])
            print(f"  - pinecone matches: {len(matches)}")
            for rank, match in enumerate(matches[:3], start=1):
                md = match.get("metadata", {})
                doc = md.get("document_name") or md.get("doc_id") or "unknown"
                score = match.get("score")
                print(f"    {rank}. doc={doc} score={score}")
            ok += 1
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"  - HTTPError {exc.code}: {body[:400]}")
        except Exception as exc:  # noqa: BLE001
            print(f"  - ERROR: {exc}")

    print("\n" + "=" * 80)
    print(f"Completed {len(QUERIES)} queries, successful end-to-end: {ok}/{len(QUERIES)}")
    print("=" * 80)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
