"""
Document Version API Routes
Endpoints for document version management and sync
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import structlog

from app.utils.document_versioning import get_version_manager
from app.services.document_sync import get_sync_service

logger = structlog.get_logger()
router = APIRouter()


# Request/Response Models

class VersionInfo(BaseModel):
    """Document version information"""
    doc_id: str
    version: str
    file_path: str
    file_hash: str
    last_updated: str
    supersedes: Optional[str] = None
    metadata: Dict[str, Any] = {}


class VersionHistoryResponse(BaseModel):
    """Version history response"""
    doc_id: str
    current_version: str
    version_count: int
    history: List[VersionInfo]


class ChangeDetectionResponse(BaseModel):
    """Change detection response"""
    timestamp: str
    new: List[str]
    updated: List[str]
    unchanged: List[str]
    details: Dict[str, Dict[str, Any]]


class SyncRequest(BaseModel):
    """Cloud sync request"""
    provider: str  # "s3" or "dropbox"
    bucket_name: Optional[str] = None  # For S3
    prefix: Optional[str] = ""  # For S3
    folder_path: Optional[str] = None  # For Dropbox
    access_token: Optional[str] = None  # Optional override
    aws_region: Optional[str] = "us-east-1"  # For S3


class SyncResponse(BaseModel):
    """Cloud sync response"""
    success: bool
    downloaded: List[str]
    updated: List[str]
    error: Optional[str] = None


class SyncStatusResponse(BaseModel):
    """Sync status response"""
    timestamp: str
    changes_detected: Dict[str, int]
    version_statistics: Dict[str, Any]
    pending_updates: List[str]


class VersionReportResponse(BaseModel):
    """Version report response"""
    generated_at: str
    statistics: Dict[str, Any]
    documents: List[Dict[str, Any]]


# API Endpoints

@router.get("/versions/{doc_id}", response_model=VersionHistoryResponse)
async def get_version_history(doc_id: str):
    """
    Get version history for a document

    Args:
        doc_id: Document identifier

    Returns:
        Version history with all versions
    """
    try:
        version_manager = get_version_manager()

        history = version_manager.get_version_history(doc_id)

        if not history:
            raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

        current = history[-1]

        return VersionHistoryResponse(
            doc_id=doc_id,
            current_version=current.version,
            version_count=len(history),
            history=[
                VersionInfo(
                    doc_id=v.doc_id,
                    version=v.version,
                    file_path=v.file_path,
                    file_hash=v.file_hash,
                    last_updated=v.last_updated,
                    supersedes=v.supersedes,
                    metadata=v.metadata
                )
                for v in history
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_version_history_failed", doc_id=doc_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions/report", response_model=VersionReportResponse)
async def get_version_report():
    """
    Get comprehensive version report for all documents

    Returns:
        Report with statistics and document list
    """
    try:
        version_manager = get_version_manager()
        report = version_manager.export_version_report()

        return VersionReportResponse(**report)

    except Exception as e:
        logger.error("get_version_report_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/detect", response_model=ChangeDetectionResponse)
async def detect_changes():
    """
    Detect changes in upload directory

    Scans all PDFs and compares against version database

    Returns:
        Lists of new, updated, and unchanged documents
    """
    try:
        from datetime import datetime

        sync_service = get_sync_service()
        changes = sync_service.detect_changes()

        return ChangeDetectionResponse(
            timestamp=datetime.utcnow().isoformat(),
            new=changes["new"],
            updated=changes["updated"],
            unchanged=changes["unchanged"],
            details=changes["details"]
        )

    except Exception as e:
        logger.error("detect_changes_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/cloud", response_model=SyncResponse)
async def sync_from_cloud(request: SyncRequest, background_tasks: BackgroundTasks):
    """
    Sync documents from cloud storage (S3 or Dropbox)

    Args:
        request: Sync configuration

    Returns:
        Sync results with downloaded/updated documents
    """
    try:
        sync_service = get_sync_service()

        if request.provider == "s3":
            if not request.bucket_name:
                raise HTTPException(status_code=400, detail="bucket_name required for S3 sync")

            result = sync_service.sync_from_s3(
                bucket_name=request.bucket_name,
                prefix=request.prefix or "",
                aws_region=request.aws_region
            )

        elif request.provider == "dropbox":
            if not request.folder_path:
                raise HTTPException(status_code=400, detail="folder_path required for Dropbox sync")

            result = sync_service.sync_from_dropbox(
                folder_path=request.folder_path,
                access_token=request.access_token
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: {request.provider}. Use 's3' or 'dropbox'"
            )

        success = result.get("error") is None

        return SyncResponse(
            success=success,
            downloaded=result.get("downloaded", []),
            updated=result.get("updated", []),
            error=result.get("error")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("sync_from_cloud_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """
    Get current sync status and statistics

    Returns:
        Sync status with pending updates and statistics
    """
    try:
        sync_service = get_sync_service()
        status = sync_service.get_sync_status()

        return SyncStatusResponse(**status)

    except Exception as e:
        logger.error("get_sync_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/invalidate/{doc_id}")
async def invalidate_document_chunks(doc_id: str):
    """
    Manually invalidate (delete) all chunks for a document

    Args:
        doc_id: Document identifier

    Returns:
        Success confirmation
    """
    try:
        sync_service = get_sync_service()

        deleted_count = sync_service.invalidate_old_chunks(doc_id)

        return {
            "success": True,
            "doc_id": doc_id,
            "chunks_deleted": deleted_count,
            "message": f"Invalidated chunks for document: {doc_id}"
        }

    except Exception as e:
        logger.error("invalidate_chunks_failed", doc_id=doc_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
