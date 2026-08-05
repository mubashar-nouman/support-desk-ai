"""
Ticket model for support requests.

Tickets represent the entire lifecycle of a customer support interaction.
"""

from multiprocessing import Value
from optparse import Option
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from unicodedata import category
from uuid import UUID

from pydantic import Field, field_validator

from .base import (
    BaseModelWithConfig,
    IndentifierMixin,
    TimestampMixin,
    TicketStatus,
    TicketCategory,
    TicketPriority,
)

from .message import Message

class Ticket(BaseModelWithConfig, IndentifierMixin, TimestampMixin):
    """
    Represents a support ticket.

    Attributes:
        customer_id: Reference to the customer
        subject: Ticket subject/title
        status: Current ticket status
        category: Classified category
        priority: Ticket priority level
        messages: List of conversation messages
        assigned_to: Agent ID if escalated to human
        resolution_summary: Summary of how ticket was resolved.
        tags: Searchable tags for the ticket.
        metadata: Additional ticket data
        first_response_time: Time to first agent response
        resolution_time: Time to ticket resolution
        satisfaction_rating: Customer satisfaction (1-5)
        automated: Whether resolved by AI (not escalated)
    """

    # Core Fields
    customer_id: UUID = Field(..., description = "Customer who created ticket.")
    subject: str = Field(..., min_length = 1, description = "Ticket Subject")

    # Status & Classification
    status: TicketStatus = Field(
        default = TicketStatus.OPEN,
        description = "Current ticket status"
    )
    category: TicketCategory = Field(
        default = TicketCategory.GENERAL,
        description = "Classified ticket category"
    )
    priority: TicketPriority = Field(
        default = TicketPriority.MEDIUM,
        description = "Ticket priority"
    )

    # Messages 
    messages: List[Message] = Field(
        default_factory = list,
        description = "Conversation messages"
    )

    # Assignment
    assigned_to: Optional[str] = Field(
        None,
        description = "Human agent ID if escalated"
    )

    # Resolution
    resolution_summary: Optional[str] = Field(
        None,
        description = "Summary of resolution"
    )

    # Metadata
    tags: List[str] = Field(
        default_factory = list,
        description = "Searchable tags"
    )
    metadata: Dict[str, Any] = Field(
        default_factory = dict,
        description = "Additional data"
    )

    # Metrics
    first_response_time: Optional[float] = Field(
        None,
        ge = 0.0,
        description = "Seconds to first response"
    )
    resolution_time: Optional[float] = Field(
        None,
        ge = 0.0,
        description = "Seconds to resolution"
    )
    satisfaction_rating: Optional[int] = Field(
        None,
        ge = 1,
        le = 5,
        description = "Customer satrisfaction (1-5)"
    )

    # Automation Tracking
    automated: bool = Field(
        default = True,
        description = "Whether resolved by AI"
    )


    @field_validator('subject')
    @classmethod
    def validate_subject(cls, v: str) -> str:
        """
        Ensure subject is not just whitespace.
        """
        if not v.strip():
            raise ValueError("Ticket subject cannot be empty")
        return v.strip()

    @property
    def is_open(self) -> bool:
        """
        Check if ticket is still open.
        """
        return self.status in [
            TicketStatus.OPEN,
            TicketStatus.IN_PROGRESS,
            TicketStatus.WAITING_FOR_CUSTOMER
        ]

    @property
    def is_resolved(self) -> bool:
        """
        Check if the ticket is resolved.
        """
        return self.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]

    @property
    def is_escalated(self) -> bool:
        """
        Check if ticket was escalated to human.
        """
        return self.status == TicketStatus.ESCALATED or self.assigned_to is not None

    @property
    def message_count(self) -> int:
        """
        Get total number of messages.
        """
        return len(self.messages)

    @property
    def last_message(self) -> Optional[Message]:
        """
        Get the most reecent message.
        """
        return self.messages[-1] if self.messages else None

    @property
    def user_messages(self) -> List[Message]:
        """
        Get all messages from user.
        """
        return [m for m in self.messages if m.is_from_user]

    @property
    def assistant_messages(self) -> List[Message]:
        """
        Get all messages from assistant.
        """
        return [m for m in self.messages if m.is_from_assistant]

    def add_message(self, message: Message) -> None:
        """
        Add a message to the tikcet.

        Args:
            message: Message to add
        """
        self.messages.append(message)

        # Update first response time if this is first assistant message
        if message.is_from_assistant and self.first_response_time is None:
            time_diff = (message.created_at - self.created_at).total_seconds()
            self.first_response_time = time_diff

        self.touch()

    def add_tag(self, tag: str) -> None:
        """
        Add a tag to the ticket.
        """
        tag = tag.strip().lower()
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.touch()

    def escalate(self, agent_id: str, reason: Optional[str] = None) -> None:
        """
        Escalate ticket to human agent.

        Args:
            agent_id: ID of the human agent
            reason: Optional reason for escalation
        """

        self.status = TicketStatus.ESCALATED
        self.assigned_to = agent_id
        self.automated = False

        if reason:
            self.metadata["escalation_reason"] = reason

        self.touch()
        
    def resolve(self, summary: str, satisfaction: Optional[int] = None) -> None:
        """
        Mark ticket as resolved.

        Args:
            summary: Resolution summary
            satisfaction: Optional CSAT rating (1-5)
        """

        self.status = TicketStatus.RESOLVED
        self.resolution_summary = summary

        if satisfaction is not None:
            self.satisfaction_rating = satisfaction

        # Calculate resolution time
        self.resolution_time = (
            datetime.now(timezone.utc) - self.created_at
        ).total_seconds()

        self.touch()

    def close(self) -> None:
        """
        Close the ticket.
        """
        if not self.is_resolved:
            raise ValueError("Cannot close ticket that is not resolved.")

        self.status = TicketStatus.CLOSED
        self.touch()

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Get conversation in LLM-friendly format.

        Returns:
            List of dicts with "role" and "content"
        """
        return [msg.to_llm_format() for msg in self.messages]

    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Calculate ticket metrics.

        Returns:
            Dict with various metrics.
        """
        return {
            "message_count": self.message_count,
            "user_messages": len(self.user_messages),
            "assistant_messages": len(self.assistant_messages),
            "first_response_time": self.first_response_time,
            "resolution_time": self.resolution_time,
            "automated": self.automated,
            "escalated": self.is_escalated,
            "satisfaction_rating": self.satisfaction_rating,
        }

    def __str__(self) -> str:
        return f"Ticket #{self.id}: {self.subject} [{self.status}]"

    def __repr__(self) -> str:
        return (
            f"Ticket(id = {self.id}, subject = '{self.subject}',  "
            f"status = {self.status}, category = {self.category})"
        )

class TicketCreate(BaseModelWithConfig):
    """
    Schema for creating new tickets.
    """

    customer_id: UUID
    subject: str = Field(..., min_length = 1)
    category: TicketCategory = Field(default = TicketCategory.GENERAL)
    priority: TicketPriority = Field(default = TicketPriority.MEDIUM)
    tags: List[str] = Field(default_factory = list)
    metadata: Dict[str, Any] = Field(default_factory = dict)

class TicketUpdate(BaseModelWithConfig):
    """
    Schema for updating existing tickets.
    """

    subject: Optional[str] = Field(None, min_length = 1)
    status: Optional[TicketStatus] = None
    category: Optional[TicketCategory] = None
    priority: Optional[TicketPriority] = None
    assigned_to: Optional[str] = None
    resolution_summary: Optional[str] = None
    satisfaction_rating: Optional[int] = Field(None, ge = 1, le = 5)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None