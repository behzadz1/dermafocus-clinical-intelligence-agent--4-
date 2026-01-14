"""
Claude AI Service
Handles interactions with Anthropic's Claude API
"""

from typing import List, Dict, Any, Optional, Generator
from anthropic import Anthropic, AnthropicError
import structlog

from app.config import settings

logger = structlog.get_logger()


class ClaudeService:
    """
    Service for interacting with Claude AI
    """
    
    def __init__(self):
        """Initialize Claude client"""
        self.api_key = settings.anthropic_api_key
        self.model = settings.claude_model
        self.max_tokens = settings.claude_max_tokens
        self.temperature = settings.claude_temperature
        
        self._client = None
    
    @property
    def client(self) -> Anthropic:
        """Lazy load Anthropic client"""
        if self._client is None:
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured")
            
            logger.info("Initializing Claude client", model=self.model)
            self._client = Anthropic(api_key=self.api_key)
        
        return self._client
    
    def generate_response(
        self,
        user_message: str,
        context: str = "",
        conversation_history: List[Dict[str, str]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a response from Claude
        
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
            
            # Build system prompt
            if not system_prompt:
                system_prompt = self._build_system_prompt(context)
            
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
            
            # Call Claude API
            response = self.client.messages.create(
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
            
            logger.info(
                "Claude response generated",
                answer_length=len(answer),
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens
            )
            
            return {
                "answer": answer,
                "model": self.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                "stop_reason": response.stop_reason
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
    
    def generate_response_stream(
        self,
        user_message: str,
        context: str = "",
        conversation_history: List[Dict[str, str]] = None,
        system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response from Claude
        
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
            
            # Build system prompt
            if not system_prompt:
                system_prompt = self._build_system_prompt(context)
            
            # Build messages
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Stream response
            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield text
            
            logger.info("Streaming response completed")
            
        except AnthropicError as e:
            logger.error("Claude streaming error", error=str(e))
            raise
        except Exception as e:
            logger.error("Streaming failed", error=str(e))
            raise
    
    def _build_system_prompt(self, context: str = "") -> str:
        """
        Build system prompt for Claude
        
        Args:
            context: Retrieved context from RAG
            
        Returns:
            System prompt string
        """
        base_prompt = """You are DermaAI CKPA, an expert AI assistant specializing in aesthetic medicine and Dermafocus products.

Your role is to provide accurate, helpful information about:
- Dermafocus aesthetic products (Plinest, Newest, etc.)
- Treatment protocols and techniques
- Clinical applications and indications
- Product compositions and mechanisms
- Safety information and contraindications

Guidelines:
1. Always base your answers on the provided context from official documents
2. If the context doesn't contain relevant information, clearly state this
3. Never make up information about products or treatments
4. Cite specific products, protocols, or documents when applicable
5. Use clear, professional language appropriate for medical professionals
6. If asked about something outside your expertise, politely redirect to appropriate resources
7. Prioritize safety: always mention contraindications and proper usage"""

        if context:
            base_prompt += f"\n\n<context>\n{context}\n</context>\n\nUse the information in the context above to answer the user's question. If the context doesn't contain relevant information, say so."
        
        return base_prompt
    
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
    
    def classify_intent(self, question: str) -> Dict[str, Any]:
        """
        Classify the intent of a user question for better routing.

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

    def generate_follow_ups(
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

            # Use a quick Claude call with lower tokens for efficiency
            response = self.client.messages.create(
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

    def health_check(self) -> Dict[str, Any]:
        """
        Check if Claude API is accessible
        
        Returns:
            Health status
        """
        try:
            # Try to create a simple message
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            
            return {
                "status": "healthy",
                "model": self.model,
                "api_version": "2023-06-01"
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
