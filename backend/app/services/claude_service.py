"""
Claude AI Service
Handles interactions with Anthropic's Claude API using async client
Includes customization for Dermafocus brand voice and clinical communication
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
from anthropic import AsyncAnthropic, AnthropicError
import structlog

from app.config import settings
from app.services.prompt_customization import (
    OutputCustomizer,
    get_customizer,
    AudienceType,
    ResponseStyle
)

logger = structlog.get_logger()


class ClaudeService:
    """
    Service for interacting with Claude AI (async version)
    """

    def __init__(
        self,
        customizer_preset: str = "physician_clinical",
        audience: AudienceType = None,
        style: ResponseStyle = None
    ):
        """
        Initialize Claude client with customization options

        Args:
            customizer_preset: Pre-configured customization preset
                Options: physician_clinical, physician_concise, nurse_practical,
                         aesthetician_educational, staff_simple
            audience: Override audience type (optional)
            style: Override response style (optional)
        """
        self.api_key = settings.anthropic_api_key
        self.model = settings.claude_model
        self.max_tokens = settings.claude_max_tokens
        self.temperature = settings.claude_temperature

        self._client = None

        # Initialize customizer
        self.customizer = get_customizer(customizer_preset)

        # Override audience/style if specified
        if audience:
            self.customizer.audience = audience
        if style:
            self.customizer.style = style

        logger.info(
            "Claude service initialized",
            model=self.model,
            audience=self.customizer.audience.value,
            style=self.customizer.style.value
        )

    @property
    def client(self) -> AsyncAnthropic:
        """Lazy load async Anthropic client"""
        if self._client is None:
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured")

            logger.info("Initializing async Claude client", model=self.model)
            self._client = AsyncAnthropic(api_key=self.api_key)

        return self._client

    async def generate_response(
        self,
        user_message: str,
        context: str = "",
        conversation_history: List[Dict[str, str]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a response from Claude (async)

        Args:
            user_message: User's question
            context: Retrieved context from RAG
            conversation_history: Previous messages
            system_prompt: Custom system prompt

        Returns:
            Response dictionary with answer and metadata
        """
        try:
            logger.info(
                "Generating Claude response",
                message_length=len(user_message),
                has_context=len(context) > 0,
                history_length=len(conversation_history) if conversation_history else 0
            )

            # Build system prompt with customization
            if not system_prompt:
                system_prompt = self._build_system_prompt(context, query=user_message)

            # Build messages
            messages = []

            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)

            # Add current message
            messages.append({
                "role": "user",
                "content": user_message
            })

            # Call Claude API (async)
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages
            )

            # Extract answer
            answer = ""
            for block in response.content:
                if block.type == "text":
                    answer += block.text

            # Apply terminology corrections (ensure brand names are correct)
            answer = self.customizer.apply_terminology(answer)

            logger.info(
                "Claude response generated",
                answer_length=len(answer),
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                audience=self.customizer.audience.value,
                style=self.customizer.style.value
            )

            return {
                "answer": answer,
                "model": self.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                "stop_reason": response.stop_reason,
                "customization": {
                    "audience": self.customizer.audience.value,
                    "style": self.customizer.style.value
                }
            }

        except AnthropicError as e:
            logger.error(
                "Claude API error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
        except Exception as e:
            logger.error(
                "Claude response generation failed",
                error=str(e)
            )
            raise

    async def generate_response_stream(
        self,
        user_message: str,
        context: str = "",
        conversation_history: List[Dict[str, str]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from Claude (async)

        Args:
            user_message: User's question
            context: Retrieved context from RAG
            conversation_history: Previous messages
            system_prompt: Custom system prompt

        Yields:
            Text chunks as they arrive
        """
        try:
            logger.info(
                "Starting Claude streaming response",
                message_length=len(user_message)
            )

            # Build system prompt with customization
            if not system_prompt:
                system_prompt = self._build_system_prompt(context, query=user_message)

            # Build messages
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({
                "role": "user",
                "content": user_message
            })

            # Stream response (async)
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages
            ) as stream:
                async for text in stream.text_stream:
                    yield text

            logger.info("Streaming response completed")

        except AnthropicError as e:
            logger.error("Claude streaming error", error=str(e))
            raise
        except Exception as e:
            logger.error("Streaming failed", error=str(e))
            raise

    def _build_system_prompt(self, context: str = "", query: str = "") -> str:
        """
        Build system prompt for Claude with strict source-grounded behavior.

        Combines:
        1. Brand voice and customization rules
        2. Retrieved document context as the only acceptable evidence base

        Args:
            context: Retrieved context from RAG
            query: User query for template matching (optional)

        Returns:
            System prompt string
        """
        # Get customization instructions
        customization_prompt = self.customizer.build_customization_prompt()

        # Get query-specific template if applicable
        query_category = self.customizer.classify_query_category(query) if query else None
        template_hint = ""
        if query_category:
            template = self.customizer.get_query_template(query_category)
            if template:
                template_hint = f"\n\n## RESPONSE TEMPLATE GUIDANCE\nFor this type of query ({query_category.value}), structure your response similar to:\n{template[:500]}..."

        base_prompt = f"""{customization_prompt}

---

# CORE IDENTITY

You are DermaAI, a clinical knowledge assistant for Dermafocus aesthetic medicine products.

## RESPONSE STYLE

- **Be concise**: Answer directly without unnecessary preamble
- **Be professional**: Use clinical language appropriate for healthcare professionals
- **Be accurate**: Only state facts from the provided documents
- **Structure clearly**: Use brief bullet points for lists, short paragraphs for explanations

## RESPONSE LENGTH GUIDELINES

- **Simple questions** ("What is X?"): 2-4 sentences overview, key points only
- **Protocol questions**: Structured steps, no lengthy explanations
- **Comparison questions**: Brief table or bullet comparison
- **Complex clinical questions**: More detail allowed, but stay focused

## KNOWLEDGE PRIORITY

1. **ONLY SOURCE**: Information from <context> documents below

## RULES

- NEVER fabricate product specifications or claims not in documents
- If documents don't cover something, refuse clearly
- Don't repeat the same information in different ways
- Skip obvious disclaimers unless safety-critical"""

        if context:
            base_prompt += f"""

## DOCUMENT CONTEXT

<context>
{context}
</context>

## YOUR TASK

Answer the user's question directly and concisely using the documents above.
- Extract key facts, don't over-explain
- For "what is X" questions: brief definition + 2-3 key points
- Only add clinical context if it adds real value
"""
        else:
            base_prompt += """

## NOTE: No document context was provided for this query.

Do not answer from general knowledge.
Respond with a strict refusal that states there is insufficient documented evidence.
"""

        # Add template hint if available
        if template_hint:
            base_prompt += template_hint

        return base_prompt

    def set_customization(
        self,
        audience: AudienceType = None,
        style: ResponseStyle = None,
        preset: str = None
    ):
        """
        Update customization settings at runtime

        Args:
            audience: Target audience type
            style: Response style preference
            preset: Use a preset configuration
        """
        if preset:
            self.customizer = get_customizer(preset)
        if audience:
            self.customizer.audience = audience
        if style:
            self.customizer.style = style

        logger.info(
            "Customization updated",
            audience=self.customizer.audience.value,
            style=self.customizer.style.value
        )

    def extract_sources(
        self,
        context_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract source information from context chunks

        Args:
            context_chunks: RAG retrieved chunks

        Returns:
            List of source dictionaries
        """
        sources = []
        seen_docs = set()

        for i, chunk in enumerate(context_chunks, 1):
            doc_id = chunk["metadata"].get("doc_id", "unknown")

            if doc_id not in seen_docs:
                sources.append({
                    "source_id": i,
                    "doc_id": doc_id,
                    "doc_type": chunk["metadata"].get("doc_type", "document"),
                    "title": chunk["metadata"].get("title", doc_id),
                    "page": chunk["metadata"].get("page_number"),
                    "relevance_score": chunk["score"]
                })
                seen_docs.add(doc_id)

        return sources

    def analyze_knowledge_usage(self, answer: str, context: str) -> Dict[str, Any]:
        """
        Analyze how an answer uses document vs general knowledge.

        Args:
            answer: The generated answer
            context: The provided document context

        Returns:
            Analysis of knowledge sources used
        """
        answer_lower = answer.lower()
        context_lower = context.lower() if context else ""

        # Indicators of document-sourced information
        doc_indicators = [
            "according to the documentation",
            "the document states",
            "based on the provided",
            "from the context",
            "the dermafocus documentation",
            "[source",
            "as stated in",
            "the factsheet indicates",
            "the clinical paper shows",
            "per the protocol"
        ]

        # Indicators of general clinical knowledge
        general_indicators = [
            "from a clinical standpoint",
            "based on general clinical practice",
            "in dermatological practice",
            "from a medical perspective",
            "generally speaking",
            "standard practice",
            "clinically",
            "in aesthetic medicine",
            "medical literature suggests",
            "general consensus"
        ]

        # Count indicators
        doc_count = sum(1 for ind in doc_indicators if ind in answer_lower)
        general_count = sum(1 for ind in general_indicators if ind in answer_lower)

        # Check if answer contains specific terms from context
        context_terms_used = 0
        if context:
            # Extract key terms from context (product names, medical terms)
            import re
            context_terms = set(re.findall(r'\b[A-Z][a-z]+®?\b', context))
            for term in context_terms:
                if term.lower() in answer_lower:
                    context_terms_used += 1

        # Determine primary knowledge source
        if doc_count > general_count and context_terms_used > 0:
            primary_source = "document"
        elif general_count > doc_count:
            primary_source = "clinical_knowledge"
        elif context_terms_used > 2:
            primary_source = "document"
        else:
            primary_source = "hybrid"

        # Calculate blend ratio
        total_indicators = doc_count + general_count
        if total_indicators > 0:
            doc_ratio = doc_count / total_indicators
        else:
            doc_ratio = 0.5 if context else 0.0

        return {
            "primary_source": primary_source,
            "document_indicators": doc_count,
            "clinical_indicators": general_count,
            "context_terms_matched": context_terms_used,
            "document_ratio": round(doc_ratio, 2),
            "knowledge_blend": "document-heavy" if doc_ratio > 0.7 else "clinical-heavy" if doc_ratio < 0.3 else "balanced"
        }

    def classify_intent(self, question: str) -> Dict[str, Any]:
        """
        Classify the intent of a user question for better routing.
        This is a sync method as it doesn't call external APIs.

        Args:
            question: User's question

        Returns:
            Intent classification with category and confidence
        """
        question_lower = question.lower()

        # Intent patterns
        intents = {
            "product_info": ["what is", "composition", "ingredients", "mechanism", "how does", "technology"],
            "protocol": ["protocol", "treatment", "procedure", "steps", "how to", "technique"],
            "dosing": ["dose", "dosing", "how much", "quantity", "amount", "ml", "mg"],
            "contraindications": ["contraindication", "side effect", "adverse", "allergy", "pregnant", "avoid"],
            "comparison": ["difference", "compare", "versus", "vs", "better", "which one"],
            "safety": ["safe", "risk", "warning", "caution", "danger"],
            "scheduling": ["session", "frequency", "how often", "interval", "schedule", "maintenance"],
            "equipment": ["needle", "syringe", "tool", "device", "gauge"]
        }

        # Score each intent
        scores = {}
        for intent, keywords in intents.items():
            score = sum(1 for kw in keywords if kw in question_lower)
            if score > 0:
                scores[intent] = score

        if not scores:
            return {"intent": "general_query", "confidence": 0.5}

        # Get highest scoring intent
        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent] / 3.0, 1.0)  # Normalize to 0-1

        return {
            "intent": best_intent,
            "confidence": confidence,
            "all_intents": scores
        }

    async def generate_follow_ups(
        self,
        question: str,
        answer: str,
        context: str
    ) -> List[str]:
        """
        Generate dynamic follow-up questions using Claude based on the conversation context.

        Args:
            question: Original question asked by the user
            answer: Generated answer from the system
            context: RAG context used to generate the answer

        Returns:
            List of 3 contextually relevant follow-up questions
        """
        try:
            logger.info("Generating dynamic follow-up questions with Claude")

            # Build a focused prompt for follow-up generation
            follow_up_prompt = f"""Based on this clinical Q&A exchange, generate exactly 3 relevant follow-up questions that a clinician would naturally want to ask next.

**User Question:** {question}

**Answer Provided:** {answer[:500]}{"..." if len(answer) > 500 else ""}

**Available Context Topics:** {context[:300]}{"..." if len(context) > 300 else ""}

Requirements:
1. Questions must be directly related to the topic discussed
2. Questions should explore deeper aspects not fully covered in the answer
3. Questions should be practical and clinically relevant
4. Each question should be concise (under 10 words)
5. Do NOT repeat or rephrase the original question

Return ONLY 3 questions, one per line, no numbering or bullets."""

            # Use a quick Claude call with lower tokens for efficiency (async)
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=150,  # Short response needed
                temperature=0.4,  # Slightly more creative for variety
                system="You are a clinical assistant generating follow-up questions for aesthetic medicine practitioners. Be concise and specific.",
                messages=[{"role": "user", "content": follow_up_prompt}]
            )

            # Extract the response text
            response_text = ""
            for block in response.content:
                if block.type == "text":
                    response_text += block.text

            # Parse the response into individual questions
            lines = [line.strip() for line in response_text.strip().split('\n') if line.strip()]

            # Clean up any numbering or bullets that might have been added
            follow_ups = []
            for line in lines:
                # Remove common prefixes like "1.", "- ", "• ", etc.
                cleaned = line.lstrip('0123456789.-•) ').strip()
                if cleaned and len(cleaned) > 5:  # Ensure it's a real question
                    # Add question mark if missing
                    if not cleaned.endswith('?'):
                        cleaned += '?'
                    follow_ups.append(cleaned)

            logger.info(f"Generated {len(follow_ups)} dynamic follow-up questions")

            # Return max 3 follow-ups
            return follow_ups[:3]

        except Exception as e:
            logger.warning(f"Failed to generate dynamic follow-ups: {str(e)}, falling back to defaults")
            # Fallback to basic contextual questions if Claude fails
            return self._get_fallback_follow_ups(question, answer)

    def _get_fallback_follow_ups(self, question: str, answer: str) -> List[str]:
        """
        Generate fallback follow-up questions when Claude call fails.
        Uses simple keyword detection for basic relevance.
        """
        question_lower = question.lower()
        answer_lower = answer.lower()

        # Product-based fallbacks
        products = {
            "plinest": ["What is the Plinest treatment protocol?", "Plinest contraindications?", "Plinest needle size?"],
            "newest": ["How does Newest work?", "Newest treatment schedule?", "Newest indications?"],
            "newgyn": ["NewGyn application technique?", "NewGyn patient selection?", "NewGyn dosing?"],
            "purasomes": ["Purasomes mechanism of action?", "Purasomes treatment areas?", "Purasomes vs alternatives?"]
        }

        for product, questions in products.items():
            if product in question_lower or product in answer_lower:
                return questions[:3]

        # Generic clinical fallbacks
        return [
            "What are the contraindications?",
            "What is the recommended protocol?",
            "What results can be expected?"
        ]

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if Claude API is accessible (async)

        Returns:
            Health status
        """
        try:
            # Just verify the client can be created - don't make actual API call
            # (expensive and slow for health checks)
            _ = self.client
            return {
                "status": "healthy",
                "model": self.model,
                "key_configured": True
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Singleton instance
_claude_service = None


def get_claude_service() -> ClaudeService:
    """Get singleton Claude service instance"""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
