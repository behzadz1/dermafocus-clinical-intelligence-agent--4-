"""
Lightweight BM25 lexical index over processed chunks.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import structlog

logger = structlog.get_logger()


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return TOKEN_PATTERN.findall((text or "").lower())


@dataclass
class LexicalChunk:
    chunk_id: str
    text: str
    metadata: Dict[str, object]
    chunk_type: str
    section: str


class LexicalIndex:
    """
    In-memory BM25 index for lexical retrieval.
    """

    def __init__(self, chunks: List[LexicalChunk]):
        self.chunks = chunks
        self.doc_freq: Dict[str, int] = {}
        self.doc_lens: List[int] = []
        self.term_freqs: List[Dict[str, int]] = []
        self.avgdl = 0.0
        self._build()

    @classmethod
    def from_processed_dir(cls, processed_dir: Path) -> "LexicalIndex":
        chunks: List[LexicalChunk] = []
        processed_dir = Path(processed_dir)
        if not processed_dir.exists():
            logger.warning("lexical_index_missing_processed_dir", processed_dir=str(processed_dir))
            return cls([])

        for file_path in processed_dir.glob("*_processed.json"):
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("lexical_index_read_failed", file=str(file_path), error=str(e))
                continue

            for idx, chunk in enumerate(payload.get("chunks", [])):
                text = chunk.get("text") or ""
                if not text.strip():
                    continue
                chunk_id = chunk.get("id") or f"{payload.get('doc_id','doc')}_chunk_{idx}"
                metadata = chunk.get("metadata", {}) or {}
                metadata.setdefault("doc_id", chunk.get("doc_id") or payload.get("doc_id"))
                metadata.setdefault("doc_type", chunk.get("doc_type") or payload.get("doc_type"))
                section = chunk.get("section") or metadata.get("section") or ""
                chunks.append(
                    LexicalChunk(
                        chunk_id=str(chunk_id),
                        text=text,
                        metadata=metadata,
                        chunk_type=chunk.get("chunk_type") or "flat",
                        section=section,
                    )
                )

        logger.info("lexical_index_loaded", chunks=len(chunks))
        return cls(chunks)

    def _build(self) -> None:
        if not self.chunks:
            self.avgdl = 0.0
            return

        df: Dict[str, int] = {}
        term_freqs: List[Dict[str, int]] = []
        doc_lens: List[int] = []

        for chunk in self.chunks:
            tokens = _tokenize(chunk.text)
            doc_lens.append(len(tokens))
            tf: Dict[str, int] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
            term_freqs.append(tf)
            for token in tf.keys():
                df[token] = df.get(token, 0) + 1

        self.doc_freq = df
        self.term_freqs = term_freqs
        self.doc_lens = doc_lens
        self.avgdl = sum(doc_lens) / max(1, len(doc_lens))

        logger.info(
            "lexical_index_built",
            docs=len(self.chunks),
            avgdl=round(self.avgdl, 2),
            vocab=len(self.doc_freq)
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
        doc_type: Optional[str] = None,
        k1: float = 1.5,
        b: float = 0.75
    ) -> List[Tuple[LexicalChunk, float]]:
        """
        Return top_k chunks scored by BM25.
        """
        if not self.chunks:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        N = len(self.chunks)
        scores: List[Tuple[int, float]] = []
        for idx, chunk in enumerate(self.chunks):
            if doc_type and chunk.metadata.get("doc_type") != doc_type:
                continue
            score = 0.0
            doc_len = self.doc_lens[idx]
            tf = self.term_freqs[idx]
            for term in tokens:
                freq = tf.get(term, 0)
                if freq == 0:
                    continue
                df = self.doc_freq.get(term, 0)
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                denom = freq + k1 * (1 - b + b * (doc_len / (self.avgdl or 1.0)))
                score += idf * ((freq * (k1 + 1)) / (denom or 1.0))
            if score > 0:
                scores.append((idx, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        results: List[Tuple[LexicalChunk, float]] = []
        for idx, score in scores[:top_k]:
            results.append((self.chunks[idx], score))

        return results
