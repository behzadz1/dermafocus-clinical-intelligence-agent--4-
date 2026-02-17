"""
Chat Routes
Endpoints for conversational AI with RAG capabilities
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import structlog
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.middleware.auth import verify_api_key
from app.policies.role_safety import evaluate_role_safety
from app.utils.logging_utils import redact_phi
from app.utils.audit_logger import log_audit_event
from app.utils import metrics
from app.evaluation.quality_metrics import get_quality_metrics_collector
from app.services.conversation_service import get_conversation_service
from app.models.conversation import MessageRole

router = APIRouter()
logger = structlog.get_logger()


# ==============================================================================
# CONFIDENCE CALCULATION
# ==============================================================================

def calculate_weighted_confidence(chunks: list) -> float:
    """
    Calculate confidence score based on retrieval quality.

    Adjusted for realistic embedding similarity scores (typically 0.3-0.7).

    Returns:
        Confidence score between 0.0 and 0.95
    """
    if not chunks:
        return 0.0

    scores = [c["score"] for c in chunks]
    top_score = scores[0] if scores else 0

    # Normalize scores: 0.3 = low, 0.5 = medium, 0.7+ = high
    # Map to confidence: top_score of 0.5 -> ~70% confidence
    if top_score >= 0.6:
        confidence = 0.85 + (top_score - 0.6) * 0.25  # 0.6->0.85, 0.8->0.90
    elif top_score >= 0.4:
        confidence = 0.65 + (top_score - 0.4) * 1.0   # 0.4->0.65, 0.6->0.85
    elif top_score >= 0.3:
        confidence = 0.50 + (top_score - 0.3) * 1.5   # 0.3->0.50, 0.4->0.65
    else:
        confidence = top_score * 1.67  # Below 0.3 is low confidence

    # Boost if multiple good sources found
    good_sources = sum(1 for s in scores if s > 0.35)
    if good_sources >= 3:
        confidence = min(confidence + 0.05, 0.95)

    return min(round(confidence, 2), 0.95)


STRICT_REFUSAL_MESSAGE = (
    "I do not have sufficient documented evidence in the current Dermafocus knowledge base "
    "to answer this safely. Please upload or reference the relevant source document."
)


def resolve_page_number(metadata: dict) -> int:
    """Resolve best page number from chunk metadata."""
    for key in ("page_number", "page_start", "page"):
        value = metadata.get(key)
        try:
            page = int(value)
        except (TypeError, ValueError):
            continue
        if page > 0:
            return page
    return 1


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class Message(BaseModel):
    """Single message in conversation"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None


class CustomizationOptions(BaseModel):
    """Options to customize response style per request"""
    audience: Optional[str] = Field(
        None,
        description="Target audience: physician, nurse_practitioner, aesthetician, clinic_staff, patient"
    )
    style: Optional[str] = Field(
        None,
        description="Response style: clinical, conversational, concise, detailed, educational"
    )
    preset: Optional[str] = Field(
        None,
        description="Use preset: physician_clinical, physician_concise, nurse_practical, aesthetician_educational, staff_simple"
    )


class ChatRequest(BaseModel):
    """Chat request payload"""
    question: str = Field(..., description="User's question", min_length=1, max_length=2000)
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    history: Optional[List[Message]] = Field(default=[], description="Conversation history")
    customization: Optional[CustomizationOptions] = Field(None, description="Response customization options")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the needle size for Plinest Eye?",
                "conversation_id": "conv_123abc",
                "history": [],
                "customization": {
                    "audience": "physician",
                    "style": "concise"
                }
            }
        }


class Source(BaseModel):
    """Source citation from knowledge base with clickable links"""
    document: str = Field(..., description="Document name/ID")
    title: str = Field(..., description="Human-readable document title")
    page: int = Field(..., description="Page number")
    section: Optional[str] = Field(None, description="Section name")
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    text_snippet: Optional[str] = Field(None, description="Relevant text snippet")
    view_url: str = Field(..., description="URL to view the document at this page")
    download_url: str = Field(..., description="URL to download the document")


class KnowledgeUsage(BaseModel):
    """Tracks how the response uses document vs general knowledge"""
    primary_source: str = Field(..., description="Primary knowledge source: document, clinical_knowledge, or hybrid")
    document_ratio: float = Field(..., description="Ratio of document-sourced content (0-1)")
    knowledge_blend: str = Field(..., description="document-heavy, clinical-heavy, or balanced")


class ResponseCustomization(BaseModel):
    """Shows what customization was applied"""
    audience: str = Field(..., description="Target audience used")
    style: str = Field(..., description="Response style used")


class RelatedDocument(BaseModel):
    """Related document information"""
    doc_id: str = Field(..., description="Document ID")
    doc_type: Optional[str] = Field(None, description="Document type")
    shared_products: List[str] = Field(default=[], description="Products shared with retrieved documents")


class ChatResponse(BaseModel):
    """Chat response payload"""
    answer: str = Field(..., description="AI-generated answer")
    sources: List[Source] = Field(default=[], description="Source citations")
    intent: Optional[str] = Field(None, description="Classified intent")
    confidence: float = Field(..., description="Response confidence (0-1)")
    conversation_id: str = Field(..., description="Conversation ID")
    follow_ups: List[str] = Field(default=[], description="Suggested follow-up questions")
    knowledge_usage: Optional[KnowledgeUsage] = Field(None, description="How document vs general knowledge was used")
    customization_applied: Optional[ResponseCustomization] = Field(None, description="Customization settings used for this response")
    related_documents: List[RelatedDocument] = Field(default=[], description="Related documents (See also)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Plinest Eye uses a 30G ½ needle...",
                "sources": [
                    {
                        "document": "Plinest_Eye_Factsheet",
                        "title": "Plinest® Eye Factsheet",
                        "page": 9,
                        "section": "Product Specifications",
                        "relevance_score": 0.95,
                        "text_snippet": "...30G ½ needle provided in pack...",
                        "view_url": "/api/documents/view?doc_id=Plinest_Eye_Factsheet&page=9",
                        "download_url": "/api/documents/download/Plinest_Eye_Factsheet"
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
async def chat(request: ChatRequest, raw_request: Request, api_key: str = Depends(verify_api_key)):
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
        from app.services.prompt_customization import AudienceType, ResponseStyle

        rag_service = get_rag_service()
        claude_service = get_claude_service()
        conversation_service = get_conversation_service()

        # Apply per-request customization if provided
        if request.customization:
            if request.customization.preset:
                claude_service.set_customization(preset=request.customization.preset)
            else:
                audience = None
                style = None
                if request.customization.audience:
                    try:
                        audience = AudienceType(request.customization.audience)
                    except ValueError:
                        pass
                if request.customization.style:
                    try:
                        style = ResponseStyle(request.customization.style)
                    except ValueError:
                        pass
                if audience or style:
                    claude_service.set_customization(audience=audience, style=style)

        # Step 1: Classify query intent early for retrieval routing
        intent_data = claude_service.classify_intent(request.question)
        detected_intent = intent_data["intent"]
        logger.info("Intent classified", intent=detected_intent, intent_confidence=intent_data["confidence"])

        # Step 1.5: Role-based safety enforcement (patients cannot receive procedural guidance)
        role_decision = evaluate_role_safety(
            question=request.question,
            audience=claude_service.customizer.audience,
            intent=detected_intent
        )
        if not role_decision.allowed:
            conversation_id = request.conversation_id or f"conv_{int(datetime.utcnow().timestamp())}"
            logger.info("role_safety_blocked", reason=role_decision.reason)
            log_audit_event(
                "chat_interaction",
                request=raw_request,
                conversation_id=conversation_id,
                intent=detected_intent,
                audience=claude_service.customizer.audience.value,
                evidence_sufficient=False,
                refusal=True,
                sources_count=0,
                mode="sync",
                reason="role_restricted"
            )

            # Record quality metrics for role-based refusal
            quality_collector = get_quality_metrics_collector()
            quality_collector.record_query_quality(
                query=request.question,
                confidence=0.0,
                intent=detected_intent,
                top_retrieval_score=0.0,
                num_chunks_retrieved=0,
                num_strong_matches=0,
                evidence_sufficient=False,
                evidence_reason="role_restricted",
                query_expansion_applied="none",
                hierarchy_match_type="none",
                reranking_enabled=False,
                refusal=True,
                conversation_id=conversation_id,
                request_id=getattr(raw_request.state, 'request_id', None)
            )

            return ChatResponse(
                answer=role_decision.response or STRICT_REFUSAL_MESSAGE,
                sources=[],
                intent="role_restricted",
                confidence=0.0,
                conversation_id=conversation_id,
                follow_ups=[
                    "Can you share general, non-treatment information?",
                    "Should I speak with a licensed clinician?"
                ],
                knowledge_usage=KnowledgeUsage(
                    primary_source="document",
                    document_ratio=1.0,
                    knowledge_blend="document-heavy"
                ),
                customization_applied=ResponseCustomization(
                    audience=claude_service.customizer.audience.value,
                    style=claude_service.customizer.style.value
                ),
                related_documents=[]
            )

        # Step 2: Retrieve relevant context from RAG
        doc_type_filter = rag_service.infer_doc_type_for_intent(detected_intent)
        logger.info("Retrieving context from RAG", doc_type=doc_type_filter)
        context_data = await run_in_threadpool(
            rag_service.get_context_for_query,
            query=request.question,
            max_chunks=5,  # Enough for good context without overwhelming
            doc_type=doc_type_filter
        )

        context_text = context_data["context_text"]
        retrieved_chunks = context_data["chunks"]
        evidence = context_data.get("evidence", {})
        related_docs_raw = context_data.get("related_documents", [])

        logger.info(
            "Context retrieved",
            chunks_found=len(retrieved_chunks),
            context_length=len(context_text),
            evidence_sufficient=evidence.get("sufficient", False),
            evidence_reason=evidence.get("reason")
        )

        # Record retrieval metrics
        strong_matches_count = sum(1 for chunk in retrieved_chunks if chunk.get("score", 0) > 0.35)
        hierarchy_type = "mixed" if any(chunk.get("metadata", {}).get("parent_id") for chunk in retrieved_chunks) else "flat"
        expansion_type = context_data.get("expansion_type", "none")

        metrics.record_retrieval_metrics(
            confidence=max((chunk.get("score", 0) for chunk in retrieved_chunks), default=0.0),
            chunks_count=len(retrieved_chunks),
            strong_matches_count=strong_matches_count,
            hierarchy_match_type=hierarchy_type,
            evidence_sufficient_flag=evidence.get("sufficient", False),
            expansion_type=expansion_type
        )

        # Strict refusal when evidence is missing/weak.
        if not evidence.get("sufficient", False):
            # Record insufficient evidence
            metrics.record_insufficient_evidence()

            conversation_id = request.conversation_id or f"conv_{int(datetime.utcnow().timestamp())}"
            log_audit_event(
                "chat_interaction",
                request=raw_request,
                conversation_id=conversation_id,
                intent=detected_intent,
                audience=claude_service.customizer.audience.value,
                evidence_sufficient=False,
                refusal=True,
                sources_count=0,
                mode="sync",
                reason="insufficient_evidence"
            )

            # Record quality metrics for refusal
            quality_collector = get_quality_metrics_collector()
            quality_collector.record_query_quality(
                query=request.question,
                confidence=0.0,
                intent=detected_intent,
                top_retrieval_score=max((chunk.get("score", 0) for chunk in retrieved_chunks), default=0.0),
                num_chunks_retrieved=len(retrieved_chunks),
                num_strong_matches=strong_matches_count,
                evidence_sufficient=False,
                evidence_reason=evidence.get("reason"),
                query_expansion_applied=expansion_type,
                hierarchy_match_type=hierarchy_type,
                reranking_enabled=settings.reranker_enabled,
                refusal=True,
                conversation_id=conversation_id,
                request_id=getattr(raw_request.state, 'request_id', None)
            )

            return ChatResponse(
                answer=STRICT_REFUSAL_MESSAGE,
                sources=[],
                intent="insufficient_evidence",
                confidence=0.0,
                conversation_id=conversation_id,
                follow_ups=[
                    "Which source document should I use?",
                    "Can you upload the relevant protocol or factsheet?"
                ],
                knowledge_usage=KnowledgeUsage(
                    primary_source="document",
                    document_ratio=1.0,
                    knowledge_blend="document-heavy"
                ),
                customization_applied=ResponseCustomization(
                    audience=claude_service.customizer.audience.value,
                    style=claude_service.customizer.style.value
                ),
                related_documents=[]
            )

        # Step 3: Fetch conversation history from Redis and build context for Claude
        conversation_history = []

        # Fetch stored conversation from Redis (if exists)
        conversation_id = request.conversation_id or f"conv_{int(datetime.utcnow().timestamp())}"
        stored_conversation = conversation_service.get_conversation(conversation_id)

        if stored_conversation:
            # Use stored conversation history (last 3 message pairs = 6 messages)
            recent_messages = stored_conversation.get_recent_messages(count=3)
            for msg in recent_messages:
                conversation_history.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            logger.info(
                "conversation_loaded",
                conversation_id=conversation_id,
                turn_count=stored_conversation.turn_count,
                messages_loaded=len(recent_messages)
            )
        elif request.history:
            # Fallback to client-provided history (for backward compatibility)
            for msg in request.history[-5:]:
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

        # Record token usage
        if "usage" in claude_response:
            metrics.record_token_usage(
                service="claude",
                input_tokens=claude_response["usage"]["input_tokens"],
                output_tokens=claude_response["usage"]["output_tokens"]
            )

        answer = claude_response["answer"]

        # Step 5: Extract and format sources - DEDUPLICATED, TOP 3 UNIQUE DOCS
        from app.services.citation_service import get_citation_service
        from urllib.parse import quote

        citation_service = get_citation_service()
        sources = []
        seen_docs = set()
        MAX_SOURCES = 3  # Show only top 3 unique documents

        for chunk in retrieved_chunks:
            doc_id = chunk["metadata"].get("doc_id", "unknown")

            # Skip if we already have this document
            if doc_id in seen_docs:
                continue
            seen_docs.add(doc_id)

            # Stop after MAX_SOURCES unique documents
            if len(sources) >= MAX_SOURCES:
                break

            page_num = resolve_page_number(chunk.get("metadata", {}))
            doc_title = citation_service.get_document_title(doc_id)

            sources.append(Source(
                document=doc_id,
                title=doc_title,
                page=max(page_num, 1),  # Ensure page is at least 1
                section=chunk["metadata"].get("section"),
                relevance_score=round(chunk["score"], 2),
                text_snippet=chunk["text"][:150] + "..." if len(chunk["text"]) > 150 else chunk["text"],
                view_url=f"/api/documents/view?doc_id={quote(doc_id)}&page={max(page_num, 1)}",
                download_url=f"/api/documents/download/{quote(doc_id)}"
            ))

        # Step 5: Generate follow-up questions (async)
        follow_ups = await claude_service.generate_follow_ups(
            question=request.question,
            answer=answer,
            context=context_text
        )

        # Step 6: Calculate confidence using weighted formula
        confidence = calculate_weighted_confidence(retrieved_chunks)

        # Step 7: Analyze knowledge usage (document vs general knowledge)
        knowledge_analysis = claude_service.analyze_knowledge_usage(answer, context_text)

        # Get customization info from response
        customization_info = claude_response.get("customization", {})

        # Convert related documents to response format
        related_documents = [
            RelatedDocument(
                doc_id=doc.get("doc_id", ""),
                doc_type=doc.get("doc_type"),
                shared_products=doc.get("shared_products", [])
            )
            for doc in related_docs_raw
        ]

        response = ChatResponse(
            answer=answer,
            sources=sources,
            intent=detected_intent,  # Use classified intent instead of generic "answered"
            confidence=confidence,
            conversation_id=conversation_id,
            follow_ups=follow_ups,
            knowledge_usage=KnowledgeUsage(
                primary_source=knowledge_analysis["primary_source"],
                document_ratio=knowledge_analysis["document_ratio"],
                knowledge_blend=knowledge_analysis["knowledge_blend"]
            ),
            customization_applied=ResponseCustomization(
                audience=customization_info.get("audience", "physician"),
                style=customization_info.get("style", "clinical")
            ),
            related_documents=related_documents
        )
        
        logger.info(
            "chat_response_generated",
            conversation_id=conversation_id,
            answer_length=len(answer),
            sources_count=len(sources),
            confidence=confidence,
            knowledge_source=knowledge_analysis["primary_source"],
            document_ratio=knowledge_analysis["document_ratio"],
            tokens_used=claude_response["usage"]["input_tokens"] + claude_response["usage"]["output_tokens"]
        )

        log_audit_event(
            "chat_interaction",
            request=raw_request,
            conversation_id=conversation_id,
            intent=detected_intent,
            audience=customization_info.get("audience", "physician"),
            evidence_sufficient=evidence.get("sufficient", False),
            refusal=False,
            sources_count=len(sources),
            mode="sync"
        )

        # Record quality metrics
        quality_collector = get_quality_metrics_collector()
        quality_collector.record_query_quality(
            query=request.question,
            confidence=confidence,
            intent=detected_intent,
            top_retrieval_score=max((chunk.get("score", 0) for chunk in retrieved_chunks), default=0.0),
            num_chunks_retrieved=len(retrieved_chunks),
            num_strong_matches=strong_matches_count,
            evidence_sufficient=evidence.get("sufficient", False),
            evidence_reason=evidence.get("reason"),
            query_expansion_applied=expansion_type,
            hierarchy_match_type=hierarchy_type,
            reranking_enabled=settings.reranker_enabled,
            refusal=False,
            conversation_id=conversation_id,
            request_id=getattr(raw_request.state, 'request_id', None)
        )

        # Save user question and assistant response to conversation (1 hour TTL)
        try:
            conversation_service.add_message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=request.question,
                metadata={"intent": detected_intent, "confidence": confidence}
            )
            conversation_service.add_message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=answer,
                metadata={
                    "sources_count": len(sources),
                    "confidence": confidence,
                    "knowledge_source": knowledge_analysis["primary_source"]
                }
            )
            logger.debug("conversation_updated", conversation_id=conversation_id)
        except Exception as conv_error:
            logger.error("failed_to_save_conversation", error=str(conv_error), conversation_id=conversation_id)

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
            follow_ups=[],
            related_documents=[]
        )


@router.post("/stream", status_code=status.HTTP_200_OK)
async def chat_stream(request: ChatRequest, raw_request: Request, api_key: str = Depends(verify_api_key)):
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
            conversation_service = get_conversation_service()
            conversation_id = request.conversation_id or f"conv_{int(datetime.utcnow().timestamp())}"

            data = {"type": "conversation", "conversation_id": conversation_id}
            yield f"data: {json.dumps(data)}\n\n"

            log_audit_event(
                "chat_stream_start",
                request=raw_request,
                conversation_id=conversation_id,
                mode="stream"
            )

            # Apply per-request customization if provided
            if request.customization:
                if request.customization.preset:
                    claude_service.set_customization(preset=request.customization.preset)
                else:
                    audience = None
                    style = None
                    if request.customization.audience:
                        try:
                            audience = AudienceType(request.customization.audience)
                        except ValueError:
                            pass
                    if request.customization.style:
                        try:
                            style = ResponseStyle(request.customization.style)
                        except ValueError:
                            pass
                    if audience or style:
                        claude_service.set_customization(audience=audience, style=style)
            
            # Classify intent for retrieval routing
            intent_data = claude_service.classify_intent(request.question)
            detected_intent = intent_data["intent"]
            doc_type_filter = rag_service.infer_doc_type_for_intent(detected_intent)

            # Enforce role-based safety before retrieval
            role_decision = evaluate_role_safety(
                question=request.question,
                audience=claude_service.customizer.audience,
                intent=detected_intent
            )
            if not role_decision.allowed:
                logger.info("role_safety_blocked", reason=role_decision.reason)
                data = {"type": "content", "content": role_decision.response or STRICT_REFUSAL_MESSAGE}
                yield f"data: {json.dumps(data)}\n\n"
                data = {"type": "sources", "sources": []}
                yield f"data: {json.dumps(data)}\n\n"
                data = {
                    "type": "follow_ups",
                    "follow_ups": [
                        "Can you share general, non-treatment information?",
                        "Should I speak with a licensed clinician?"
                    ]
                }
                yield f"data: {json.dumps(data)}\n\n"
                data = {"type": "done"}
                yield f"data: {json.dumps(data)}\n\n"
                return

            # Retrieve context
            context_data = await run_in_threadpool(
                rag_service.get_context_for_query,
                query=request.question,
                max_chunks=5,  # Balanced for good context
                doc_type=doc_type_filter
            )
            
            context_text = context_data["context_text"]
            retrieved_chunks = context_data["chunks"]
            evidence = context_data.get("evidence", {})

            if not evidence.get("sufficient", False):
                data = {"type": "content", "content": STRICT_REFUSAL_MESSAGE}
                yield f"data: {json.dumps(data)}\n\n"
                data = {"type": "sources", "sources": []}
                yield f"data: {json.dumps(data)}\n\n"
                data = {
                    "type": "follow_ups",
                    "follow_ups": [
                        "Which source document should I use?",
                        "Can you upload the relevant protocol or factsheet?"
                    ]
                }
                yield f"data: {json.dumps(data)}\n\n"
                data = {"type": "done"}
                yield f"data: {json.dumps(data)}\n\n"
                return
            
            # Fetch stored conversation history from Redis
            conversation_history = []
            stored_conversation = conversation_service.get_conversation(conversation_id)

            if stored_conversation:
                # Use stored conversation history (last 3 message pairs)
                recent_messages = stored_conversation.get_recent_messages(count=3)
                for msg in recent_messages:
                    conversation_history.append({
                        "role": msg.role.value,
                        "content": msg.content
                    })
            elif request.history:
                # Fallback to client-provided history
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

            # Send sources at the end - deduplicated, with full metadata
            from app.services.citation_service import get_citation_service
            from urllib.parse import quote

            citation_service = get_citation_service()
            sources = []
            seen_docs = set()
            MAX_SOURCES = 3

            for chunk in retrieved_chunks:
                doc_id = chunk["metadata"].get("doc_id", "unknown")
                if doc_id in seen_docs:
                    continue
                seen_docs.add(doc_id)
                if len(sources) >= MAX_SOURCES:
                    break

                page_num = resolve_page_number(chunk.get("metadata", {}))
                sources.append({
                    "document": doc_id,
                    "title": citation_service.get_document_title(doc_id),
                    "page": max(page_num, 1),
                    "section": chunk["metadata"].get("section"),
                    "relevance_score": round(chunk["score"], 2),
                    "view_url": f"/api/documents/view?doc_id={quote(doc_id)}&page={max(page_num, 1)}",
                    "download_url": f"/api/documents/download/{quote(doc_id)}"
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

            # Save conversation messages to Redis
            try:
                conversation_service.add_message(
                    conversation_id=conversation_id,
                    role=MessageRole.USER,
                    content=request.question,
                    metadata={"intent": detected_intent}
                )
                conversation_service.add_message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=full_answer,
                    metadata={"sources_count": len(sources)}
                )
            except Exception as conv_error:
                logger.error("stream_conversation_save_failed", error=str(conv_error))

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

    Returns: List of messages in conversation with metadata
    """
    try:
        conversation_service = get_conversation_service()
        conversation = conversation_service.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found or expired"
            )

        # Convert to response format
        messages = [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            }
            for msg in conversation.messages
        ]

        logger.info(
            "conversation_history_retrieved",
            conversation_id=conversation_id,
            message_count=len(messages),
            turn_count=conversation.turn_count
        )

        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "turn_count": conversation.turn_count,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "summary": conversation.summary
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_conversation_history_failed", error=str(e), conversation_id=conversation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation history: {str(e)}"
        )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation and its history

    Args:
        conversation_id: Unique conversation identifier

    Returns: 204 No Content on success
    """
    try:
        conversation_service = get_conversation_service()
        deleted = conversation_service.delete_conversation(conversation_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )

        logger.info("conversation_deleted", conversation_id=conversation_id)
        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_conversation_failed", error=str(e), conversation_id=conversation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
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
