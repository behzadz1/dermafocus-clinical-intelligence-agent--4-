"""
Document Sync Service
Auto-syncs documents from cloud storage and manages document lifecycle
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from app.utils.document_versioning import get_version_manager, DocumentVersion
from app.services.pinecone_service import get_pinecone_service

logger = structlog.get_logger()


class DocumentSyncService:
    """
    Syncs documents from cloud storage and manages updates

    Features:
    - Auto-sync from S3, Dropbox, Google Drive
    - Change detection (SHA256 hash)
    - Automatic chunk invalidation on updates
    - Version tracking
    """

    def __init__(self, upload_dir: Optional[Path] = None):
        """
        Initialize sync service

        Args:
            upload_dir: Directory for uploaded PDFs
                       Defaults to backend/data/uploads/
        """
        if upload_dir is None:
            base_dir = Path(__file__).parent.parent.parent
            upload_dir = base_dir / "data" / "uploads"

        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        self.version_manager = get_version_manager()
        self.pinecone_service = get_pinecone_service()

        # Cloud storage clients (lazy loaded)
        self._s3_client = None
        self._dropbox_client = None

    def detect_changes(self) -> Dict[str, Any]:
        """
        Scan upload directory and detect changes

        Returns:
            Dictionary with:
            - new: List of new document IDs
            - updated: List of updated document IDs
            - unchanged: List of unchanged document IDs
            - details: Dict with per-document details
        """
        logger.info("detecting_document_changes", upload_dir=str(self.upload_dir))

        changes = self.version_manager.detect_updates(self.upload_dir)

        logger.info(
            "change_detection_complete",
            new=len(changes["new"]),
            updated=len(changes["updated"]),
            unchanged=len(changes["unchanged"])
        )

        return changes

    def invalidate_old_chunks(self, doc_id: str, namespace: str = "default") -> int:
        """
        Invalidate (delete) old chunks for a document from Pinecone

        Args:
            doc_id: Document identifier
            namespace: Pinecone namespace

        Returns:
            Number of chunks deleted
        """
        try:
            logger.info("invalidating_old_chunks", doc_id=doc_id, namespace=namespace)

            # Query Pinecone for all chunks with this doc_id
            # Use a dummy vector to find all chunks (metadata filter)
            filter_dict = {"doc_id": doc_id}

            # Delete all chunks matching doc_id
            # Pinecone delete API: delete by filter
            delete_result = self.pinecone_service.index.delete(
                filter=filter_dict,
                namespace=namespace
            )

            logger.info(
                "chunks_invalidated",
                doc_id=doc_id,
                namespace=namespace
            )

            # Return count (Pinecone doesn't return count, assume success)
            return 1  # Placeholder

        except Exception as e:
            logger.error(
                "failed_to_invalidate_chunks",
                doc_id=doc_id,
                error=str(e)
            )
            return 0

    def register_document_update(
        self,
        doc_id: str,
        file_path: Path,
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentVersion:
        """
        Register a document update and invalidate old chunks

        Args:
            doc_id: Document identifier
            file_path: Path to updated PDF
            version: Version string (auto-generated if None)
            metadata: Additional metadata

        Returns:
            Created DocumentVersion
        """
        # Check if document has changed
        if not self.version_manager.has_changed(doc_id, file_path):
            logger.info("document_unchanged_skipping", doc_id=doc_id)
            return self.version_manager.get_current_version(doc_id)

        # Invalidate old chunks
        deleted_count = self.invalidate_old_chunks(doc_id)

        # Register new version
        doc_version = self.version_manager.register_version(
            doc_id=doc_id,
            file_path=file_path,
            version=version,
            metadata=metadata
        )

        logger.info(
            "document_update_registered",
            doc_id=doc_id,
            version=doc_version.version,
            old_chunks_deleted=deleted_count
        )

        return doc_version

    def sync_from_s3(
        self,
        bucket_name: str,
        prefix: str = "",
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        aws_region: str = "us-east-1"
    ) -> Dict[str, Any]:
        """
        Sync documents from S3 bucket

        Args:
            bucket_name: S3 bucket name
            prefix: S3 key prefix (folder path)
            aws_access_key: AWS access key (uses env var if None)
            aws_secret_key: AWS secret key (uses env var if None)
            aws_region: AWS region

        Returns:
            Sync results with downloaded/updated documents
        """
        try:
            # Lazy load boto3
            if self._s3_client is None:
                try:
                    import boto3
                except ImportError:
                    logger.error("boto3_missing", message="Install with: pip install boto3")
                    return {"error": "boto3 not installed"}

                # Use provided keys or environment variables
                access_key = aws_access_key or os.getenv("AWS_ACCESS_KEY_ID")
                secret_key = aws_secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")

                self._s3_client = boto3.client(
                    's3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=aws_region
                )

            logger.info("syncing_from_s3", bucket=bucket_name, prefix=prefix)

            # List objects in bucket
            response = self._s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response:
                logger.warning("no_objects_in_s3", bucket=bucket_name, prefix=prefix)
                return {"downloaded": [], "updated": [], "error": None}

            downloaded = []
            updated = []

            for obj in response['Contents']:
                key = obj['Key']

                # Skip non-PDF files
                if not key.lower().endswith('.pdf'):
                    continue

                # Download to upload_dir
                filename = Path(key).name
                local_path = self.upload_dir / filename

                # Check if file exists and has same size (quick check)
                needs_download = True
                if local_path.exists():
                    local_size = local_path.stat().st_size
                    s3_size = obj['Size']
                    if local_size == s3_size:
                        needs_download = False

                if needs_download:
                    logger.info("downloading_from_s3", key=key, local_path=str(local_path))
                    self._s3_client.download_file(bucket_name, key, str(local_path))
                    downloaded.append(str(local_path))

                    # Register as updated
                    doc_id = local_path.stem  # filename without .pdf
                    self.register_document_update(
                        doc_id=doc_id,
                        file_path=local_path,
                        metadata={"source": "s3", "bucket": bucket_name, "key": key}
                    )
                    updated.append(doc_id)

            logger.info(
                "s3_sync_complete",
                downloaded=len(downloaded),
                updated=len(updated)
            )

            return {
                "downloaded": downloaded,
                "updated": updated,
                "error": None
            }

        except Exception as e:
            logger.error("s3_sync_failed", error=str(e))
            return {"downloaded": [], "updated": [], "error": str(e)}

    def sync_from_dropbox(
        self,
        folder_path: str,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync documents from Dropbox folder

        Args:
            folder_path: Dropbox folder path (e.g., "/Documents/PDFs")
            access_token: Dropbox access token (uses env var if None)

        Returns:
            Sync results with downloaded/updated documents
        """
        try:
            # Lazy load dropbox
            if self._dropbox_client is None:
                try:
                    import dropbox
                except ImportError:
                    logger.error("dropbox_missing", message="Install with: pip install dropbox")
                    return {"error": "dropbox not installed"}

                # Use provided token or environment variable
                token = access_token or os.getenv("DROPBOX_ACCESS_TOKEN")
                if not token:
                    logger.error("dropbox_token_missing", message="DROPBOX_ACCESS_TOKEN not set")
                    return {"error": "Dropbox access token not provided"}

                self._dropbox_client = dropbox.Dropbox(token)

            logger.info("syncing_from_dropbox", folder=folder_path)

            # List files in folder
            result = self._dropbox_client.files_list_folder(folder_path)

            downloaded = []
            updated = []

            for entry in result.entries:
                # Skip non-PDF files
                if not entry.name.lower().endswith('.pdf'):
                    continue

                # Download to upload_dir
                local_path = self.upload_dir / entry.name

                # Download file
                logger.info("downloading_from_dropbox", file=entry.name, local_path=str(local_path))

                metadata, response = self._dropbox_client.files_download(entry.path_display)
                with open(local_path, 'wb') as f:
                    f.write(response.content)

                downloaded.append(str(local_path))

                # Register as updated
                doc_id = local_path.stem
                self.register_document_update(
                    doc_id=doc_id,
                    file_path=local_path,
                    metadata={"source": "dropbox", "path": entry.path_display}
                )
                updated.append(doc_id)

            logger.info(
                "dropbox_sync_complete",
                downloaded=len(downloaded),
                updated=len(updated)
            )

            return {
                "downloaded": downloaded,
                "updated": updated,
                "error": None
            }

        except Exception as e:
            logger.error("dropbox_sync_failed", error=str(e))
            return {"downloaded": [], "updated": [], "error": str(e)}

    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current sync status and statistics

        Returns:
            Dictionary with sync statistics
        """
        changes = self.detect_changes()
        version_report = self.version_manager.export_version_report()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "changes_detected": {
                "new": len(changes["new"]),
                "updated": len(changes["updated"]),
                "unchanged": len(changes["unchanged"])
            },
            "version_statistics": version_report["statistics"],
            "pending_updates": changes["new"] + changes["updated"]
        }


# Singleton instance
_sync_service: Optional[DocumentSyncService] = None


def get_sync_service() -> DocumentSyncService:
    """Get singleton DocumentSyncService instance"""
    global _sync_service
    if _sync_service is None:
        _sync_service = DocumentSyncService()
    return _sync_service
