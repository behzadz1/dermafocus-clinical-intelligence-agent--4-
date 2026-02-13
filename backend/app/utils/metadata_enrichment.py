"""
Canonical metadata enrichment for RAG indexing.
"""

import re
from typing import Any, Dict, Optional


PRODUCT_TERMS = [
    "plinest eye",
    "plinest hair",
    "plinest",
    "newest",
    "newgyn",
    "purasomes xcell",
    "purasomes skin glow complex",
    "purasomes hair & scalp complex",
    "purasomes nutri complex 150+",
    "purasomes"
]

ANATOMY_TERMS = {
    "periocular": ["periocular", "eye contour", "under eye", "under-eye", "orbital"],
    "perioral": ["perioral", "perioral area", "lip area", "mouth area", "lips"],
    "face": ["face", "facial", "full-face", "full face"],
    "scalp": ["scalp", "hairline", "follicle"],
    "vulvovaginal": ["vulvar", "vaginal", "intimate"],
    "neck": ["neck", "décolleté", "decollete"],
    "hand": ["hand", "hands", "dorsum of hand", "dorsum"],
}

TREATMENT_TERMS = {
    "rejuvenation": ["rejuvenation", "anti-aging", "anti aging", "revitalization"],
    "protocol": ["protocol", "step", "session", "injection technique"],
    "hair_restoration": ["hair loss", "alopecia", "hair restoration"],
    "periocular_treatment": ["dark circles", "eye contour", "periocular"],
    "perioral_treatment": ["lip enhancement", "perioral rejuvenation", "lip restoration", "mouth area treatment"],
    "hand_treatment": ["hand rejuvenation", "hand restoration", "dorsum rejuvenation"],
}

AUDIENCE_TERMS = {
    "patient": ["patient", "consumer", "before and after", "brochure"],
    "hcp": ["physician", "doctor", "clinic", "protocol", "contraindication", "injection"],
}


def build_canonical_metadata(
    doc_id: str,
    doc_type: str,
    chunk_index: int,
    text: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Normalize and enrich metadata fields used by retrieval and filtering.
    """
    base = sanitize_metadata(metadata or {})
    text_value = (text or "").strip()
    source_blob = _build_source_blob(doc_id, doc_type, text_value, base)

    product = str(base.get("product") or _match_term(PRODUCT_TERMS, source_blob) or "")
    treatment = str(base.get("treatment") or _match_term_map(TREATMENT_TERMS, source_blob) or "")
    anatomy = str(base.get("anatomy") or _match_term_map(ANATOMY_TERMS, source_blob) or "")
    audience = str(base.get("audience") or _infer_audience(doc_type, source_blob) or "")
    version = str(base.get("version") or _infer_version(base) or "")
    content_modality = str(base.get("content_modality") or _infer_content_modality(doc_type, base) or "text")

    enriched = {
        **base,
        "doc_id": doc_id,
        "doc_type": doc_type or str(base.get("doc_type") or "unknown"),
        "chunk_index": int(chunk_index),
        "text": text_value[:1000],
        "product": product,
        "treatment": treatment,
        "anatomy": anatomy,
        "version": version,
        "audience": audience,
        "content_modality": content_modality,
        "source_kind": _infer_source_kind(base),
    }

    page_number = _to_positive_int(enriched.get("page_number"))
    page_start = _to_positive_int(enriched.get("page_start"))
    page_end = _to_positive_int(enriched.get("page_end"))

    source_kind = str(enriched.get("source_kind") or "")

    if page_number is None and source_kind == "pdf":
        # Fallback so PDF citations always resolve to at least page 1.
        page_number = 1
    if page_start is None and source_kind == "pdf":
        page_start = page_number or 1
    if page_end is None and source_kind == "pdf":
        page_end = page_start or 1

    if page_number is not None:
        enriched["page_number"] = page_number
    if page_start is not None:
        enriched["page_start"] = page_start
    if page_end is not None:
        enriched["page_end"] = page_end

    return sanitize_metadata(enriched)


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Keep metadata Pinecone-safe: scalars and lists of strings only.
    """
    clean: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, bool):
            clean[key] = value
            continue
        if isinstance(value, (int, float, str)):
            clean[key] = value
            continue
        if isinstance(value, list):
            clean[key] = [str(item) for item in value if item is not None]
            continue
        clean[key] = str(value)
    return clean


def _build_source_blob(doc_id: str, doc_type: str, text: str, metadata: Dict[str, Any]) -> str:
    parts = [
        doc_id or "",
        doc_type or "",
        str(metadata.get("title") or ""),
        str(metadata.get("section") or ""),
        str(metadata.get("source_file") or ""),
        text[:2500],
    ]
    return " ".join(parts).lower()


def _match_term(terms: list[str], source_blob: str) -> Optional[str]:
    for term in sorted(terms, key=len, reverse=True):
        if term in source_blob:
            return term
    return None


def _match_term_map(terms_map: Dict[str, list[str]], source_blob: str) -> Optional[str]:
    for label, terms in terms_map.items():
        if any(term in source_blob for term in terms):
            return label
    return None


def _infer_audience(doc_type: str, source_blob: str) -> str:
    doc_type_lower = (doc_type or "").lower()
    if doc_type_lower in {"brochure"}:
        return "patient"
    for audience, terms in AUDIENCE_TERMS.items():
        if any(term in source_blob for term in terms):
            return audience
    return "hcp"


def _infer_version(metadata: Dict[str, Any]) -> Optional[str]:
    candidates = [
        str(metadata.get("title") or ""),
        str(metadata.get("source_file") or ""),
        str(metadata.get("subject") or ""),
    ]
    pattern = re.compile(r"(v\d+(?:\.\d+)?|rev(?:ision)?\s*\d+|20\d{2}(?:[-_/]\d{2})?)", re.IGNORECASE)
    for candidate in candidates:
        match = pattern.search(candidate)
        if match:
            return match.group(1)
    return None


def _infer_content_modality(doc_type: str, metadata: Dict[str, Any]) -> str:
    doc_type_lower = (doc_type or "").lower()
    if metadata.get("frame_path") or metadata.get("frame_index") is not None:
        return "image"
    if doc_type_lower == "video":
        return "transcript"
    if metadata.get("start_time") is not None or metadata.get("timestamp"):
        return "transcript"
    return "text"


def _infer_source_kind(metadata: Dict[str, Any]) -> str:
    source_file = str(metadata.get("source_file") or "").lower()
    if source_file.endswith((".mp4", ".mov", ".avi")):
        return "video"
    if source_file.endswith(".pdf"):
        return "pdf"
    if source_file.endswith((".txt", ".md", ".docx")):
        return "text"
    return "unknown"


def _to_positive_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
