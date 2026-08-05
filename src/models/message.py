"""
Message model for customer-agent conversations.

Messages are the atomic units of communication in the system.
"""

from token import OP
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import Field, field_validator

from .base import (
    BaseModelWithConfig,
    IndentifierMixin,
    TimestampMixin,
    MessageRole,
    SentimentScore
)

class Message(BaseModelWithConfig, IndentifierMixin, TimestampMixin):
    """
    Represents a single message in a conversation.

    Attributes:
        ticket_id: Reference to the parent ticket.
        role: Who sent the message (user, assistant, system)
        content: The actual message text
        sentiment: Detected sentiment of the message
        metadata: Additional data (tokens used, model info etc.)
        agent_type: Which agent generated this (if assistant)
        confidence_score: Confidence in the response (0-1)
        escalation_flag: Whether this message triggered escalation
    """

    ticket_id: UUID = Field(..., description = "Parent Ticket Id")
    role: MessageRole = Field(..., description = "Message sender role")
    content: str = Field(..., min_length = 1, description = "Message Content")

    # Analysis fields -
    sentiment: Optional[SentimentScore] = Field(
        None,
        description = "Sentiment analysis result"
    )

    # Agent metadata
    agent_type: Optional[str] = Field(
        None,
        description = "Type of agent that generated this message"
    )
    confidence_score: Optional[float] = Field(
        None,
        ge = 0.0,
        le = 1.0,
        description = "Confidence score for AI responses"
    )

    # Flags
    escalation_flag: bool = Field(
        default = False,
        description = "Whether this triggered escalation"
    )

    # Flexible metadata storage
    metadata: Dict[str, Any] = Field(
        default_factory = dict,
        description = "Additional metadata (model, tokens, etc.)"
    )

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """ 
        Ensure content is not just whitespace.
        """
        if not v.strip():
            raise ValueError("Message content cannot be empty or just whitespace.")
        return v.strip()

    @property
    def is_from_user(self) -> bool:
        """
        Check if message is from user.
        """
        return self.role == MessageRole.USER

    @property
    def is_from_assistant(self) -> bool:
        """
        Check if message is from assistant.
        """
        return self.role == MessageRole.ASSISTANT

    @property
    def is_negative_sentiment(self) -> bool:
        """
        Check if message has negative sentiment
        """
        return self.sentiment in [
            SentimentScore.NEGATIVE,
            SentimentScore.VERY_NEGATIVE
        ]

    @property
    def token_count(self) -> Optional[int]:
        """
        Get token count from metadata if available.
        """
        return self.metadata.get("token_count")

    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add a metadata entry.
        """
        self.metadata[key] = value
        self.touch()

    def to_llm_format(self) -> Dict[str, str]:
        """
        Convert to format expected by LLM APIs.

        Returns:
            Dict with 'role' and 'content' keys.
        """
        return {
            "role": self.role if isinstance(self.role, str) else self.role.value,
            "content": self.content
        }

    def __str__(self) -> str:
        return f"{self.role.value}: {self.content[:50]}..."

    def __repr__(self) -> str:
        return(
            f"Message(id = {self.id}, role = {self.role}, "
            f"content = '{self.content[:30]}...', sentiment = {self.sentiment})"
        )

class MessageCreate(BaseModelWithConfig):
    """
    Schema for creating new messages.
    """

    ticket_id: UUID
    role: MessageRole
    content: str = Field(..., min_length = 1)
    sentiment: Optional[SentimentScore] = None
    agent_type: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory = dict)

class MessageUpdate(BaseModelWithConfig):
    """
    Schema for updating existing messages.
    """

    content: Optional[str] = Field(None, min_length = 1)
    sentiment: Optional[SentimentScore] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    escalation_flag: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


