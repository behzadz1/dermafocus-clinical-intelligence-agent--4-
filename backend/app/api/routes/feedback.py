"""
Feedback API Routes
Endpoints for collecting and managing user feedback
"""

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, status
import structlog

from app.models.feedback import (
    FeedbackSubmission,
    FeedbackRecord,
    FeedbackResponse,
    FeedbackStats,
    FeedbackRating,
    FeedbackCategory
)

logger = structlog.get_logger()

router = APIRouter(prefix="/feedback", tags=["feedback"])

# Feedback storage directory
FEEDBACK_DIR = Path(__file__).parent.parent.parent.parent / "data" / "feedback"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


def _get_feedback_file_path(date: datetime = None) -> Path:
    """Get feedback file path for a specific date (one file per day)"""
    if date is None:
        date = datetime.utcnow()
    filename = f"feedback_{date.strftime('%Y%m%d')}.jsonl"
    return FEEDBACK_DIR / filename


def _load_conversation_context(conversation_id: str) -> dict:
    """
    Load conversation context from Redis or storage
    For now, returns empty dict - integrate with conversation storage later
    """
    # TODO: Integrate with conversation persistence from Phase 1.2
    # For now, return empty context - frontend should include query/response
    return {}


@router.post("/submit", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(feedback: FeedbackSubmission):
    """
    Submit user feedback on a response

    Args:
        feedback: Feedback submission with rating and optional comment

    Returns:
        Confirmation with feedback ID
    """
    try:
        # Generate unique feedback ID
        feedback_id = f"fb_{uuid.uuid4().hex[:12]}"

        # Load conversation context (if available)
        # In Phase 1.2 we added conversation persistence - integrate here
        context = _load_conversation_context(feedback.conversation_id)

        # Create feedback record
        record = FeedbackRecord(
            id=feedback_id,
            conversation_id=feedback.conversation_id,
            message_id=feedback.message_id,
            rating=feedback.rating,
            category=feedback.category,
            comment=feedback.comment,
            query=context.get("query", ""),  # Will be empty for now
            response=context.get("response", ""),
            confidence=context.get("confidence"),
            sources=context.get("sources", []),
            timestamp=datetime.utcnow()
        )

        # Save to JSONL file (one file per day)
        feedback_file = _get_feedback_file_path()
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        logger.info(
            "feedback_submitted",
            feedback_id=feedback_id,
            conversation_id=feedback.conversation_id,
            rating=feedback.rating.value,
            category=feedback.category.value if feedback.category else None
        )

        return FeedbackResponse(
            success=True,
            feedback_id=feedback_id,
            message="Feedback recorded successfully. Thank you for helping us improve!"
        )

    except Exception as e:
        logger.error("failed_to_submit_feedback", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats(days: int = 7):
    """
    Get feedback statistics for the last N days

    Args:
        days: Number of days to include (default: 7)

    Returns:
        Aggregated feedback statistics
    """
    try:
        # Load feedback from last N days
        all_feedback = []
        for i in range(days):
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            date = date.replace(day=date.day - i)

            feedback_file = _get_feedback_file_path(date)
            if feedback_file.exists():
                with open(feedback_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                record = FeedbackRecord.model_validate_json(line)
                                all_feedback.append(record)
                            except Exception as e:
                                logger.warning("failed_to_parse_feedback_line", error=str(e))

        # Calculate statistics
        total = len(all_feedback)
        if total == 0:
            return FeedbackStats(
                total_feedback=0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                positive_rate=0.0,
                negative_rate=0.0,
                category_breakdown={},
                low_rated_queries=[]
            )

        positive_count = sum(1 for f in all_feedback if f.rating == FeedbackRating.POSITIVE)
        negative_count = sum(1 for f in all_feedback if f.rating == FeedbackRating.NEGATIVE)
        neutral_count = sum(1 for f in all_feedback if f.rating == FeedbackRating.NEUTRAL)

        # Category breakdown (negative feedback only)
        category_breakdown = {}
        for f in all_feedback:
            if f.rating == FeedbackRating.NEGATIVE and f.category:
                category = f.category.value
                category_breakdown[category] = category_breakdown.get(category, 0) + 1

        # Average confidence
        confidences = [f.confidence for f in all_feedback if f.confidence is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None

        # Low-rated queries (negative feedback)
        low_rated = []
        negative_feedback = [f for f in all_feedback if f.rating == FeedbackRating.NEGATIVE]

        # Group by query
        query_groups = {}
        for f in negative_feedback:
            query = f.query or "Unknown query"
            if query not in query_groups:
                query_groups[query] = []
            query_groups[query].append(f)

        # Get top 10 most complained about queries
        for query, feedbacks in sorted(query_groups.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            low_rated.append({
                "query": query,
                "rating": "negative",
                "count": len(feedbacks),
                "categories": list(set(f.category.value for f in feedbacks if f.category)),
                "comments": [f.comment for f in feedbacks if f.comment][:3]  # First 3 comments
            })

        logger.info(
            "feedback_stats_retrieved",
            days=days,
            total_feedback=total,
            positive_rate=positive_count / total if total > 0 else 0
        )

        return FeedbackStats(
            total_feedback=total,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            positive_rate=positive_count / total if total > 0 else 0,
            negative_rate=negative_count / total if total > 0 else 0,
            category_breakdown=category_breakdown,
            avg_confidence=avg_confidence,
            low_rated_queries=low_rated
        )

    except Exception as e:
        logger.error("failed_to_get_feedback_stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feedback statistics: {str(e)}"
        )


@router.get("/recent", response_model=List[FeedbackRecord])
async def get_recent_feedback(limit: int = 50, rating: str = None):
    """
    Get recent feedback records

    Args:
        limit: Maximum number of records to return (default: 50)
        rating: Filter by rating (positive/negative/neutral)

    Returns:
        List of recent feedback records
    """
    try:
        # Load feedback from last 30 days
        all_feedback = []
        for i in range(30):
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            date = date.replace(day=date.day - i)

            feedback_file = _get_feedback_file_path(date)
            if feedback_file.exists():
                with open(feedback_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                record = FeedbackRecord.model_validate_json(line)
                                all_feedback.append(record)
                            except Exception as e:
                                logger.warning("failed_to_parse_feedback_line", error=str(e))

        # Filter by rating if specified
        if rating:
            try:
                rating_enum = FeedbackRating(rating.lower())
                all_feedback = [f for f in all_feedback if f.rating == rating_enum]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid rating: {rating}. Must be positive, negative, or neutral"
                )

        # Sort by timestamp (newest first) and limit
        all_feedback.sort(key=lambda x: x.timestamp, reverse=True)
        recent = all_feedback[:limit]

        logger.info(
            "recent_feedback_retrieved",
            count=len(recent),
            rating_filter=rating,
            limit=limit
        )

        return recent

    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_get_recent_feedback", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recent feedback: {str(e)}"
        )
