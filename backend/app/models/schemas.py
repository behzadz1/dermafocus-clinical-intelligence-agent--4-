"""
Pydantic Models and Schemas
Shared data models used across the application
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ==============================================================================
# ENUMS
# ==============================================================================

class DocumentType(str, Enum):
    """Document type enumeration"""
    PRODUCT = "product"
    PROTOCOL = "protocol"
    CLINICAL_PAPER = "clinical_paper"
    VIDEO = "video"
    CASE_STUDY = "case_study"
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IntentType(str, Enum):
    """Query intent classification"""
    PRODUCT_INFO = "product_info"
    INJECTION_PROTOCOL = "injection_protocol"
    CLINICAL_EVIDENCE = "clinical_evidence"
    PRODUCT_COMPARISON = "product_comparison"
    COMPLICATION = "complication"
    CONTRAINDICATION = "contraindication"
    GENERAL = "general"


class MessageRole(str, Enum):
    """Message role in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ==============================================================================
# DOCUMENT MODELS
# ==============================================================================

class DocumentChunk(BaseModel):
    """Single chunk of a document"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Parent document ID")
    text: str = Field(..., description="Chunk text content")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    
    @field_validator('text')
    @classmethod
    def text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Chunk text cannot be empty")
        return v


class Document(BaseModel):
    """Document model"""
    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    doc_type: DocumentType = Field(..., description="Document type")
    status: DocumentStatus = Field(default=DocumentStatus.PENDING, description="Processing status")
    file_path: str = Field(..., description="Path to stored file")
    file_size: int = Field(..., description="File size in bytes")
    upload_date: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    processed_date: Optional[datetime] = Field(None, description="Processing completion timestamp")
    namespace: str = Field(..., description="Pinecone namespace")
    num_chunks: Optional[int] = Field(None, description="Number of chunks created")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


# ==============================================================================
# CONVERSATION MODELS
# ==============================================================================

class Message(BaseModel):
    """Single message in a conversation"""
    message_id: str = Field(..., description="Unique message identifier")
    conversation_id: str = Field(..., description="Parent conversation ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Conversation(BaseModel):
    """Conversation model"""
    conversation_id: str = Field(..., description="Unique conversation identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    messages: List[Message] = Field(default_factory=list, description="Conversation messages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ==============================================================================
# RAG MODELS
# ==============================================================================

class RAGContext(BaseModel):
    """Context retrieved for RAG"""
    query: str = Field(..., description="Original query")
    retrieved_chunks: List[DocumentChunk] = Field(..., description="Retrieved document chunks")
    intent: IntentType = Field(..., description="Classified intent")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")


class Source(BaseModel):
    """Source citation"""
    document: str = Field(..., description="Document name")
    page: int = Field(..., description="Page number")
    section: Optional[str] = Field(None, description="Section name")
    chunk_id: str = Field(..., description="Chunk identifier")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance score")
    text_snippet: str = Field(..., description="Relevant text snippet", max_length=500)


class RAGResponse(BaseModel):
    """Complete RAG response"""
    answer: str = Field(..., description="Generated answer")
    sources: List[Source] = Field(..., description="Source citations")
    intent: IntentType = Field(..., description="Classified intent")
    confidence: float = Field(..., ge=0, le=1, description="Response confidence")
    follow_ups: List[str] = Field(default_factory=list, description="Suggested follow-up questions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ==============================================================================
# EMBEDDINGS MODELS
# ==============================================================================

class EmbeddingRequest(BaseModel):
    """Request to generate embedding"""
    text: str = Field(..., description="Text to embed", max_length=8000)
    model: Optional[str] = Field(None, description="Embedding model to use")


class EmbeddingResponse(BaseModel):
    """Embedding response"""
    embedding: List[float] = Field(..., description="Vector embedding")
    model: str = Field(..., description="Model used")
    dimensions: int = Field(..., description="Embedding dimensions")


# ==============================================================================
# ANALYTICS MODELS
# ==============================================================================

class QueryLog(BaseModel):
    """Query logging model"""
    query_id: str = Field(..., description="Unique query identifier")
    conversation_id: str = Field(..., description="Conversation identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    query: str = Field(..., description="User query")
    intent: IntentType = Field(..., description="Classified intent")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    sources_count: int = Field(..., description="Number of sources retrieved")
    confidence: float = Field(..., ge=0, le=1, description="Response confidence")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Query timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Feedback(BaseModel):
    """User feedback model"""
    feedback_id: str = Field(..., description="Unique feedback identifier")
    query_id: str = Field(..., description="Associated query ID")
    conversation_id: str = Field(..., description="Conversation identifier")
    message_id: str = Field(..., description="Message identifier")
    feedback_type: str = Field(..., description="Feedback type (thumbs_up, thumbs_down, flag)")
    comment: Optional[str] = Field(None, description="Feedback comment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Feedback timestamp")


# ==============================================================================
# SYSTEM MODELS
# ==============================================================================

class HealthStatus(BaseModel):
    """System health status"""
    status: str = Field(..., description="Overall status (healthy, degraded, unhealthy)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: str = Field(..., description="Application version")
    dependencies: Dict[str, Dict[str, Any]] = Field(..., description="Dependency statuses")


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error detail message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")
