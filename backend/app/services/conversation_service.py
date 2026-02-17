"""
Conversation Service
Manages conversation history persistence using Redis
"""

import structlog
from typing import Optional, List
import json

from app.models.conversation import (
    ConversationSession,
    ConversationMessage,
    MessageRole
)
from app.services.cache_service import get_redis_client

logger = structlog.get_logger()

# Conversation TTL: 1 hour (3600 seconds)
CONVERSATION_TTL = 3600


class ConversationService:
    """
    Service for managing conversation sessions in Redis
    """

    def __init__(self):
        self.redis_client = None

    def _get_client(self):
        """Get Redis client (lazy load)"""
        if self.redis_client is None:
            try:
                self.redis_client = get_redis_client()
            except Exception as e:
                logger.error("Failed to connect to Redis for conversations", error=str(e))
                raise
        return self.redis_client

    def _get_conversation_key(self, conversation_id: str) -> str:
        """Generate Redis key for conversation"""
        return f"conversation:{conversation_id}"

    def get_conversation(self, conversation_id: str) -> Optional[ConversationSession]:
        """
        Retrieve conversation from Redis

        Args:
            conversation_id: Conversation ID

        Returns:
            ConversationSession if found, None otherwise
        """
        try:
            client = self._get_client()
            key = self._get_conversation_key(conversation_id)

            data = client.get(key)
            if data is None:
                logger.debug("conversation_not_found", conversation_id=conversation_id)
                return None

            # Deserialize conversation
            conversation_dict = json.loads(data)
            conversation = ConversationSession.from_dict(conversation_dict)

            logger.debug(
                "conversation_retrieved",
                conversation_id=conversation_id,
                message_count=len(conversation.messages),
                turn_count=conversation.turn_count
            )

            return conversation

        except Exception as e:
            logger.error(
                "Failed to retrieve conversation",
                conversation_id=conversation_id,
                error=str(e)
            )
            return None

    def save_conversation(self, conversation: ConversationSession) -> bool:
        """
        Save conversation to Redis with TTL

        Args:
            conversation: ConversationSession to save

        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()
            key = self._get_conversation_key(conversation.conversation_id)

            # Serialize conversation
            data = json.dumps(conversation.to_dict())

            # Save with TTL
            client.setex(key, CONVERSATION_TTL, data)

            logger.debug(
                "conversation_saved",
                conversation_id=conversation.conversation_id,
                message_count=len(conversation.messages),
                turn_count=conversation.turn_count,
                ttl=CONVERSATION_TTL
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to save conversation",
                conversation_id=conversation.conversation_id,
                error=str(e)
            )
            return False

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Add a message to an existing conversation

        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant)
            content: Message content
            metadata: Optional metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get or create conversation
            conversation = self.get_conversation(conversation_id)

            if conversation is None:
                # Create new conversation
                conversation = ConversationSession(conversation_id=conversation_id)

            # Add message
            conversation.add_message(role, content, metadata)

            # Save back to Redis
            return self.save_conversation(conversation)

        except Exception as e:
            logger.error(
                "Failed to add message to conversation",
                conversation_id=conversation_id,
                error=str(e)
            )
            return False

    def get_recent_messages(
        self,
        conversation_id: str,
        count: int = 3
    ) -> List[ConversationMessage]:
        """
        Get recent messages from conversation

        Args:
            conversation_id: Conversation ID
            count: Number of message PAIRS to return

        Returns:
            List of recent messages (up to count*2)
        """
        try:
            conversation = self.get_conversation(conversation_id)

            if conversation is None:
                return []

            return conversation.get_recent_messages(count)

        except Exception as e:
            logger.error(
                "Failed to get recent messages",
                conversation_id=conversation_id,
                error=str(e)
            )
            return []

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete conversation from Redis

        Args:
            conversation_id: Conversation ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            client = self._get_client()
            key = self._get_conversation_key(conversation_id)

            deleted = client.delete(key)

            if deleted:
                logger.info("conversation_deleted", conversation_id=conversation_id)
                return True

            logger.debug("conversation_not_found_for_deletion", conversation_id=conversation_id)
            return False

        except Exception as e:
            logger.error(
                "Failed to delete conversation",
                conversation_id=conversation_id,
                error=str(e)
            )
            return False

    def list_active_conversations(self, limit: int = 100) -> List[str]:
        """
        List active conversation IDs

        Args:
            limit: Maximum number of conversations to return

        Returns:
            List of conversation IDs
        """
        try:
            client = self._get_client()
            pattern = "conversation:*"

            # Scan for conversation keys
            conversation_ids = []
            for key in client.scan_iter(match=pattern, count=100):
                # Extract conversation_id from key
                conv_id = key.replace("conversation:", "")
                conversation_ids.append(conv_id)

                if len(conversation_ids) >= limit:
                    break

            logger.debug("active_conversations_listed", count=len(conversation_ids))
            return conversation_ids

        except Exception as e:
            logger.error("Failed to list conversations", error=str(e))
            return []

    def refresh_ttl(self, conversation_id: str) -> bool:
        """
        Refresh TTL for active conversation

        Args:
            conversation_id: Conversation ID

        Returns:
            True if TTL refreshed, False otherwise
        """
        try:
            client = self._get_client()
            key = self._get_conversation_key(conversation_id)

            # Check if key exists
            if not client.exists(key):
                return False

            # Reset TTL
            client.expire(key, CONVERSATION_TTL)

            logger.debug("conversation_ttl_refreshed", conversation_id=conversation_id)
            return True

        except Exception as e:
            logger.error(
                "Failed to refresh conversation TTL",
                conversation_id=conversation_id,
                error=str(e)
            )
            return False


# Singleton instance
_conversation_service = None


def get_conversation_service() -> ConversationService:
    """Get singleton ConversationService instance"""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
