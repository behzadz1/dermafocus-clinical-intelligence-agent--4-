"""
Vision Service for Image Analysis
Uses Claude Vision API to describe images from PDFs
"""

import os
import base64
from typing import Dict, Any, Optional
import structlog
from anthropic import Anthropic

logger = structlog.get_logger()


class VisionService:
    """
    Service for analyzing images using Claude Vision API
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Vision Service

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"  # Vision-capable model

    def describe_image(
        self,
        image_bytes: bytes,
        image_type: str = "png",
        context: str = "",
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        Generate description of image using Claude Vision API

        Args:
            image_bytes: Raw image bytes
            image_type: Image type/extension (png, jpeg, jpg, webp, gif)
            context: Optional context about the document/page
            max_tokens: Maximum tokens for description

        Returns:
            Dictionary with:
            - description: Text description of image
            - confidence: Confidence in description quality (placeholder)
            - error: Error message if failed
        """
        try:
            # Convert image bytes to base64
            image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

            # Map file extensions to MIME types
            mime_types = {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "webp": "image/webp",
                "gif": "image/gif"
            }
            media_type = mime_types.get(image_type.lower(), "image/png")

            # Build prompt based on document type
            base_prompt = """You are analyzing an image from a medical/clinical document about aesthetic dermatology products and treatments.

Describe this image concisely, focusing on:
1. **Type**: Is this a diagram, photo, chart, illustration, or before/after comparison?
2. **Clinical content**: What medical/treatment information does it show?
3. **Key details**: Injection points, anatomical areas, technique steps, product application, treatment zones, etc.
4. **Text**: Any important labels, annotations, or text visible in the image

Be specific about medical/anatomical terms. Keep the description factual and clinical.
"""

            if context:
                base_prompt += f"\n\nDocument context: {context}"

            # Call Claude Vision API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": base_prompt
                            }
                        ],
                    }
                ],
            )

            # Extract description
            description = response.content[0].text

            logger.info(
                "image_described",
                image_size_bytes=len(image_bytes),
                image_type=image_type,
                description_length=len(description)
            )

            return {
                "description": description,
                "confidence": 0.9,  # Placeholder - could implement quality scoring
                "model": self.model,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens
            }

        except Exception as e:
            logger.error("failed_to_describe_image", error=str(e))
            return {
                "description": None,
                "error": str(e),
                "confidence": 0.0
            }

    def describe_technique_diagram(
        self,
        image_bytes: bytes,
        image_type: str = "png",
        product_name: str = "",
        page_context: str = ""
    ) -> str:
        """
        Specialized description for injection technique diagrams

        Args:
            image_bytes: Raw image bytes
            image_type: Image type/extension
            product_name: Product name if known
            page_context: Text context from the page

        Returns:
            Detailed technique description
        """
        context = f"This is a technique diagram"
        if product_name:
            context += f" for {product_name}"
        if page_context:
            context += f". Page context: {page_context[:200]}..."

        result = self.describe_image(
            image_bytes=image_bytes,
            image_type=image_type,
            context=context,
            max_tokens=600  # More tokens for detailed technique descriptions
        )

        return result.get("description", "")

    def batch_describe_images(
        self,
        images: list[Dict[str, Any]],
        context: str = ""
    ) -> list[Dict[str, Any]]:
        """
        Describe multiple images in batch

        Args:
            images: List of image dictionaries with 'image_bytes' and 'image_type'
            context: Optional context about the document

        Returns:
            List of description results
        """
        results = []

        for i, image_info in enumerate(images):
            image_bytes = image_info.get("image_bytes")
            image_type = image_info.get("image_ext", "png")

            if not image_bytes:
                results.append({
                    "description": None,
                    "error": "No image bytes provided"
                })
                continue

            # Describe image
            result = self.describe_image(
                image_bytes=image_bytes,
                image_type=image_type,
                context=context
            )

            # Add original image metadata
            result.update({
                "page_number": image_info.get("page_number"),
                "image_index": image_info.get("image_index"),
                "width": image_info.get("width"),
                "height": image_info.get("height")
            })

            results.append(result)

            logger.info(
                "batch_image_described",
                batch_index=i,
                total_images=len(images),
                page_number=image_info.get("page_number")
            )

        return results


# Singleton instance
_vision_service = None


def get_vision_service() -> VisionService:
    """Get singleton VisionService instance"""
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
