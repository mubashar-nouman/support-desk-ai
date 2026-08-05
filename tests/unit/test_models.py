"""

Unit tests for data models. This is a comprehensive test file to verify our models work correctly.

Tests all model creation, validation, and methods.

"""

import uuid
import pytest
from datetime import datetime
from uuid import uuid4

from src.models import (
    # Models
    Message,
    Customer,
    Ticket,
    AgentState,

    # Enums
    MessageRole,
    SentimentScore,
    TicketStatus,
    TicketCategory,
    TicketPriority,
    CustomerTier,
    customer,
    ticket,
)

class TestMessage:
    """ Tests for Message Model. """

    def test_create_message(self):
        """ Test basic message creation. """
        ticket_id = uuid4()
        msg = Message(
            ticket_id = ticket_id,
            role = MessageRole.USER,
            content = "I need help with my password"
        )

        assert msg.ticket_id == ticket_id
        assert msg.role == MessageRole.USER
        assert msg.content == "I need help with my password"
        assert msg.sentiment is None
        assert msg.escalation_flag is False

    def test_message_validation(self):
        """ Test message content validation. """
        ticket_id = uuid4()

        # Empty content should fail
        with pytest.raises(ValueError):
            Message(
                ticket_id = ticket_id,
                role = MessageRole.USER,
                content = ""
            )

        # Whitespace only should fail
        with pytest.raises(ValueError):
            Message(
                ticket_id = ticket_id,
                role = MessageRole.USER,
                content = "   "
            )

    def test_message_properties(self):
        """ Test message helper properties """
        ticket_id = uuid4()

        user_msg = Message(
            ticket_id = ticket_id,
            role = MessageRole.USER,
            content = "Help me",
            sentiment = SentimentScore.NEGATIVE
        )

        assert user_msg.is_from_user is True
        assert user_msg.is_from_assistant is False
        assert user_msg.is_negative_sentiment is True

    def test_message_to_llm_format(self):
        """ Test conversion to LLM format. """
        ticket_id = uuid4()
        msg = Message(
            ticket_id = ticket_id,
            role = MessageRole.USER,
            content = "Hello"
        )

        llm_format = msg.to_llm_format()
        assert llm_format == {"role": "user", "content": "Hello"}

class TestCustomer:
    """ Tests for Customer Model. """

    def test_create_customer(self):
        """ Test basic customer creation. """
        customer = Customer(
            email = "test@example.com",
            name = "John Doe"
        )

        assert customer.email == "test@example.com"
        assert customer.name == "John Doe"
        assert customer.tier == CustomerTier.FREE
        assert customer.lifetime_tickets == 0
        assert customer.language == "en"

    def test_customer_validation(self):
        """ Test customer validation. """
        
        # Empty name should fail
        with pytest.raises(ValueError):
            Customer(
                email = "test@example.com",
                name = ""
            )

        # Invalid email should fail
        with pytest.raises(ValueError):
            Customer(
                email = "invalid-email",
                name = "John Doe"
            )

    def test_customer_properties(self):
        """ Test customer helper functions. """
        premium_customer = Customer(
            email = "premium@example.com",
            name = "Premium User",
            tier = CustomerTier.PREMIUM,
            lifetime_tickets = 3
        )

        assert premium_customer.is_premium is True
        assert premium_customer.is_new_customer is True

    def test_increment_ticket_count(self):
        """ Test ticket count increment. """
        customer = Customer(
            email = "test@example.com",
            name = "John Doe"
        )

        assert customer.lifetime_tickets == 0
        assert customer.last_interaction is None

        customer.increment_ticket_count()
        
        assert customer.lifetime_tickets == 1
        assert customer.last_interaction is not None

    def test_update_satisfaction(self):
        """ Test satisfaction score update. """
        customer = Customer(
            email = "test@example.com",
            name = "John Doe"
        )

        # First Score
        customer.update_satisfaction(80.0)
        assert customer.satisfaction_score == 80.0

        # Weighted average
        customer.update_satisfaction(60.0)
        expected = 0.8 * 80.0 + 0.2 * 60.0
        assert customer.satisfaction_score == expected

class TestTicket:
    """ Tests for Ticket Model. """

    def test_create_ticket(self):
        """ Test basic ticket creation. """
        customer_id = uuid4()
        ticket = Ticket(
            customer_id = customer_id,
            subject = "Password reset needed"
        )

        assert ticket.customer_id == customer_id
        assert ticket.subject == "Password reset needed"
        assert ticket.status == TicketStatus.OPEN
        assert ticket.category == TicketCategory.GENERAL
        assert ticket.priority == TicketPriority.MEDIUM
        assert len(ticket.messages) == 0

    def test_ticket_properties(self):
        """ Test ticket helper properties. """
        customer_id = uuid4()
        ticket = Ticket(
            customer_id = customer_id,
            subject = "Test Ticket",
            status = TicketStatus.OPEN
        )

        assert ticket.is_open is True
        assert ticket.is_resolved is False
        assert ticket.is_escalated is False

    def test_add_message(self):
        """ Test adding messages to ticket. """
        customer_id = uuid4()
        ticket = Ticket(
            customer_id = customer_id,
            subject = "Test Ticket"
        )

        msg = Message(
            ticket_id = ticket.id,
            role = MessageRole.USER,
            content = "Help needed"
        )

        ticket.add_message(msg)

        assert len(ticket.messages) == 1
        assert ticket.last_message == msg

    def test_escalate(self):
        """ Test ticket escalation. """
        customer_id = uuid4()
        ticket = Ticket(
            customer_id = customer_id,
            subject = "Complex issue"
        )

        ticket.escalate(agent_id = "agent-123", reason = "Complex technical issue")

        assert ticket.status == TicketStatus.ESCALATED
        assert ticket.assigned_to == "agent-123"
        assert ticket.automated is False
        assert ticket.is_escalated is True

    def test_resolve(self):
        """ Test ticket resolution. """
        customer_id = uuid4()
        ticket = Ticket(
            customer_id = customer_id,
            subject = "Password Issue"
        )

        ticket.resolve(
            summary = "Password reset link sent",
            satisfaction = 5
        )

        assert ticket.status == TicketStatus.RESOLVED
        assert ticket.resolution_summary == "Password reset link sent"
        assert ticket.satisfaction_rating == 5
        assert ticket.resolution_time is not None

    def test_get_conversation_history(self):
        """ Test conversation history extraction. """
        customer_id = uuid4()
        ticket = Ticket(
            customer_id = customer_id,
            subject = "Test"
        )

        msg1 = Message(
            ticket_id = ticket.id,
            role = MessageRole.USER,
            content = "Hellp"
        )

        msg2 = Message(
            ticket_id = ticket.id,
            role = MessageRole.ASSISTANT,
            content = "Hi, how can I help ?"
        )

        ticket.add_message(msg1)
        ticket.add_message(msg2)

        history = ticket.get_conversation_history()

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

class TestAgentState:
    """ Tests for AgentState model. """

    def test_create_agent_state(self):
        """ Tests basic agent state creation. """
        ticket_id = uuid4()
        customer_id = uuid4()

        state = AgentState(
            ticket_id = ticket_id,
            customer_id = customer_id,
            current_message = "I need help"
        )

        assert state.ticket_id == ticket_id
        assert state.customer_id == customer_id
        assert state.current_message == "I need help"
        assert state.workflow_step == "intake"
        assert state.should_escalate is False

    def test_agent_state_properties(self):
        """ Test agent state helper properties. """
        ticket_id = uuid4()
        customer_id = uuid4()

        state = AgentState(
            ticket_id = ticket_id,
            customer_id = customer_id,
            current_message = "Test",
            priority = TicketPriority.HIGH,
            sentiment = SentimentScore.NEGATIVE,
            knowledge_confidence = 0.8,
            retrieved_documents = [{"content": "test"}]
        )
        
        assert state.is_high_priority is True
        assert state.has_negative_sentiment is True
        assert state.has_sufficient_knowledge is True

    def test_add_agent_to_history(self):
        """ Test tracking agent history. """
        ticket_id = uuid4()
        customer_id = uuid4()

        state = AgentState(
            ticket_id = ticket_id,
            customer_id = customer_id,
            current_message = "Test"
        )

        state.add_agent_to_history("intake")
        state.add_agent_to_history("knowledge")

        assert len(state.agent_history) == 2
        assert "intake" in state.agent_history
        assert "knowledge" in state.agent_history

    def test_add_retrieved_document(self):
        """ Test adding retrieved documents. """
        ticket_id = uuid4()
        customer_id = uuid4()

        state = AgentState(
            ticket_id = ticket_id,
            customer_id = customer_id,
            current_message = "Test"
        )

        state.add_retrieved_document(
            content = "How to reset password",
            score = 0.95,
            metadata = {"source": "kb_article_123"}
        )

        assert len(state.retrieved_documents) == 1
        assert state.retrieved_documents[0]["score"] == 0.95

    def test_trigger_escalation(self):
        """ Test escalation triggering. """
        ticket_id = uuid4()
        customer_id = uuid4()

        state = AgentState(
            ticket_id = ticket_id,
            customer_id = customer_id,
            current_message = "Complex technical issue"
        )

        state.trigger_escalation(
            reason = "Requires human expertise",
            context = {"complexity": "high"}
        )

        assert state.should_escalate is True
        assert state.escalation_reason == "Requires human expertise"
        assert state.escalation_context["complexity"] == "high"

    def test_get_conversation_for_llm(self):
        """ Test LLM conversation format. """
        ticket_id = uuid4()
        customer_id = uuid4()

        msg = Message(
            ticket_id = ticket_id,
            role = MessageRole.USER,
            content = "Previous message"
        )

        state = AgentState(
            ticket_id = ticket_id,
            customer_id = customer_id,
            current_message = "Current message",
            messages = [msg] 
        )

        conversation = state.get_conversation_for_llm()

        assert len(conversation) == 2
        assert conversation[0]["content"] == "Previous message"
        assert conversation[1]["content"] == "Current message"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])