"""
Document Management Routes
Endpoints for uploading, processing, and managing knowledge base documents
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import structlog

from app.config import settings

router = APIRouter()
logger = structlog.get_logger()


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
            
            return DocumentUploadResponse(
                doc_id=doc_id,
                filename=file.filename,
                status="completed",
                message=f"Document processed successfully. {result['stats']['num_chunks']} chunks created."
            )
        
        elif file_ext in ['.mp4', '.mov', '.avi']:
            if not is_video_processing_available():
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Video processing not available. Install: openai-whisper, moviepy"
                )
            
            video_processor = VideoProcessor()
            result = video_processor.process_video(file_path, doc_id=doc_id, doc_type=doc_type)
            
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
            
            return DocumentUploadResponse(
                doc_id=doc_id,
                filename=file.filename,
                status="completed",
                message=f"Video transcribed successfully. {result['stats']['num_chunks']} chunks created."
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
async def delete_document(doc_id: str):
    """
    Delete a document from the knowledge base
    
    This will:
    1. Remove document from database
    2. Delete vectors from Pinecone
    3. Remove files from storage
    
    Args:
        doc_id: Unique document identifier
    
    NOTE: This is a placeholder. Implementation in Phase 2.
    """
    logger.info("document_deletion_requested", doc_id=doc_id)
    
    # TODO: Phase 2 - Implement document deletion
    # from app.services.document_service import DocumentService
    # from app.services.embedding_service import EmbeddingService
    # 
    # doc_service = DocumentService()
    # embedding_service = EmbeddingService()
    # 
    # # Delete from database
    # await doc_service.delete_document(doc_id)
    # 
    # # Delete from Pinecone
    # await embedding_service.delete_vectors(doc_id)
    # 
    # logger.info("document_deleted", doc_id=doc_id)
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document deletion not yet implemented."
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
