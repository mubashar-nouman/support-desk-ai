# Data Models

Quick reference for the data models. For full documentation, see [docs/models.md](../../docs/models.md).

## Quick Import

```python
from src.models import (
    # Models
    Message, Customer, Ticket, AgentState,
    
    # Enums
    MessageRole, TicketStatus, TicketCategory,
    SentimentScore, TicketPriority
)
```

## Core Models

- **Message**: Individual conversation messages
- **Customer**: Customer profiles and history
- **Ticket**: Support ticket with full lifecycle
- **AgentState**: LangGraph state object (flows through agents)

## Example Usage

```python
# Create a ticket
ticket = Ticket(
    customer_id=customer_id,
    subject="Password reset needed",
    category=TicketCategory.ACCOUNT_ACCESS
)

# Add a message
msg = Message(
    ticket_id=ticket.id,
    role=MessageRole.USER,
    content="I can't login"
)
ticket.add_message(msg)
```

See [full documentation](../../docs/models.md) for detailed examples and API reference.