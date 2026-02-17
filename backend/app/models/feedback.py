"""
Feedback Models
User feedback on RAG responses for quality improvement
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class FeedbackRating(str, Enum):
    """Feedback rating types"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class FeedbackCategory(str, Enum):
    """Categories for negative feedback"""
    INCORRECT_INFORMATION = "incorrect_information"
    INCOMPLETE_ANSWER = "incomplete_answer"
    IRRELEVANT_CONTEXT = "irrelevant_context"
    POOR_SOURCES = "poor_sources"
    UNCLEAR_RESPONSE = "unclear_response"
    MISSING_INFORMATION = "missing_information"
    OTHER = "other"


class FeedbackSubmission(BaseModel):
    """Request model for submitting feedback"""
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: Optional[str] = Field(None, description="Specific message ID if available")
    rating: FeedbackRating = Field(..., description="User rating (positive/negative/neutral)")
    category: Optional[FeedbackCategory] = Field(None, description="Category for negative feedback")
    comment: Optional[str] = Field(None, description="User comment/explanation")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv_abc123",
                "message_id": "msg_xyz789",
                "rating": "negative",
                "category": "incomplete_answer",
                "comment": "Missing dosing information for Newest protocol"
            }
        }


class FeedbackRecord(BaseModel):
    """Stored feedback record with full context"""
    id: str = Field(..., description="Unique feedback ID")
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: Optional[str] = Field(None, description="Message ID")
    rating: FeedbackRating = Field(..., description="User rating")
    category: Optional[FeedbackCategory] = Field(None, description="Feedback category")
    comment: Optional[str] = Field(None, description="User comment")

    # Query/response context
    query: str = Field(..., description="User query")
    response: str = Field(..., description="System response")
    confidence: Optional[float] = Field(None, description="Response confidence score")
    sources: Optional[List[str]] = Field(default=[], description="Source documents cited")

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Feedback timestamp")
    user_id: Optional[str] = Field(None, description="User ID if available")
    session_info: Optional[dict] = Field(default={}, description="Additional session information")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "fb_abc123xyz",
                "conversation_id": "conv_abc123",
                "message_id": "msg_xyz789",
                "rating": "negative",
                "category": "incomplete_answer",
                "comment": "Missing dosing information",
                "query": "What is the Newest protocol?",
                "response": "Newest is used for skin rejuvenation...",
                "confidence": 0.87,
                "sources": ["Newest_Factsheet", "Clinical_Protocol"],
                "timestamp": "2026-02-13T10:30:00Z"
            }
        }


class FeedbackResponse(BaseModel):
    """API response after submitting feedback"""
    success: bool = Field(..., description="Whether feedback was recorded")
    feedback_id: str = Field(..., description="Unique feedback ID")
    message: str = Field(..., description="Confirmation message")


class FeedbackStats(BaseModel):
    """Feedback statistics for reporting"""
    total_feedback: int = Field(..., description="Total feedback count")
    positive_count: int = Field(..., description="Positive feedback count")
    negative_count: int = Field(..., description="Negative feedback count")
    neutral_count: int = Field(..., description="Neutral feedback count")

    positive_rate: float = Field(..., description="Positive feedback rate (0-1)")
    negative_rate: float = Field(..., description="Negative feedback rate (0-1)")

    category_breakdown: dict = Field(default={}, description="Breakdown by category")
    avg_confidence: Optional[float] = Field(None, description="Average confidence of rated responses")

    low_rated_queries: List[dict] = Field(default=[], description="Queries with negative feedback")

    class Config:
        json_schema_extra = {
            "example": {
                "total_feedback": 150,
                "positive_count": 120,
                "negative_count": 25,
                "neutral_count": 5,
                "positive_rate": 0.80,
                "negative_rate": 0.167,
                "category_breakdown": {
                    "incomplete_answer": 12,
                    "incorrect_information": 5,
                    "poor_sources": 8
                },
                "avg_confidence": 0.85,
                "low_rated_queries": [
                    {"query": "Newest dosing", "rating": "negative", "count": 3}
                ]
            }
        }
