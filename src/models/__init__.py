"""
Data models for the AI Customer Service System.

This package contains all Pydantic models used throughout the application.
"""

from .base import (
    # Base Classes
    BaseModelWithConfig,
    TimestampMixin,
    IndentifierMixin,

    # Enums
    TicketStatus,
    TicketCategory,
    TicketPriority,
    MessageRole,
    SentimentScore,
    AgentType,
)

from .message import (
    Message,
    MessageCreate,
    MessageUpdate,
)

from .customer import (
    Customer,
    CustomerCreate,
    CiustomerUpdate,
    CustomerTier,
)

from .ticket import (
    Ticket,
    TicketCreate,
    TicketUpdate,
)

from .agent_state import (
    AgentState,
    AgentStateCreate,
)

__all__ = [
    # Base
    "BaseModelWithConfig",
    "TimestampMixin",
    "IndentifierMixin",

    # Enums
    "TicketStatus",
    "TicketCategory",
    "TicketPriority",
    "MessageRole",
    "SentimentScore",
    "AgentType",

    # Message
    "Message",
    "MessageCreate",
    "MessageUpdate",

    # Customer
    "Customer",
    "CustomerCreate",
    "CiustomerUpdate",
    "CustomerTier",

    # Ticket
    "Ticket",
    "TicketCreate",
    "TicketUpdate",

    # Agent State
    "AgentState",
    "AgentStateCreate",
]