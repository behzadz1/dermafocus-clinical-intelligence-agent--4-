"""
Protocols Routes
Endpoints for dynamically extracting treatment protocol information from RAG
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog
import json
import re
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.middleware.auth import verify_api_key
from app.services.cache_service import get_cache, set_cache, clear_cache

router = APIRouter(dependencies=[Depends(verify_api_key)])
logger = structlog.get_logger()

CACHE_KEY_PROTOCOLS = "protocols_response"
CACHE_TTL_PROTOCOLS = 3600  # 1 hour


# ==============================================================================
# RESPONSE MODELS
# ==============================================================================

class ProtocolStep(BaseModel):
    """Single step in a protocol"""
    title: str = Field(..., description="Step title")
    description: str = Field(..., description="Step description")
    details: Optional[List[str]] = Field(default=[], description="Additional details")


class ProtocolVector(BaseModel):
    """Injection vector information"""
    name: str = Field(..., description="Vector name")
    description: str = Field(..., description="Vector description")


class ProtocolInfo(BaseModel):
    """Protocol information extracted from RAG"""
    id: str = Field(..., description="Protocol identifier")
    title: str = Field(..., description="Protocol title")
    product: str = Field(..., description="Product name")
    indication: str = Field(..., description="Primary indication")
    dosing: str = Field(..., description="Dosing information")
    steps: List[ProtocolStep] = Field(default=[], description="Protocol steps")
    contraindications: List[str] = Field(default=[], description="Contraindications")
    vectors: Optional[List[ProtocolVector]] = Field(default=None, description="Injection vectors")
    imagePlaceholder: Optional[str] = Field(None, description="Placeholder image URL")


class ProtocolsResponse(BaseModel):
    """Response containing all protocols"""
    protocols: List[ProtocolInfo] = Field(default=[], description="List of protocols")
    total: int = Field(0, description="Total number of protocols")
    last_updated: str = Field(..., description="Last update timestamp")
    source: str = Field("rag", description="Data source (rag or cache)")


# ==============================================================================
# PROTOCOL EXTRACTION LOGIC
# ==============================================================================

# Known protocols to search for
KNOWN_PROTOCOLS = [
    {"name": "Plinest Face Protocol", "product": "Plinest"},
    {"name": "Plinest Eye Protocol", "product": "Plinest Eye"},
    {"name": "Plinest Hair Protocol", "product": "Plinest Hair"},
    {"name": "Newest Global Revitalization", "product": "Newest"},
    {"name": "NewGyn Vulvar Protocol", "product": "NewGyn"},
    {"name": "Purasomes Skin Treatment", "product": "Purasomes Skin Glow Complex"},
    {"name": "Purasomes Hair Treatment", "product": "Purasomes Hair & Scalp Complex"},
]


def generate_protocol_id(name: str) -> str:
    """Generate a URL-safe protocol ID from name"""
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


async def extract_protocols_with_llm(rag_service, claude_service) -> List[ProtocolInfo]:
    """
    Use LLM to extract structured protocol information from RAG

    Args:
        rag_service: RAG service instance
        claude_service: Claude service instance

    Returns:
        List of extracted protocols
    """
    protocols = []

    for protocol_data in KNOWN_PROTOCOLS:
        protocol_name = protocol_data["name"]
        product_name = protocol_data["product"]

        try:
            # Search for protocol information
            query = f"Treatment protocol for {product_name} including injection technique, dosing, treatment schedule, steps, and contraindications"

            context_data = await run_in_threadpool(
                rag_service.get_context_for_query,
                query=query,
                max_chunks=10
            )

            if not context_data["chunks"]:
                logger.info(f"No RAG data found for protocol {protocol_name}")
                continue

            context_text = context_data["context_text"]

            # Use Claude to extract structured data
            extraction_prompt = f"""Based on the following clinical documentation, extract the treatment protocol information for "{product_name}" in JSON format.

Return ONLY a valid JSON object with these exact fields (no markdown, no explanation):
{{
  "title": "Protocol title (e.g., '{protocol_name}')",
  "product": "{product_name}",
  "indication": "Primary clinical indication for this protocol",
  "dosing": "Dosing information (e.g., '2ml total per session')",
  "steps": [
    {{
      "title": "Step title (e.g., 'Preparation', 'Injection Technique', 'Treatment Schedule')",
      "description": "Detailed step description",
      "details": ["Optional", "bullet", "points"]
    }}
  ],
  "contraindications": ["List", "of", "contraindications"],
  "vectors": [
    {{
      "name": "Vector/area name",
      "description": "Injection technique for this area"
    }}
  ]
}}

Include at least 3 steps. If vectors/injection areas are mentioned, include them.
If information is not available for a field, use empty string "" or empty array [].

Documentation context:
{context_text}"""

            response = await claude_service.generate_response(
                user_message=extraction_prompt,
                context="",
                system_prompt="You are a medical protocol extraction assistant. Extract structured treatment protocol information from clinical documentation. Return ONLY valid JSON, no markdown formatting, no explanations."
            )

            answer = response["answer"].strip()

            # Clean up response - remove markdown code blocks if present
            if answer.startswith("```"):
                answer = re.sub(r'^```(?:json)?\n?', '', answer)
                answer = re.sub(r'\n?```$', '', answer)

            # Parse JSON
            try:
                protocol_json = json.loads(answer)

                # Process steps
                steps = []
                for step_data in protocol_json.get("steps", []):
                    steps.append(ProtocolStep(
                        title=step_data.get("title", ""),
                        description=step_data.get("description", ""),
                        details=step_data.get("details", [])
                    ))

                # Process vectors
                vectors = None
                if protocol_json.get("vectors"):
                    vectors = []
                    for vec_data in protocol_json["vectors"]:
                        vectors.append(ProtocolVector(
                            name=vec_data.get("name", ""),
                            description=vec_data.get("description", "")
                        ))

                protocol_info = ProtocolInfo(
                    id=generate_protocol_id(protocol_json.get("title", protocol_name)),
                    title=protocol_json.get("title", protocol_name),
                    product=protocol_json.get("product", product_name),
                    indication=protocol_json.get("indication", ""),
                    dosing=protocol_json.get("dosing", ""),
                    steps=steps,
                    contraindications=protocol_json.get("contraindications", []),
                    vectors=vectors
                )
                protocols.append(protocol_info)
                logger.info(f"Extracted protocol: {protocol_name}")

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON for protocol {protocol_name}: {e}")
                continue

        except Exception as e:
            logger.error(f"Error extracting protocol {protocol_name}: {e}")
            continue

    return protocols


# ==============================================================================
# FAST FALLBACK DATA - BASIC PROTOCOL INFO (NO LLM CALLS)
# ==============================================================================

FALLBACK_PROTOCOLS = [
    ProtocolInfo(
        id=generate_protocol_id("Plinest Face Protocol"),
        title="Plinest Face Protocol",
        product="Plinest",
        indication="Facial rejuvenation and anti-aging",
        dosing="2ml per session",
        steps=[
            ProtocolStep(title="Preparation", description="Cleanse and prepare treatment area"),
            ProtocolStep(title="Injection Technique", description="Use proper injection vectors"),
            ProtocolStep(title="Treatment Schedule", description="Sessions spaced 2-4 weeks apart"),
        ],
        contraindications=["Pregnancy", "Active infections"],
    ),
    ProtocolInfo(
        id=generate_protocol_id("Plinest Eye Protocol"),
        title="Plinest Eye Protocol",
        product="Plinest Eye",
        indication="Periorbital rejuvenation",
        dosing="0.5ml per eye",
        steps=[
            ProtocolStep(title="Preparation", description="Gentle cleansing of eye area"),
            ProtocolStep(title="Micro-injection", description="Superficial injection technique"),
            ProtocolStep(title="Post-treatment", description="Apply soothing eye cream"),
        ],
        contraindications=["Eye infections", "Severe dry eye"],
    ),
    ProtocolInfo(
        id=generate_protocol_id("Plinest Hair Protocol"),
        title="Plinest Hair Protocol",
        product="Plinest Hair",
        indication="Hair loss and scalp rejuvenation",
        dosing="1-2ml per session",
        steps=[
            ProtocolStep(title="Scalp Preparation", description="Cleanse scalp thoroughly"),
            ProtocolStep(title="Intradermal Injection", description="Inject into scalp dermis"),
            ProtocolStep(title="Treatment Schedule", description="Monthly sessions for optimal results"),
        ],
        contraindications=["Scalp infections", "Recent head trauma"],
    ),
    ProtocolInfo(
        id=generate_protocol_id("Newest Global Revitalization"),
        title="Newest Global Revitalization",
        product="Newest",
        indication="Full-face rejuvenation",
        dosing="3-5ml per session",
        steps=[
            ProtocolStep(title="Full Assessment", description="Evaluate facial anatomy"),
            ProtocolStep(title="Multi-point Injection", description="Strategic placement"),
            ProtocolStep(title="Integration Period", description="Allow 2 weeks for integration"),
        ],
        contraindications=["Autoimmune conditions"],
    ),
    ProtocolInfo(
        id=generate_protocol_id("NewGyn Vulvar Protocol"),
        title="NewGyn Vulvar Protocol",
        product="NewGyn",
        indication="Vulvar rejuvenation and health",
        dosing="Variable dosing",
        steps=[
            ProtocolStep(title="Consultation", description="Detailed patient consultation"),
            ProtocolStep(title="Precise Application", description="Careful anatomical placement"),
            ProtocolStep(title="Follow-up Care", description="Post-treatment instructions"),
        ],
        contraindications=["Active infections", "Recent procedures"],
    ),
    ProtocolInfo(
        id=generate_protocol_id("Purasomes Skin Glow"),
        title="Purasomes Skin Glow Complex Protocol",
        product="Purasomes Skin Glow Complex",
        indication="Skin rejuvenation and glow",
        dosing="1-2ml per session",
        steps=[
            ProtocolStep(title="Skin Assessment", description="Evaluate skin condition"),
            ProtocolStep(title="Product Application", description="Inject into treatment areas"),
            ProtocolStep(title="Massage", description="Gentle massage for integration"),
        ],
        contraindications=["Sensitive skin conditions"],
    ),
    ProtocolInfo(
        id=generate_protocol_id("Purasomes Hair Complex"),
        title="Purasomes Hair & Scalp Complex Protocol",
        product="Purasomes Hair & Scalp Complex",
        indication="Hair and scalp health",
        dosing="1-1.5ml per session",
        steps=[
            ProtocolStep(title="Scalp Analysis", description="Assess scalp health"),
            ProtocolStep(title="Targeted Injection", description="Focus on problem areas"),
            ProtocolStep(title="Maintenance", description="Regular monthly sessions"),
        ],
        contraindications=["Active scalp disease"],
    ),
]


# ==============================================================================
# CACHE MANAGEMENT
# ==============================================================================

def get_cached_protocols() -> Optional[ProtocolsResponse]:
    """Get cached protocols if still valid"""
    return get_cache(CACHE_KEY_PROTOCOLS)


def set_protocols_cache(protocols: ProtocolsResponse):
    """Set protocols cache"""
    set_cache(CACHE_KEY_PROTOCOLS, protocols, ttl_seconds=CACHE_TTL_PROTOCOLS)


def clear_protocols_cache():
    """Clear protocols cache (called when new documents uploaded)"""
    clear_cache(CACHE_KEY_PROTOCOLS)
    logger.info("protocols_cache_invalidated", reason="document_upload")


def get_fallback_protocols() -> ProtocolsResponse:
    """Get fallback protocols (no LLM calls, instant response)"""
    return ProtocolsResponse(
        protocols=FALLBACK_PROTOCOLS,
        total=len(FALLBACK_PROTOCOLS),
        last_updated=datetime.utcnow().isoformat(),
        source="fallback"
    )


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/", response_model=ProtocolsResponse, status_code=status.HTTP_200_OK)
async def get_protocols(refresh: bool = False):
    """
    Get all protocols - instant response with fallback data

    Args:
        refresh: Force refresh from RAG (ignore cache)

    Returns:
        List of protocols with metadata
    """
    logger.info("Protocols request received", refresh=refresh)

    # Check cache first
    if not refresh:
        cached = get_cached_protocols()
        if cached:
            logger.info("Returning cached protocols", count=cached.total)
            cached.source = "cache"
            return cached

    # Return fast fallback (no LLM calls, instant response)
    logger.info("Returning fallback protocols (instant response)")
    response = get_fallback_protocols()
    set_protocols_cache(response)
    return response


@router.get("/{protocol_id}", response_model=ProtocolInfo, status_code=status.HTTP_200_OK)
async def get_protocol(protocol_id: str):
    """
    Get detailed information for a specific protocol

    Args:
        protocol_id: Protocol identifier

    Returns:
        Protocol information
    """
    logger.info("Single protocol request", protocol_id=protocol_id)

    # First check cache
    cached = get_cached_protocols()
    if cached:
        for protocol in cached.protocols:
            if protocol.id == protocol_id:
                return protocol

    # If not in cache, fetch all and search
    try:
        from app.services.rag_service import get_rag_service
        from app.services.claude_service import get_claude_service

        rag_service = get_rag_service()
        claude_service = get_claude_service()

        protocols = await extract_protocols_with_llm(rag_service, claude_service)

        for protocol in protocols:
            if protocol.id == protocol_id:
                return protocol

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Protocol '{protocol_id}' not found in knowledge base"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Protocol extraction failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get protocol: {str(e)}"
        )


@router.post("/refresh", response_model=ProtocolsResponse, status_code=status.HTTP_200_OK)
async def refresh_protocols():
    """
    Force refresh protocols from RAG

    Returns:
        Updated list of protocols
    """
    logger.info("Forcing protocols refresh")
    return await get_protocols(refresh=True)


@router.get("/cache/clear", status_code=status.HTTP_200_OK)
async def clear_protocols_cache_endpoint():
    """
    Clear the protocols cache

    Returns:
        Confirmation message
    """
    clear_protocols_cache()
    return {"status": "cleared", "message": "Protocols cache has been cleared"}
