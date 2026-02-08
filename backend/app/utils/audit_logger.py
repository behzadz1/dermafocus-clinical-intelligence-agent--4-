"""
Audit logging utility (JSON lines).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib

from fastapi import Request
from pythonjsonlogger import jsonlogger

from app.config import settings


_AUDIT_LOGGER_NAME = "audit"


def _ensure_logger() -> logging.Logger:
    logger = logging.getLogger(_AUDIT_LOGGER_NAME)
    if logger.handlers:
        return logger

    log_path = Path(settings.audit_log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=settings.audit_log_max_bytes,
        backupCount=settings.audit_log_backup_count,
        encoding="utf-8"
    )
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def _fingerprint(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:12]


def log_audit_event(
    event: str,
    request: Optional[Request] = None,
    **fields: Any
) -> None:
    if not settings.audit_log_enabled:
        return

    logger = _ensure_logger()
    payload: Dict[str, Any] = {"event": event}

    if request is not None:
        request_id = request.headers.get("X-Request-ID")
        state_request_id = getattr(getattr(request, "state", None), "request_id", None)
        payload.update({
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent"),
            "request_id": request_id or state_request_id,
        })
        api_key = request.headers.get(settings.api_key_header) or request.query_params.get("api_key")
        payload["api_key_fp"] = _fingerprint(api_key)

    payload.update(fields)
    logger.info("audit", extra=payload)
