"""
Document Versioning Utility
Tracks document versions, detects changes, and manages version history
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger()


class DocumentVersion:
    """Represents a document version"""

    def __init__(
        self,
        doc_id: str,
        version: str,
        file_path: str,
        file_hash: str,
        last_updated: str,
        supersedes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.doc_id = doc_id
        self.version = version
        self.file_path = file_path
        self.file_hash = file_hash
        self.last_updated = last_updated
        self.supersedes = supersedes
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "doc_id": self.doc_id,
            "version": self.version,
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "last_updated": self.last_updated,
            "supersedes": self.supersedes,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentVersion':
        """Create from dictionary"""
        return cls(
            doc_id=data["doc_id"],
            version=data["version"],
            file_path=data["file_path"],
            file_hash=data["file_hash"],
            last_updated=data["last_updated"],
            supersedes=data.get("supersedes"),
            metadata=data.get("metadata", {})
        )


class DocumentVersionManager:
    """
    Manages document versions and change detection

    Features:
    - Version tracking with metadata
    - SHA256 hash-based change detection
    - Version history storage
    - Superseded version tracking
    """

    def __init__(self, version_db_path: Optional[Path] = None):
        """
        Initialize version manager

        Args:
            version_db_path: Path to version database JSON file
                            Defaults to backend/data/versions/versions.json
        """
        if version_db_path is None:
            # Default to backend/data/versions/versions.json
            base_dir = Path(__file__).parent.parent.parent
            version_db_path = base_dir / "data" / "versions" / "versions.json"

        self.version_db_path = Path(version_db_path)
        self.version_db_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing versions
        self.versions: Dict[str, List[DocumentVersion]] = self._load_versions()

    def _load_versions(self) -> Dict[str, List[DocumentVersion]]:
        """Load versions from database"""
        if not self.version_db_path.exists():
            return {}

        try:
            with open(self.version_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            versions = {}
            for doc_id, version_list in data.items():
                versions[doc_id] = [
                    DocumentVersion.from_dict(v) for v in version_list
                ]

            logger.info(
                "versions_loaded",
                document_count=len(versions),
                total_versions=sum(len(v) for v in versions.values())
            )

            return versions

        except Exception as e:
            logger.error("failed_to_load_versions", error=str(e))
            return {}

    def _save_versions(self):
        """Save versions to database"""
        try:
            data = {
                doc_id: [v.to_dict() for v in version_list]
                for doc_id, version_list in self.versions.items()
            }

            with open(self.version_db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug("versions_saved", path=str(self.version_db_path))

        except Exception as e:
            logger.error("failed_to_save_versions", error=str(e))

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """
        Compute SHA256 hash of a file

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string
        """
        sha256 = hashlib.sha256()

        try:
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                while chunk := f.read(8192):
                    sha256.update(chunk)

            return sha256.hexdigest()

        except Exception as e:
            logger.error("failed_to_compute_hash", file=str(file_path), error=str(e))
            raise

    def get_current_version(self, doc_id: str) -> Optional[DocumentVersion]:
        """
        Get current (latest) version of a document

        Args:
            doc_id: Document identifier

        Returns:
            Latest DocumentVersion or None if not found
        """
        if doc_id not in self.versions or not self.versions[doc_id]:
            return None

        # Latest version is last in list
        return self.versions[doc_id][-1]

    def get_version_history(self, doc_id: str) -> List[DocumentVersion]:
        """
        Get full version history for a document

        Args:
            doc_id: Document identifier

        Returns:
            List of DocumentVersion objects (oldest to newest)
        """
        return self.versions.get(doc_id, [])

    def has_changed(self, doc_id: str, file_path: Path) -> bool:
        """
        Check if a document has changed since last version

        Args:
            doc_id: Document identifier
            file_path: Path to current file

        Returns:
            True if changed (or new document), False if unchanged
        """
        current_version = self.get_current_version(doc_id)

        if current_version is None:
            # New document
            return True

        # Compare hashes
        current_hash = self.compute_file_hash(file_path)
        return current_hash != current_version.file_hash

    def register_version(
        self,
        doc_id: str,
        file_path: Path,
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentVersion:
        """
        Register a new version of a document

        Args:
            doc_id: Document identifier
            file_path: Path to document file
            version: Version string (e.g., "v2.1") - auto-generated if None
            metadata: Additional metadata

        Returns:
            Created DocumentVersion
        """
        # Compute file hash
        file_hash = self.compute_file_hash(file_path)

        # Get current version for supersedes tracking
        current = self.get_current_version(doc_id)
        supersedes = current.version if current else None

        # Auto-generate version if not provided
        if version is None:
            if current is None:
                version = "v1.0"
            else:
                # Parse version and increment
                try:
                    # Extract numeric parts from version (e.g., "v2.1" -> [2, 1])
                    version_parts = current.version.lstrip('v').split('.')
                    major, minor = int(version_parts[0]), int(version_parts[1]) if len(version_parts) > 1 else 0

                    # Increment minor version
                    minor += 1
                    version = f"v{major}.{minor}"

                except (ValueError, IndexError):
                    # Fallback to timestamp-based version
                    version = f"v_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Create version object
        doc_version = DocumentVersion(
            doc_id=doc_id,
            version=version,
            file_path=str(file_path),
            file_hash=file_hash,
            last_updated=datetime.utcnow().isoformat(),
            supersedes=supersedes,
            metadata=metadata or {}
        )

        # Add to version history
        if doc_id not in self.versions:
            self.versions[doc_id] = []

        self.versions[doc_id].append(doc_version)

        # Save to database
        self._save_versions()

        logger.info(
            "version_registered",
            doc_id=doc_id,
            version=version,
            supersedes=supersedes,
            file_hash=file_hash[:12]
        )

        return doc_version

    def detect_updates(self, upload_dir: Path) -> Dict[str, Dict[str, Any]]:
        """
        Scan upload directory and detect document updates

        Args:
            upload_dir: Directory containing uploaded PDFs

        Returns:
            Dictionary with update info:
            {
                "new": [doc_ids...],
                "updated": [doc_ids...],
                "unchanged": [doc_ids...],
                "details": {doc_id: {old_hash, new_hash, file_path}}
            }
        """
        new_docs = []
        updated_docs = []
        unchanged_docs = []
        details = {}

        # Scan all PDFs in upload directory (recursive)
        pdf_files = list(upload_dir.rglob("*.pdf"))

        for pdf_path in pdf_files:
            # Use relative path as doc_id (without .pdf extension)
            relative_path = pdf_path.relative_to(upload_dir)
            doc_id = str(relative_path.with_suffix('')).replace('/', '_')

            current_version = self.get_current_version(doc_id)
            new_hash = self.compute_file_hash(pdf_path)

            if current_version is None:
                # New document
                new_docs.append(doc_id)
                details[doc_id] = {
                    "status": "new",
                    "old_hash": None,
                    "new_hash": new_hash,
                    "file_path": str(pdf_path)
                }
            elif new_hash != current_version.file_hash:
                # Updated document
                updated_docs.append(doc_id)
                details[doc_id] = {
                    "status": "updated",
                    "old_hash": current_version.file_hash,
                    "new_hash": new_hash,
                    "old_version": current_version.version,
                    "file_path": str(pdf_path)
                }
            else:
                # Unchanged document
                unchanged_docs.append(doc_id)
                details[doc_id] = {
                    "status": "unchanged",
                    "hash": new_hash,
                    "version": current_version.version,
                    "file_path": str(pdf_path)
                }

        logger.info(
            "update_detection_complete",
            new=len(new_docs),
            updated=len(updated_docs),
            unchanged=len(unchanged_docs),
            total=len(pdf_files)
        )

        return {
            "new": new_docs,
            "updated": updated_docs,
            "unchanged": unchanged_docs,
            "details": details
        }

    def get_superseded_versions(self, doc_id: str) -> List[DocumentVersion]:
        """
        Get all superseded (old) versions of a document

        Args:
            doc_id: Document identifier

        Returns:
            List of superseded versions (oldest to newest, excluding current)
        """
        history = self.get_version_history(doc_id)

        if len(history) <= 1:
            return []

        # All versions except the last (current) one
        return history[:-1]

    def export_version_report(self) -> Dict[str, Any]:
        """
        Export version report for all documents

        Returns:
            Dictionary with version statistics and details
        """
        total_documents = len(self.versions)
        total_versions = sum(len(v) for v in self.versions.values())
        versioned_docs = sum(1 for v in self.versions.values() if len(v) > 1)

        documents = []
        for doc_id, version_list in self.versions.items():
            current = version_list[-1]
            documents.append({
                "doc_id": doc_id,
                "current_version": current.version,
                "version_count": len(version_list),
                "last_updated": current.last_updated,
                "file_hash": current.file_hash[:12],
                "has_history": len(version_list) > 1
            })

        # Sort by last updated (newest first)
        documents.sort(key=lambda x: x["last_updated"], reverse=True)

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "statistics": {
                "total_documents": total_documents,
                "total_versions": total_versions,
                "documents_with_history": versioned_docs,
                "average_versions_per_doc": round(total_versions / max(total_documents, 1), 2)
            },
            "documents": documents
        }


# Singleton instance
_version_manager: Optional[DocumentVersionManager] = None


def get_version_manager() -> DocumentVersionManager:
    """Get singleton DocumentVersionManager instance"""
    global _version_manager
    if _version_manager is None:
        _version_manager = DocumentVersionManager()
    return _version_manager
