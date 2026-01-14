"""
Products Routes
Endpoints for dynamically extracting product information from RAG
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog
import json
import re

from app.config import settings

router = APIRouter()
logger = structlog.get_logger()


# ==============================================================================
# RESPONSE MODELS
# ==============================================================================

class ProductInfo(BaseModel):
    """Product information extracted from RAG"""
    name: str = Field(..., description="Product name")
    technology: str = Field(..., description="Technology/platform")
    composition: str = Field(..., description="Product composition")
    indications: List[str] = Field(default=[], description="Treatment indications")
    mechanism: str = Field("", description="Mechanism of action")
    benefits: List[str] = Field(default=[], description="Clinical benefits")
    contraindications: List[str] = Field(default=[], description="Contraindications")
    imageUrl: Optional[str] = Field(None, description="Product image URL")


class ProductsResponse(BaseModel):
    """Response containing all products"""
    products: List[ProductInfo] = Field(default=[], description="List of products")
    total: int = Field(0, description="Total number of products")
    last_updated: str = Field(..., description="Last update timestamp")
    source: str = Field("rag", description="Data source (rag or cache)")


# ==============================================================================
# PRODUCT EXTRACTION LOGIC
# ==============================================================================

# Known product names to search for
KNOWN_PRODUCTS = [
    "Plinest",
    "Plinest Eye",
    "Plinest Hair",
    "Newest",
    "NewGyn",
    "Purasomes Skin Glow Complex",
    "Purasomes Nutri Complex 150+",
    "Purasomes Hair & Scalp Complex",
    "Purasomes XCell"
]


def extract_product_info_from_chunks(product_name: str, chunks: List[Dict[str, Any]]) -> Optional[ProductInfo]:
    """
    Extract structured product information from RAG chunks

    Args:
        product_name: Name of the product to extract
        chunks: RAG chunks containing product information

    Returns:
        ProductInfo or None if not enough data
    """
    if not chunks:
        return None

    # Combine all chunk text
    combined_text = "\n".join([c["text"] for c in chunks])

    # Initialize product data
    product_data = {
        "name": product_name,
        "technology": "",
        "composition": "",
        "indications": [],
        "mechanism": "",
        "benefits": [],
        "contraindications": []
    }

    # Extract technology
    tech_patterns = [
        r"PN-HPT®?\s*\+?\s*(?:HA\s*\+?\s*Mannitol)?",
        r"AMPLEX Plus®?\s*\(Exosomes\)",
        r"Polynucleotides?",
        r"Exosomes?\s*(?:&\s*Secretomes?)?"
    ]
    for pattern in tech_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            tech = match.group(0).strip()
            if "exosome" in tech.lower() or "AMPLEX" in tech:
                product_data["technology"] = "AMPLEX Plus® (Exosomes)"
            elif "HA" in tech and "Mannitol" in tech:
                product_data["technology"] = "PN-HPT® + HA + Mannitol"
            else:
                product_data["technology"] = "PN-HPT® (Polynucleotides)"
            break

    # Extract composition
    comp_patterns = [
        rf"{re.escape(product_name)}[^.]*?(\d+\s*(?:mg|ml|billion)[^.]*)",
        r"(?:Contains?|Composition)[:\s]*([^.]+(?:\d+\s*(?:mg|ml))[^.]*)",
        r"(\d+\s*(?:billion)?\s*exosomes?[^.]*)"
    ]
    for pattern in comp_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            product_data["composition"] = match.group(1).strip()[:200]
            break

    # Extract indications
    indication_keywords = [
        "ageing", "aging", "skin quality", "acne scars", "hydration", "dehydration",
        "rejuvenation", "face", "neck", "décolleté", "periocular", "eye contour",
        "hair", "scalp", "eyebrows", "vulvar", "genital", "thinning", "alopecia",
        "skin regeneration", "wound healing", "tissue repair", "dark spots",
        "age spots", "oily skin", "dull skin"
    ]
    for keyword in indication_keywords:
        if keyword.lower() in combined_text.lower():
            # Capitalize first letter properly
            indication = keyword.title() if len(keyword) > 3 else keyword.upper()
            if indication not in product_data["indications"]:
                product_data["indications"].append(indication)

    # Extract mechanism
    mechanism_patterns = [
        r"(?:mechanism|action|works by|stimulat(?:es?|ing))[:\s]*([^.]+\.)",
        r"(?:trophic|regenerat|repair|hydrat)[^.]*action[^.]*\."
    ]
    for pattern in mechanism_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            product_data["mechanism"] = match.group(0).strip()[:300]
            break

    # Extract benefits
    benefit_keywords = [
        "remodels", "bio-regeneration", "improves elasticity", "moisturises",
        "hydration", "radiance", "firmness", "collagen synthesis", "reduces",
        "enhances", "stimulates", "restores", "increases", "smoothes"
    ]
    for keyword in benefit_keywords:
        pattern = rf"({keyword}[^.]*\.)"
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            benefit = match.group(1).strip()
            if len(benefit) < 100 and benefit not in product_data["benefits"]:
                product_data["benefits"].append(benefit.capitalize())

    # Limit benefits to 4
    product_data["benefits"] = product_data["benefits"][:4]

    # Extract contraindications
    contraindication_keywords = [
        "pregnancy", "fish allergy", "active infection", "autoimmune",
        "scalp infection", "genital infection", "bovine allergy"
    ]
    for keyword in contraindication_keywords:
        if keyword.lower() in combined_text.lower():
            contra = keyword.title()
            if contra not in product_data["contraindications"]:
                product_data["contraindications"].append(contra)

    # Only return if we have meaningful data
    if product_data["technology"] or product_data["composition"] or product_data["indications"]:
        return ProductInfo(**product_data)

    return None


async def extract_products_with_llm(rag_service, claude_service) -> List[ProductInfo]:
    """
    Use LLM to extract structured product information from RAG

    Args:
        rag_service: RAG service instance
        claude_service: Claude service instance

    Returns:
        List of extracted products
    """
    products = []

    for product_name in KNOWN_PRODUCTS:
        try:
            # Search for product information
            query = f"Complete product information for {product_name} including composition, indications, mechanism of action, benefits, and contraindications"

            context_data = rag_service.get_context_for_query(
                query=query,
                max_chunks=8
            )

            if not context_data["chunks"]:
                logger.info(f"No RAG data found for {product_name}")
                continue

            context_text = context_data["context_text"]

            # Use Claude to extract structured data
            extraction_prompt = f"""Based on the following clinical documentation, extract product information for "{product_name}" in JSON format.

Return ONLY a valid JSON object with these exact fields (no markdown, no explanation):
{{
  "name": "{product_name}",
  "technology": "technology platform (e.g., PN-HPT®, AMPLEX Plus® Exosomes)",
  "composition": "exact composition with concentrations",
  "indications": ["list", "of", "indications"],
  "mechanism": "mechanism of action description",
  "benefits": ["clinical", "benefit", "1", "benefit 2"],
  "contraindications": ["list", "of", "contraindications"]
}}

If information is not available for a field, use empty string "" or empty array [].

Documentation context:
{context_text}"""

            response = claude_service.generate_response(
                user_message=extraction_prompt,
                context="",
                system_prompt="You are a medical data extraction assistant. Extract structured product information from clinical documentation. Return ONLY valid JSON, no markdown formatting, no explanations."
            )

            answer = response["answer"].strip()

            # Clean up response - remove markdown code blocks if present
            if answer.startswith("```"):
                answer = re.sub(r'^```(?:json)?\n?', '', answer)
                answer = re.sub(r'\n?```$', '', answer)

            # Parse JSON
            try:
                product_json = json.loads(answer)
                product_info = ProductInfo(
                    name=product_json.get("name", product_name),
                    technology=product_json.get("technology", ""),
                    composition=product_json.get("composition", ""),
                    indications=product_json.get("indications", []),
                    mechanism=product_json.get("mechanism", ""),
                    benefits=product_json.get("benefits", []),
                    contraindications=product_json.get("contraindications", [])
                )
                products.append(product_info)
                logger.info(f"Extracted product: {product_name}")

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON for {product_name}: {e}")
                # Try regex extraction as fallback
                product_info = extract_product_info_from_chunks(product_name, context_data["chunks"])
                if product_info:
                    products.append(product_info)

        except Exception as e:
            logger.error(f"Error extracting {product_name}: {e}")
            continue

    return products


# ==============================================================================
# CACHE
# ==============================================================================

_products_cache: Optional[ProductsResponse] = None
_cache_timestamp: Optional[datetime] = None
CACHE_DURATION_SECONDS = 3600  # 1 hour


def get_cached_products() -> Optional[ProductsResponse]:
    """Get cached products if still valid"""
    global _products_cache, _cache_timestamp

    if _products_cache and _cache_timestamp:
        age = (datetime.utcnow() - _cache_timestamp).total_seconds()
        if age < CACHE_DURATION_SECONDS:
            return _products_cache

    return None


def set_products_cache(products: ProductsResponse):
    """Set products cache"""
    global _products_cache, _cache_timestamp
    _products_cache = products
    _cache_timestamp = datetime.utcnow()


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/", response_model=ProductsResponse, status_code=status.HTTP_200_OK)
async def get_products(refresh: bool = False):
    """
    Get all products dynamically extracted from RAG

    Args:
        refresh: Force refresh from RAG (ignore cache)

    Returns:
        List of products with metadata
    """
    logger.info("Products request received", refresh=refresh)

    # Check cache first
    if not refresh:
        cached = get_cached_products()
        if cached:
            logger.info("Returning cached products", count=cached.total)
            cached.source = "cache"
            return cached

    try:
        from app.services.rag_service import get_rag_service
        from app.services.claude_service import get_claude_service

        rag_service = get_rag_service()
        claude_service = get_claude_service()

        # Extract products using LLM
        products = await extract_products_with_llm(rag_service, claude_service)

        response = ProductsResponse(
            products=products,
            total=len(products),
            last_updated=datetime.utcnow().isoformat(),
            source="rag"
        )

        # Cache the results
        set_products_cache(response)

        logger.info("Products extracted from RAG", count=len(products))
        return response

    except Exception as e:
        logger.error("Failed to extract products", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract products: {str(e)}"
        )


@router.get("/{product_name}", response_model=ProductInfo, status_code=status.HTTP_200_OK)
async def get_product(product_name: str):
    """
    Get detailed information for a specific product

    Args:
        product_name: Name of the product

    Returns:
        Product information
    """
    logger.info("Single product request", product_name=product_name)

    try:
        from app.services.rag_service import get_rag_service
        from app.services.claude_service import get_claude_service

        rag_service = get_rag_service()
        claude_service = get_claude_service()

        # Search for specific product
        query = f"Complete product information for {product_name} including composition, indications, mechanism of action, benefits, and contraindications"

        context_data = rag_service.get_context_for_query(
            query=query,
            max_chunks=10
        )

        if not context_data["chunks"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product '{product_name}' not found in knowledge base"
            )

        # Use Claude to extract structured data
        extraction_prompt = f"""Based on the following clinical documentation, extract complete product information for "{product_name}" in JSON format.

Return ONLY a valid JSON object with these exact fields:
{{
  "name": "{product_name}",
  "technology": "technology platform",
  "composition": "exact composition with concentrations",
  "indications": ["list", "of", "indications"],
  "mechanism": "detailed mechanism of action",
  "benefits": ["clinical", "benefits"],
  "contraindications": ["contraindications"]
}}

Documentation:
{context_data["context_text"]}"""

        response = claude_service.generate_response(
            user_message=extraction_prompt,
            context="",
            system_prompt="You are a medical data extraction assistant. Extract structured product information. Return ONLY valid JSON."
        )

        answer = response["answer"].strip()

        # Clean markdown
        if answer.startswith("```"):
            answer = re.sub(r'^```(?:json)?\n?', '', answer)
            answer = re.sub(r'\n?```$', '', answer)

        product_json = json.loads(answer)

        return ProductInfo(
            name=product_json.get("name", product_name),
            technology=product_json.get("technology", ""),
            composition=product_json.get("composition", ""),
            indications=product_json.get("indications", []),
            mechanism=product_json.get("mechanism", ""),
            benefits=product_json.get("benefits", []),
            contraindications=product_json.get("contraindications", [])
        )

    except json.JSONDecodeError as e:
        logger.error("JSON parse error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse product information"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Product extraction failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get product: {str(e)}"
        )


@router.post("/refresh", response_model=ProductsResponse, status_code=status.HTTP_200_OK)
async def refresh_products():
    """
    Force refresh products from RAG

    Returns:
        Updated list of products
    """
    logger.info("Forcing products refresh")
    return await get_products(refresh=True)


@router.get("/cache/clear", status_code=status.HTTP_200_OK)
async def clear_cache():
    """
    Clear the products cache

    Returns:
        Confirmation message
    """
    global _products_cache, _cache_timestamp
    _products_cache = None
    _cache_timestamp = None

    logger.info("Products cache cleared")
    return {"status": "cleared", "message": "Products cache has been cleared"}
