"""
Document Management Routes
Endpoints for uploading, processing, and managing knowledge base documents
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import structlog
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.middleware.auth import verify_api_key
from app.api.routes.protocols import clear_protocols_cache
from app.api.routes.products import clear_products_cache
from app.utils.metadata_enrichment import build_canonical_metadata

router = APIRouter(dependencies=[Depends(verify_api_key)])
logger = structlog.get_logger()


def _safe_vector_id(value: str) -> str:
    """
    Normalize IDs to ASCII-safe strings for Pinecone vector IDs.
    """
    import re
    safe = value.encode("ascii", "ignore").decode("ascii")
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", safe).strip("_").lower()
    return safe or "doc"


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class DocumentMetadata(BaseModel):
    """Document metadata"""
    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    doc_type: str = Field(..., description="Document type (product, protocol, clinical_paper, etc.)")
    upload_date: datetime = Field(..., description="Upload timestamp")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Processing status (pending, processing, completed, failed)")
    num_chunks: Optional[int] = Field(None, description="Number of chunks created")
    namespace: Optional[str] = Field(None, description="Pinecone namespace")
    
    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "doc_plinest_factsheet_001",
                "filename": "Plinest_Product_Sheet.pdf",
                "doc_type": "product",
                "upload_date": "2025-01-08T10:30:00Z",
                "file_size": 524288,
                "status": "completed",
                "num_chunks": 15,
                "namespace": "products"
            }
        }


class DocumentListResponse(BaseModel):
    """List of documents response"""
    total: int = Field(..., description="Total number of documents")
    documents: List[DocumentMetadata] = Field(..., description="List of documents")


class DocumentUploadResponse(BaseModel):
    """Document upload response"""
    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")


class ProcessingStatus(BaseModel):
    """Document processing status"""
    doc_id: str
    status: str
    progress: int = Field(..., ge=0, le=100, description="Processing progress (0-100)")
    message: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# ==============================================================================
# PINECONE INDEXING HELPER
# ==============================================================================

async def index_chunks_to_pinecone(
    chunks: List[dict],
    doc_id: str,
    doc_type: str,
    namespace: str = "default"
) -> int:
    """
    Embed document chunks and upload to Pinecone vector database.

    Args:
        chunks: List of chunk dictionaries with 'text' and 'metadata'
        doc_id: Document identifier
        doc_type: Type of document
        namespace: Pinecone namespace

    Returns:
        Number of vectors successfully indexed
    """
    from app.services.embedding_service import get_embedding_service
    from app.services.pinecone_service import get_pinecone_service

    embedding_service = get_embedding_service()
    pinecone_service = get_pinecone_service()

    logger.info(
        "indexing_chunks_to_pinecone",
        doc_id=doc_id,
        num_chunks=len(chunks),
        namespace=namespace
    )

    if not chunks:
        return 0

    # Extract texts for embedding
    texts = [chunk.get('text', '') for chunk in chunks]

    # Generate embeddings in batch
    embeddings = await run_in_threadpool(
        embedding_service.generate_embeddings_batch,
        texts
    )

    # Prepare vectors for Pinecone
    vectors = []
    skipped = 0
    safe_doc_id = _safe_vector_id(doc_id)
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        text = (chunk.get('text', '') or '').strip()
        if not text or embedding is None:
            skipped += 1
            continue

        vector_id = f"{safe_doc_id}_chunk_{i}"
        metadata = build_canonical_metadata(
            doc_id=doc_id,
            doc_type=doc_type,
            chunk_index=i,
            text=text,
            metadata=chunk.get('metadata', {})
        )
        metadata["doc_id_safe"] = safe_doc_id

        vectors.append({
            'id': vector_id,
            'values': embedding,
            'metadata': metadata
        })

    if skipped:
        logger.warning(
            "chunks_skipped_empty_text",
            doc_id=doc_id,
            skipped=skipped
        )

    if not vectors:
        logger.warning(
            "no_vectors_to_upsert",
            doc_id=doc_id,
            namespace=namespace
        )
        return 0

    # Upsert to Pinecone
    result = await run_in_threadpool(
        pinecone_service.upsert_vectors,
        vectors,
        namespace=namespace
    )

    logger.info(
        "chunks_indexed_successfully",
        doc_id=doc_id,
        upserted_count=result.get('upserted_count', 0)
    )

    return result.get('upserted_count', 0)


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Query(..., description="Document type: product, protocol, clinical_paper, video, case_study"),
    namespace: Optional[str] = Query(None, description="Custom namespace (optional)")
):
    """
    Upload and process a document
    
    Process:
    1. Validate file type and size
    2. Save to upload directory
    3. Process document (extract text, chunk)
    4. Save processed data
    
    Supported formats: PDF, DOCX, TXT, MP4, MOV
    
    Phase 2: Now includes real PDF processing!
    Phase 3: Will add Pinecone upload
    """
    logger.info(
        "document_upload_started",
        filename=file.filename,
        content_type=file.content_type,
        doc_type=doc_type
    )
    if any(ord(ch) > 127 for ch in file.filename):
        safe_name = _safe_vector_id(Path(file.filename).stem)
        logger.warning(
            "non_ascii_filename_detected",
            filename=file.filename,
            safe_id=safe_name
        )
    
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if file_ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed. Allowed: {settings.allowed_extensions}"
        )
    
    # Validate document type
    valid_doc_types = ["product", "protocol", "clinical_paper", "video", "case_study", "other"]
    if doc_type not in valid_doc_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid doc_type. Must be one of: {valid_doc_types}"
        )
    
    # Generate doc_id
    doc_id = f"doc_{doc_type}_{int(datetime.utcnow().timestamp())}"
    
    # Ensure upload directory exists
    import os
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # Save uploaded file
    file_path = os.path.join(settings.upload_dir, f"{doc_id}{file_ext}")
    
    try:
        import shutil
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(
            "file_saved",
            doc_id=doc_id,
            file_path=file_path
        )
        
        # Process the document
        from app.utils.document_processor import DocumentProcessor
        from app.utils.video_processor import VideoProcessor, is_video_processing_available
        
        if file_ext == '.pdf':
            processor = DocumentProcessor()
            result = processor.process_pdf(file_path, doc_id=doc_id, doc_type=doc_type)

            # Save processed data
            os.makedirs(settings.processed_dir, exist_ok=True)
            import json
            processed_file = os.path.join(settings.processed_dir, f"{doc_id}_processed.json")
            with open(processed_file, 'w') as f:
                json.dump(result, f, indent=2)

            logger.info(
                "document_processed",
                doc_id=doc_id,
                num_chunks=result['stats']['num_chunks']
            )

            # CRITICAL: Embed chunks and upload to Pinecone
            num_indexed = await index_chunks_to_pinecone(
                chunks=result['chunks'],
                doc_id=doc_id,
                doc_type=doc_type,
                namespace=namespace or "default"
            )

            logger.info(
                "document_indexed_to_pinecone",
                doc_id=doc_id,
                num_indexed=num_indexed
            )

            # Auto-invalidate both protocol and product caches
            clear_protocols_cache()
            clear_products_cache()
            logger.info("cleared_caches", reason="pdf_document_uploaded")

            return DocumentUploadResponse(
                doc_id=doc_id,
                filename=file.filename,
                status="completed",
                message=f"Document processed and indexed. {result['stats']['num_chunks']} chunks created, {num_indexed} vectors indexed to Pinecone."
            )
        
        elif file_ext in ['.mp4', '.mov', '.avi']:
            if not is_video_processing_available():
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Video processing not available. Install: openai-whisper, moviepy"
                )
            
            video_processor = VideoProcessor()
            result = video_processor.process_video(
                file_path,
                doc_id=doc_id,
                doc_type=doc_type,
                extract_keyframes=settings.enable_keyframe_extraction or settings.enable_image_analysis,
                keyframe_count=settings.video_keyframe_count
            )

            # Save processed data
            os.makedirs(settings.processed_dir, exist_ok=True)
            import json
            processed_file = os.path.join(settings.processed_dir, f"{doc_id}_processed.json")
            with open(processed_file, 'w') as f:
                json.dump(result, f, indent=2)

            logger.info(
                "video_processed",
                doc_id=doc_id,
                num_chunks=result['stats']['num_chunks']
            )

            # CRITICAL: Embed chunks and upload to Pinecone
            num_indexed = await index_chunks_to_pinecone(
                chunks=result['chunks'],
                doc_id=doc_id,
                doc_type=doc_type,
                namespace=namespace or "default"
            )

            logger.info(
                "video_indexed_to_pinecone",
                doc_id=doc_id,
                num_indexed=num_indexed
            )

            # Auto-invalidate both protocol and product caches
            clear_protocols_cache()
            clear_products_cache()
            logger.info("cleared_caches", reason="video_document_uploaded")

            return DocumentUploadResponse(
                doc_id=doc_id,
                filename=file.filename,
                status="completed",
                message=f"Video transcribed and indexed. {result['stats']['num_chunks']} chunks created, {num_indexed} vectors indexed to Pinecone."
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file_ext} not yet supported"
            )
    
    except Exception as e:
        logger.error(
            "document_processing_failed",
            doc_id=doc_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@router.get("/", response_model=DocumentListResponse, status_code=status.HTTP_200_OK)
async def list_documents(
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of documents to return"),
    offset: int = Query(0, ge=0, description="Number of documents to skip")
):
    """
    List all indexed documents
    
    Returns: Paginated list of documents with metadata
    
    Phase 2: Now shows uploaded and processed documents!
    """
    logger.info(
        "list_documents_request",
        doc_type=doc_type,
        status_filter=status_filter,
        limit=limit,
        offset=offset
    )
    
    import os
    import json
    from pathlib import Path
    
    documents = []
    
    # Check upload directory
    if os.path.exists(settings.upload_dir):
        for filename in os.listdir(settings.upload_dir):
            if not filename.startswith('.'):
                file_path = os.path.join(settings.upload_dir, filename)
                
                # Extract doc_id (filename without extension)
                doc_id = Path(filename).stem
                
                # Determine doc type from ID
                determined_type = "other"
                for dtype in ["product", "protocol", "clinical_paper", "video", "case_study"]:
                    if doc_id.startswith(f"doc_{dtype}"):
                        determined_type = dtype
                        break
                
                # Filter by doc_type if specified
                if doc_type and determined_type != doc_type:
                    continue
                
                # Check if processed
                processed_file = os.path.join(settings.processed_dir, f"{doc_id}_processed.json")
                is_processed = os.path.exists(processed_file)
                
                doc_status = "completed" if is_processed else "pending"
                
                # Filter by status if specified
                if status_filter and doc_status != status_filter:
                    continue
                
                # Get stats from processed file
                num_chunks = None
                if is_processed:
                    try:
                        with open(processed_file) as f:
                            data = json.load(f)
                            num_chunks = data.get('stats', {}).get('num_chunks')
                    except:
                        pass
                
                # Get file stats
                stat = os.stat(file_path)
                upload_date = datetime.fromtimestamp(stat.st_mtime)
                
                documents.append(DocumentMetadata(
                    doc_id=doc_id,
                    filename=filename,
                    doc_type=determined_type,
                    upload_date=upload_date,
                    file_size=stat.st_size,
                    status=doc_status,
                    num_chunks=num_chunks,
                    namespace=determined_type + "s" if is_processed else None
                ))
    
    # Apply pagination
    total = len(documents)
    documents = documents[offset:offset + limit]
    
    return DocumentListResponse(
        total=total,
        documents=documents
    )


# ==============================================================================
# PDF VIEWING ENDPOINTS (For Clickable Citations)
# IMPORTANT: These must come BEFORE the /{doc_id} catch-all route!
# ==============================================================================

from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import os


class DocumentViewInfo(BaseModel):
    """Information for viewing a document"""
    doc_id: str
    title: str
    file_path: str
    file_exists: bool
    total_pages: Optional[int] = None
    file_size: int = 0
    view_url: str
    download_url: str


@router.get("/view", response_class=HTMLResponse)
async def view_document_page(
    doc_id: str = Query(..., description="Document ID to view"),
    page: int = Query(1, ge=1, description="Page number to display")
):
    """
    View a document in the browser with PDF.js viewer
    """
    from app.services.citation_service import get_citation_service
    from urllib.parse import quote

    citation_service = get_citation_service()
    file_path = citation_service.get_document_path(doc_id)

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found"
        )

    title = citation_service.get_document_title(doc_id)
    # URL-encode the doc_id for use in URLs
    encoded_doc_id = quote(doc_id)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - DermaFocus</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; }}
            .header {{ background: #16213e; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #0f3460; }}
            .header h1 {{ font-size: 16px; font-weight: 500; }}
            .header .page-info {{ font-size: 14px; color: #888; }}
            .header .actions {{ display: flex; gap: 10px; }}
            .header button {{ background: #0f3460; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; }}
            .header button:hover {{ background: #1a4980; }}
            .pdf-container {{ width: 100%; height: calc(100vh - 60px); }}
            iframe {{ width: 100%; height: 100%; border: none; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{title}</h1>
            <span class="page-info">Page {page}</span>
            <div class="actions">
                <button onclick="window.history.back()">Back</button>
                <button onclick="downloadPDF()">Download PDF</button>
            </div>
        </div>
        <div class="pdf-container">
            <iframe id="pdf-viewer" src="/api/documents/file/{encoded_doc_id}#page={page}" title="{title}"></iframe>
        </div>
        <script>
            function downloadPDF() {{ window.location.href = '/api/documents/download/{encoded_doc_id}'; }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/file/{doc_id}")
async def get_document_file(doc_id: str):
    """Serve the actual PDF file for embedding"""
    from app.services.citation_service import get_citation_service

    citation_service = get_citation_service()
    file_path = citation_service.get_document_path(doc_id)

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found"
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={os.path.basename(file_path)}"}
    )


@router.get("/download/{doc_id}")
async def download_document(doc_id: str):
    """Download the PDF file"""
    from app.services.citation_service import get_citation_service

    citation_service = get_citation_service()
    file_path = citation_service.get_document_path(doc_id)

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found"
        )

    title = citation_service.get_document_title(doc_id)
    safe_filename = "".join(c for c in title if c.isalnum() or c in " -_").strip() + ".pdf"

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=safe_filename,
        headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
    )


@router.get("/info/{doc_id}", response_model=DocumentViewInfo)
async def get_document_info(doc_id: str):
    """Get document information for the frontend"""
    from app.services.citation_service import get_citation_service

    citation_service = get_citation_service()
    file_path = citation_service.get_document_path(doc_id)
    title = citation_service.get_document_title(doc_id)

    file_exists = file_path is not None and os.path.exists(file_path)
    file_size = os.path.getsize(file_path) if file_exists else 0

    total_pages = None
    if file_exists:
        try:
            import fitz
            doc = fitz.open(file_path)
            total_pages = len(doc)
            doc.close()
        except:
            pass

    return DocumentViewInfo(
        doc_id=doc_id,
        title=title,
        file_path=file_path or "",
        file_exists=file_exists,
        total_pages=total_pages,
        file_size=file_size,
        view_url=f"/api/documents/view?doc_id={doc_id}",
        download_url=f"/api/documents/download/{doc_id}"
    )


@router.get("/sources/list")
async def list_available_sources():
    """List all available source documents that can be cited"""
    from app.services.citation_service import get_citation_service

    citation_service = get_citation_service()

    sources = []
    for doc_id, file_path in citation_service._doc_path_cache.items():
        if doc_id != citation_service._normalize_doc_id(doc_id):
            continue
        if os.path.exists(file_path):
            path_parts = Path(file_path).parts
            category = "Other"
            for part in path_parts:
                if part in ["Clinical Papers", "Case Studies", "Fact Sheets", "Brochures", "Protocols"]:
                    category = part
                    break
            sources.append({
                "doc_id": doc_id,
                "title": citation_service.get_document_title(doc_id),
                "category": category,
                "file_path": file_path,
                "view_url": f"/api/documents/view?doc_id={doc_id}"
            })

    return {
        "total": len(sources),
        "sources": sorted(sources, key=lambda x: (x["category"], x["title"]))
    }


# ==============================================================================
# CATCH-ALL ROUTES (Must come AFTER specific routes)
# ==============================================================================

@router.get("/{doc_id}", response_model=DocumentMetadata, status_code=status.HTTP_200_OK)
async def get_document(doc_id: str):
    """
    Get document metadata
    
    Args:
        doc_id: Unique document identifier
    
    Returns: Document metadata
    
    NOTE: This is a placeholder. Implementation in Phase 2.
    """
    # TODO: Phase 2 - Retrieve document metadata from database
    # from app.services.document_service import DocumentService
    # doc_service = DocumentService()
    # document = await doc_service.get_document(doc_id)
    # if not document:
    #     raise HTTPException(status_code=404, detail="Document not found")
    # return document
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Document {doc_id} not found. Document management not yet implemented."
    )


@router.get("/{doc_id}/status", response_model=ProcessingStatus, status_code=status.HTTP_200_OK)
async def get_processing_status(doc_id: str):
    """
    Get document processing status
    
    Args:
        doc_id: Unique document identifier
    
    Returns: Current processing status and progress
    
    NOTE: This is a placeholder. Implementation in Phase 2.
    """
    # TODO: Phase 2 - Check processing status
    # from app.services.document_service import DocumentService
    # doc_service = DocumentService()
    # status = await doc_service.get_processing_status(doc_id)
    # return status
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Document {doc_id} not found. Document processing not yet implemented."
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    namespace: str = Query(default="default", description="Pinecone namespace")
):
    """
    Delete a document from the knowledge base

    This will:
    1. Delete vectors from Pinecone
    2. Remove processed JSON file
    3. Remove uploaded file from storage

    Args:
        doc_id: Unique document identifier
        namespace: Pinecone namespace where vectors are stored
    """
    import os
    import glob

    logger.info("document_deletion_requested", doc_id=doc_id, namespace=namespace)

    try:
        from app.services.pinecone_service import get_pinecone_service
        pinecone_service = get_pinecone_service()

        # Delete vectors from Pinecone using metadata filter
        # We need to delete all vectors with matching doc_id
        pinecone_service.delete_vectors(
            filter={"doc_id": {"$eq": doc_id}},
            namespace=namespace
        )
        logger.info("vectors_deleted_from_pinecone", doc_id=doc_id)

        # Delete processed JSON file
        processed_file = os.path.join(settings.processed_dir, f"{doc_id}_processed.json")
        if os.path.exists(processed_file):
            os.remove(processed_file)
            logger.info("processed_file_deleted", file=processed_file)

        # Delete uploaded file (find by doc_id prefix)
        upload_pattern = os.path.join(settings.upload_dir, f"{doc_id}.*")
        for file_path in glob.glob(upload_pattern):
            os.remove(file_path)
            logger.info("uploaded_file_deleted", file=file_path)

        # Invalidate caches
        clear_protocols_cache()
        clear_products_cache()
        logger.info("caches_cleared", reason="document_deleted")

        logger.info("document_deleted_successfully", doc_id=doc_id)

    except Exception as e:
        logger.error("document_deletion_failed", doc_id=doc_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.post("/{doc_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_document(doc_id: str):
    """
    Reprocess a document (useful after processing failures or updates)

    Args:
        doc_id: Unique document identifier

    Returns: Processing status

    NOTE: This is a placeholder. Implementation in Phase 2.
    """
    logger.info("document_reprocess_requested", doc_id=doc_id)

    # TODO: Phase 2 - Implement reprocessing
    # from app.services.document_service import DocumentService
    # doc_service = DocumentService()
    # await doc_service.reprocess_document(doc_id)

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document reprocessing not yet implemented."
    )
