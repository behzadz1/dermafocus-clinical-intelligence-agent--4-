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
        Generate intelligent follow-up questions based on conversation context.

        Args:
            question: Original question
            answer: Generated answer
            context: Used context

        Returns:
            List of contextually relevant follow-up questions
        """
        try:
            # Classify intent to generate relevant follow-ups
            intent_data = self.classify_intent(question)
            intent = intent_data["intent"]

            follow_ups = []
            question_lower = question.lower()
            answer_lower = answer.lower()

            # Product-specific follow-ups
            products = {
                "plinest": ["Plinest injection technique", "Plinest contraindications", "Plinest treatment schedule"],
                "newest": ["Newest mechanism of action", "Newest vs other polynucleotides", "Newest clinical results"],
                "newgyn": ["NewGyn vulvar protocol", "NewGyn dosing schedule", "NewGyn patient selection"],
                "purasomes": ["Purasomes composition details", "Purasomes skin protocol", "Purasomes hair treatment"]
            }

            for product, questions in products.items():
                if product in question_lower or product in answer_lower:
                    follow_ups.extend(questions)
                    break

            # Intent-based follow-ups
            intent_follow_ups = {
                "product_info": ["What are the clinical indications?", "What is the treatment protocol?", "What are the contraindications?"],
                "protocol": ["What needle size is recommended?", "How many sessions are needed?", "What areas can be treated?"],
                "dosing": ["What is the treatment frequency?", "Can the dose be adjusted?", "What factors affect dosing?"],
                "contraindications": ["Are there any drug interactions?", "What precautions should be taken?", "How to manage adverse reactions?"],
                "comparison": ["What are the indications for each?", "Which is better for specific conditions?", "What are the cost differences?"],
                "safety": ["What are the most common side effects?", "How to minimize complications?", "What is the safety profile?"],
                "scheduling": ["What is the maintenance protocol?", "When will results be visible?", "How long do effects last?"],
                "equipment": ["What injection depth is recommended?", "What technique should be used?", "Are there alternative tools?"]
            }

            if intent in intent_follow_ups:
                follow_ups.extend(intent_follow_ups[intent])

            # Remove duplicates and questions similar to the original
            unique_follow_ups = []
            seen = set()
            for fu in follow_ups:
                fu_lower = fu.lower()
                # Skip if too similar to original question
                if any(word in question_lower for word in fu_lower.split()[:3]):
                    continue
                if fu_lower not in seen:
                    seen.add(fu_lower)
                    unique_follow_ups.append(fu)

            # Return max 3 follow-ups
            return unique_follow_ups[:3]

        except Exception as e:
            logger.warning("Failed to generate follow-ups", error=str(e))
            return []
    
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
