"""
Conversation Models
Data structures for conversation persistence and management
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message role in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationMessage(BaseModel):
    """
    Single message in a conversation
    """
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationSession(BaseModel):
    """
    Complete conversation session with metadata
    """
    conversation_id: str
    messages: List[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    metadata: Optional[dict] = None
    summary: Optional[str] = None  # Generated after 10 turns
    turn_count: int = 0  # Number of user-assistant exchanges

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def add_message(self, role: MessageRole, content: str, metadata: Optional[dict] = None):
        """Add a message to the conversation"""
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata
        )
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

        # Update turn count (pair of user + assistant messages)
        if role == MessageRole.ASSISTANT:
            self.turn_count += 1

    def get_recent_messages(self, count: int = 3) -> List[ConversationMessage]:
        """
        Get the most recent message pairs

        Args:
            count: Number of message PAIRS to return (default: 3 pairs = 6 messages)

        Returns:
            List of recent messages (up to count*2 messages)
        """
        # Get last N pairs of messages (user + assistant)
        max_messages = count * 2
        return self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages

    def should_summarize(self, threshold: int = 10) -> bool:
        """
        Check if conversation should be summarized

        Args:
            threshold: Turn count threshold for summarization

        Returns:
            True if turn count >= threshold and no summary exists
        """
        return self.turn_count >= threshold and self.summary is None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "conversation_id": self.conversation_id,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata
                }
                for msg in self.messages
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "user_id": self.user_id,
            "metadata": self.metadata,
            "summary": self.summary,
            "turn_count": self.turn_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationSession":
        """Create ConversationSession from dictionary"""
        messages = [
            ConversationMessage(
                role=MessageRole(msg["role"]),
                content=msg["content"],
                timestamp=datetime.fromisoformat(msg["timestamp"]),
                metadata=msg.get("metadata")
            )
            for msg in data.get("messages", [])
        ]

        return cls(
            conversation_id=data["conversation_id"],
            messages=messages,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            user_id=data.get("user_id"),
            metadata=data.get("metadata"),
            summary=data.get("summary"),
            turn_count=data.get("turn_count", 0)
        )


class ConversationSummary(BaseModel):
    """
    Summary of a conversation for context compression
    """
    conversation_id: str
    summary_text: str
    messages_summarized: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
