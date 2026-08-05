"""
Base models and enums for AI Customer Service System.

This module provides foundational data structures used across all agents.
"""

from datetime import datetime, timezone
from enum import Enum
#from time import timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict, field_serializer

class TicketStatus(str, Enum):
    """
    Status of a support ticket throughout its lifecycle.
    """

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketCategory(str, Enum):
    """Categories for ticket classification.
    """

    ACCOUNT_ACCESS = "account_access"
    BILLING = "billing"
    TECHNICAL = "technical"
    PRODUCT = "product"
    SHIPPING = "shipping"
    REFUND = "refund"
    GENERAL = "general"
    OTHER = "other"

class TicketPriority(str, Enum):
    """
    Priority levels for tickets.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class MessageRole(str, Enum):
    """
    Role of the message sender.
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class SentimentScore(str, Enum):
    """
    Sentiment analysis results.
    """

    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"

class AgentType(str, Enum):
    """
    Types of agents in the system
    """

    INTAKE = "intake"
    KNOWLEDGE = "knowledge"
    RESOLUTION = "resolution"
    ACTION = "action"
    ESCALATION = "escalation"
    ORCHESTRATOR = "orchestrator"

class BaseModelWithConfig(BaseModel):
    """
    Base model with common configiration for all Pydantic Models

    Features -
    - Immutable by default (frozen)
    - Validates on assignment
    - Uses Python 3.11+ type hints
    - JSON serialization support
    """

    model_config = ConfigDict(
        frozen = False, # allow mutation for database updates
        validate_assignment = True,
        use_enum_values = True,
        arbitrary_types_allowed = True,
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )

class TimestampMixin(BaseModel):
    """
    Mixin for models that need timestamps.
    """

    created_at: datetime = Field(default_factory = lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory = lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        """ 
        Update the updated_at timestamp.
        """
        self.updated_at = datetime.now(timezone.utc)

class IndentifierMixin(BaseModel):
    """
    Mixin for models that need unique identifiers.
    """

    id: UUID = Field(default_factory = uuid4)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IndentifierMixin):
            return False

        return self.id == other.id
