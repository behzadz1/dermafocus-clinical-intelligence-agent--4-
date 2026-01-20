"""
Chat Routes
Endpoints for conversational AI with RAG capabilities
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import structlog

from app.config import settings
from app.middleware.auth import verify_api_key

router = APIRouter()
logger = structlog.get_logger()


# ==============================================================================
# PHI REDACTION FOR LOGGING
# ==============================================================================

import re

PHI_PATTERNS = [
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),  # SSN
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),  # Email
    (r'\b\d{10,11}\b', '[PHONE]'),  # Phone
]

def redact_phi(text: str) -> str:
    """Redact potential PHI from text for safe logging."""
    if not text:
        return text
    for pattern, replacement in PHI_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


# ==============================================================================
# CONFIDENCE CALCULATION
# ==============================================================================

def calculate_weighted_confidence(chunks: list) -> float:
    """
    Calculate confidence score using weighted factors for better accuracy.

    Factors:
    - Top chunk score (35%): Best match matters most
    - Average score (30%): Overall retrieval quality
    - Coverage score (20%): Multiple high-quality sources
    - Consistency score (15%): Agreement between sources

    Returns:
        Confidence score between 0.0 and 0.95
    """
    if not chunks:
        return 0.0

    scores = [c["score"] for c in chunks]

    # Factor 1: Top chunk score (most important match)
    top_score = scores[0] if scores else 0

    # Factor 2: Average score across all chunks
    avg_score = sum(scores) / len(scores)

    # Factor 3: Coverage - how many high-quality chunks (score > 0.6)
    high_quality_count = sum(1 for s in scores if s > 0.6)
    coverage_score = min(high_quality_count / 3.0, 1.0)  # Expect at least 3 good chunks

    # Factor 4: Consistency - low variance means sources agree
    if len(scores) > 1:
        variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
        consistency_score = max(0, 1 - (variance * 4))  # Penalize high variance
    else:
        consistency_score = 0.5  # Neutral if only one chunk

    # Weighted combination
    confidence = (
        top_score * 0.35 +
        avg_score * 0.30 +
        coverage_score * 0.20 +
        consistency_score * 0.15
    )

    # Cap at 0.95 to indicate we're never 100% certain
    return min(round(confidence, 3), 0.95)


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class Message(BaseModel):
    """Single message in conversation"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Chat request payload"""
    question: str = Field(..., description="User's question", min_length=1, max_length=2000)
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    history: Optional[List[Message]] = Field(default=[], description="Conversation history")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the needle size for Plinest Eye?",
                "conversation_id": "conv_123abc",
                "history": []
            }
        }


class Source(BaseModel):
    """Source citation from knowledge base"""
    document: str = Field(..., description="Document name")
    page: int = Field(..., description="Page number")
    section: Optional[str] = Field(None, description="Section name")
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    text_snippet: Optional[str] = Field(None, description="Relevant text snippet")


class ChatResponse(BaseModel):
    """Chat response payload"""
    answer: str = Field(..., description="AI-generated answer")
    sources: List[Source] = Field(default=[], description="Source citations")
    intent: Optional[str] = Field(None, description="Classified intent")
    confidence: float = Field(..., description="Response confidence (0-1)")
    conversation_id: str = Field(..., description="Conversation ID")
    follow_ups: List[str] = Field(default=[], description="Suggested follow-up questions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Plinest Eye uses a 30G ½ needle...",
                "sources": [
                    {
                        "document": "Mastelli_Portfolio",
                        "page": 9,
                        "section": "Product Specifications",
                        "relevance_score": 0.95,
                        "text_snippet": "...30G ½ needle provided in pack..."
                    }
                ],
                "intent": "product_info",
                "confidence": 0.92,
                "conversation_id": "conv_123abc",
                "follow_ups": [
                    "What is the protocol for Plinest Eye?",
                    "What are the contraindications?"
                ]
            }
        }


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    """
    Main chat endpoint with RAG
    
    Process:
    1. Retrieve relevant documents from Pinecone
    2. Generate context-aware response with Claude
    3. Attach source citations
    4. Generate follow-up questions
    
    Phase 4: Now fully functional with RAG!
    """
    logger.info(
        "chat_request",
        question=redact_phi(request.question[:100]),
        conversation_id=request.conversation_id,
        has_history=len(request.history) > 0
    )
    
    try:
        from app.services.rag_service import get_rag_service
        from app.services.claude_service import get_claude_service
        
        rag_service = get_rag_service()
        claude_service = get_claude_service()
        
        # Step 1: Retrieve relevant context from RAG
        logger.info("Retrieving context from RAG")
        context_data = rag_service.get_context_for_query(
            query=request.question,
            max_chunks=8  # Increased from 5 for better coverage
        )
        
        context_text = context_data["context_text"]
        retrieved_chunks = context_data["chunks"]
        
        logger.info(
            "Context retrieved",
            chunks_found=len(retrieved_chunks),
            context_length=len(context_text)
        )
        
        # Step 2: Classify query intent
        intent_data = claude_service.classify_intent(request.question)
        detected_intent = intent_data["intent"]
        logger.info("Intent classified", intent=detected_intent, intent_confidence=intent_data["confidence"])

        # Step 3: Build conversation history for Claude
        conversation_history = []
        if request.history:
            for msg in request.history[-5:]:  # Last 5 messages for context
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Step 4: Generate response with Claude (async)
        logger.info("Generating Claude response")
        claude_response = await claude_service.generate_response(
            user_message=request.question,
            context=context_text,
            conversation_history=conversation_history
        )

        answer = claude_response["answer"]

        # Step 4: Extract and format sources
        sources = []
        for chunk in retrieved_chunks:
            sources.append(Source(
                document=chunk["metadata"].get("doc_id", "unknown"),
                page=chunk["metadata"].get("page_number", 0),
                section=chunk["metadata"].get("section"),
                relevance_score=chunk["score"],
                text_snippet=chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"]
            ))

        # Step 5: Generate follow-up questions (async)
        follow_ups = await claude_service.generate_follow_ups(
            question=request.question,
            answer=answer,
            context=context_text
        )
        
        # Step 6: Calculate confidence using weighted formula
        confidence = calculate_weighted_confidence(retrieved_chunks)
        
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or f"conv_{int(datetime.utcnow().timestamp())}"
        
        response = ChatResponse(
            answer=answer,
            sources=sources,
            intent=detected_intent,  # Use classified intent instead of generic "answered"
            confidence=confidence,
            conversation_id=conversation_id,
            follow_ups=follow_ups
        )
        
        logger.info(
            "chat_response_generated",
            conversation_id=conversation_id,
            answer_length=len(answer),
            sources_count=len(sources),
            confidence=confidence,
            tokens_used=claude_response["usage"]["input_tokens"] + claude_response["usage"]["output_tokens"]
        )
        
        return response
    
    except Exception as e:
        logger.error(
            "chat_request_failed",
            error=str(e),
            question=redact_phi(request.question[:100])
        )
        
        # Return fallback response on error
        return ChatResponse(
            answer=f"I apologize, but I encountered an error processing your question. Please try again. Error: {str(e)[:100]}",
            sources=[],
            intent="error",
            confidence=0.0,
            conversation_id=request.conversation_id or f"error_{int(datetime.utcnow().timestamp())}",
            follow_ups=[]
        )


@router.post("/stream", status_code=status.HTTP_200_OK)
async def chat_stream(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    """
    Streaming chat endpoint for real-time responses

    Returns: Server-Sent Events (SSE) stream

    Phase 4: Now functional with streaming Claude responses!
    """
    from fastapi.responses import StreamingResponse
    import json
    
    logger.info(
        "chat_stream_request",
        question=redact_phi(request.question[:100]),
        conversation_id=request.conversation_id
    )
    
    async def generate():
        """Generate streaming response"""
        try:
            from app.services.rag_service import get_rag_service
            from app.services.claude_service import get_claude_service
            
            rag_service = get_rag_service()
            claude_service = get_claude_service()
            
            # Retrieve context
            context_data = rag_service.get_context_for_query(
                query=request.question,
                max_chunks=8  # Increased from 5 for better coverage
            )
            
            context_text = context_data["context_text"]
            retrieved_chunks = context_data["chunks"]
            
            # Build conversation history
            conversation_history = []
            if request.history:
                for msg in request.history[-5:]:
                    conversation_history.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Stream response from Claude and collect full answer (async)
            full_answer = ""
            async for chunk in claude_service.generate_response_stream(
                user_message=request.question,
                context=context_text,
                conversation_history=conversation_history
            ):
                full_answer += chunk
                data = {"type": "content", "content": chunk}
                yield f"data: {json.dumps(data)}\n\n"

            # Send sources at the end
            sources = []
            for chunk in retrieved_chunks:
                sources.append({
                    "document": chunk["metadata"].get("doc_id", "unknown"),
                    "page": chunk["metadata"].get("page_number", 0),
                    "relevance_score": chunk["score"]
                })

            data = {"type": "sources", "sources": sources}
            yield f"data: {json.dumps(data)}\n\n"

            # Generate and send dynamic follow-up questions (async)
            follow_ups = await claude_service.generate_follow_ups(
                question=request.question,
                answer=full_answer,
                context=context_text
            )
            data = {"type": "follow_ups", "follow_ups": follow_ups}
            yield f"data: {json.dumps(data)}\n\n"

            # Send completion
            data = {"type": "done"}
            yield f"data: {json.dumps(data)}\n\n"
            
        except Exception as e:
            logger.error("Streaming failed", error=str(e))
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/{conversation_id}/history", status_code=status.HTTP_200_OK)
async def get_conversation_history(conversation_id: str):
    """
    Retrieve conversation history
    
    Args:
        conversation_id: Unique conversation identifier
    
    Returns: List of messages in conversation
    
    NOTE: This is a placeholder. Implementation in Phase 7.
    """
    # TODO: Implement conversation storage and retrieval
    # from app.services.conversation_service import ConversationService
    # conv_service = ConversationService()
    # history = await conv_service.get_conversation(conversation_id)
    # return {"conversation_id": conversation_id, "messages": history}
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Conversation history is not yet implemented."
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation and its history
    
    Args:
        conversation_id: Unique conversation identifier
    
    NOTE: This is a placeholder. Implementation in Phase 7.
    """
    # TODO: Implement conversation deletion
    # from app.services.conversation_service import ConversationService
    # conv_service = ConversationService()
    # await conv_service.delete_conversation(conversation_id)
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Conversation deletion is not yet implemented."
    )


@router.post("/feedback", status_code=status.HTTP_200_OK)
async def submit_feedback(
    conversation_id: str,
    message_id: str,
    feedback_type: str,  # "thumbs_up", "thumbs_down", "flag"
    comment: Optional[str] = None
):
    """
    Submit feedback on a specific response
    
    Args:
        conversation_id: Conversation identifier
        message_id: Specific message identifier
        feedback_type: Type of feedback (thumbs_up, thumbs_down, flag)
        comment: Optional feedback comment
    
    NOTE: This is a placeholder. Implementation in Phase 9 (Analytics).
    """
    logger.info(
        "feedback_received",
        conversation_id=conversation_id,
        message_id=message_id,
        feedback_type=feedback_type,
        has_comment=bool(comment)
    )
    
    # TODO: Store feedback in database for analytics
    
    return {
        "status": "received",
        "message": "Thank you for your feedback!"
    }
