"""
Customer model for user information & history.

Maintains customer profiles and interaction history.
"""

import email
#from time import timezone
from token import OP
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from pydantic import Field, EmailStr, field_validator

from .base import(
    BaseModelWithConfig,
    IndentifierMixin,
    TimestampMixin,
)

class CustomerTier(str):
    """
    Customer tier/segment for prioritization.
    """

    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class Customer(BaseModelWithConfig, IndentifierMixin, TimestampMixin):
    """
    Represents a customer in the system.

    Attributes:
        email: Customer Enail (unique identifier)
        name: Full Name
        tier: Account tier for prioritization
        phone: Optional phone number
        language: Preferred language (ISO 639-1 code)
        timezone_std: IANA timezone identifier
        metadata: Additional customer data (CRM ID, etc.)
        lifetime_tickets: Total number of tickets created
        satisfaction_score: Average CSAT score (0-100)
        last_interaction: Last time customer contacted support
        notes: Internal notes about the customer.
    """

    # Basic Info -
    email: EmailStr = Field(..., description = "Customer email address")
    name: str = Field(..., min_length = 1, description = "Customer full name")

    # Account Info -
    tier: str = Field(
        default = CustomerTier.FREE,
        description = "Customer account tier"
    )

    # Contact Info -
    phone: Optional[str] = Field(None, description = "Phone Number")

    # Preferences
    language: str = Field(
        default = "en",
        min_length = 2,
        max_length = 2,
        description = "ISO 639-1 language code"
    )
    timezone_std: str = Field(
        default = "UTC",
        description = "IANA timezone identifier"
    )

    # History & Stats
    lifetime_tickets: int = Field(
        default = 0,
        ge = 0,
        description = "Total tickets created"
    )
    satisfaction_score: Optional[float] = Field(
        None,
        ge = 0.0,
        le = 100.0,
        description = "Average CSAT score"
    )
    last_interaction: Optional[datetime] = Field(
        None,
        description = "Last support interaction"
    )

    # Internal
    notes: List[str] = Field(
        default_factory = list,
        description = "Internal notes about customer"
    )
    metadata: Dict[str, Any] = Field(
        default_factory = dict,
        description = "Additional customer data"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Ensure name is not just whitespace
        """
        if not v.strip():
            raise ValueError("Customer name cannot be empty")
        return v.strip()

    @field_validator('language')
    @classmethod
    def validate_language(cls, v: str) -> str:
        """
        Ensure langauge code is lowercase.
        """
        return v.lower()

    @property
    def is_premium(self) -> bool:
        """
        Check if customer is premium tier or higher.
        """
        return self.tier in [CustomerTier.PREMIUM, CustomerTier.ENTERPRISE]

    @property
    def is_new_customer(self) -> bool:
        """
        Check if this is a new customer (< 5 tickets)
        """
        return self.lifetime_tickets < 5

    @property
    def has_good_satisfaction(self) -> bool:
        """
        Check if the customer has good satisfaction score.
        """
        if self.satisfaction_score is None:
            return True # benefit of doubt for new customers.
        return self.satisfaction_score >= 70.0

    @property
    def display_name(self) -> str:
        """
        Get display name for UI.
        """
        return self.name

    def increment_ticket_count(self) -> None:
        """
        Increment lifetime ticket counter.
        """
        self.lifetime_tickets += 1
        self.last_interaction = datetime.now(timezone.utc)
        self.touch()

    def update_satisfaction(self, new_score: float) -> None:
        """
        Update satisfaction score with weighted average.

        Args:
            new_score: New CSAT score (0 - 100)
        """
        if self.satisfaction_score is None:
            self.satisfaction_score = new_score
        else:
            # Weighted average: 80 % old and 20 % new
            self.satisfaction_score = (
                0.8 * self.satisfaction_score + 0.2 * new_score
            )
        self.touch()

    def add_note(self, note: str) -> None:
        """
        Add an internal note about the customer.
        """
        if note.strip():
            self.notes.append(note.strip())
            self.touch()

    def get_crm_id(self) -> Optional[str]:
        """
        Get CRM ID from metadata if available.
        """
        return self.metadata.get("crm_id")

    def __str__(self) -> str:
        return f"{self.name} ({self.email})"

    def __repr__(self) -> str:
        return (
            f"Customer(id = {self.id}, email = {self.email}, "
            f"tier = {self.tier}, tickets = {self.lifetime_tickets})"
        )

class CustomerCreate(BaseModelWithConfig):
    """
    Schema for creating new customers.
    """

    email: EmailStr
    name: str = Field(..., min_length = 1)
    tier: str = Field(default = CustomerTier.FREE)
    phone: Optional[str] = None
    language: str = Field(default = "en")
    timezone_std: str = Field(default = "UTC")
    metadata: Dict[str, Any] = Field(default_factory = dict)

class CiustomerUpdate(BaseModelWithConfig):
    """
    Schema for updating existing customers.
    """

    name: Optional[str] = Field(None, min_length = 1)
    tier: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = None
    timezone_std: Optional[str] = None
    satisfaction_score: Optional[float] = Field(None, ge = 0.0, le = 100.0)
    notes: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None