#!/usr/bin/env python3

"""
Quick validation script to test model functionality.

Run this to ensure all models are working correctly.
"""

from re import M
from uuid import uuid4

from numpy.matlib import mask_indices
from src.models import (
    AgentType,
    Message,
    Customer,
    Ticket,
    AgentState,
    MessageRole,
    SentimentScore,
    TicketStatus,
    TicketCategory,
    TicketPriority,
    CustomerTier,
    ticket,
)

def test_models():
    """ Run through a complete workflow to validate models. """

    print("🧪 Testing AI Customer Service Models\n")

    # 1. Create a customer
    print("1️⃣ Creating customer ...")
    customer = Customer(
        email = "john.doe@example.com",
        name = "John Doe",
        tier = CustomerTier.PREMIUM
    )
    
    print(f"    ✅ Customer created: {customer}")
    print(f"    - ID: {customer.id}")
    print(f"    - Is Premium: {customer.is_premium}")

    # 2. Create a ticket
    print("\n2️⃣  Creating ticket ...")
    ticket = Ticket(
        customer_id = customer.id,
        subject = "Cannot login to my account",
        category = TicketCategory.ACCOUNT_ACCESS,
        priority = TicketPriority.HIGH
    )
    print(f"   ✅ Ticket created: {ticket}")
    print(f"    - Status: {ticket.status}")
    print(f"    - Is Open: {ticket.is_open}")

    # 3. Add messages -
    print("\n 3️⃣ Adding messages to ticket...")

    user_msg = Message(
        ticket_id = ticket.id,
        role = MessageRole.USER,
        content = "I forgot my password and can't login",
        sentiment = SentimentScore.NEUTRAL
    )
    ticket.add_message(user_msg)
    print(f"    ✅ User message added")

    assistant_msg = Message(
        ticket_id = ticket.id,
        role = MessageRole.ASSISTANT,
        content = "I can help you reset your password right away!",
        sentiment = SentimentScore.POSITIVE,
        agent_type = "resolution",
        confidence_score = 0.95
    )
    ticket.add_message(assistant_msg)
    print(f"    ✅ Assistant message added")
    print(f"    - Total messages: {ticket.message_count}")
    print(f"    - First response time: {ticket.first_response_time:.2f}s")

    # 4. Create agent state
    print("\n4️⃣ Creating agent state for workflow ...")
    agent_state = AgentState(
        ticket_id = ticket.id,
        customer_id = customer.id,
        current_message = "Please help me reset my password.", 
        messages = ticket.messages,
        category = TicketCategory.ACCOUNT_ACCESS,
        priority = TicketPriority.HIGH,
        sentiment = SentimentScore.NEUTRAL
    )
    print(f"   ✅ Agent state created: {agent_state}")

    # 5. Simulate Workflow
    print("\n5️⃣   Simulating agent workflow ...")

    # Intake agent
    agent_state.add_agent_to_history("intake")
    agent_state.set_workflow_step("knowledge_retrieval")
    print(f"   ✅ Intake agent processed")

    # Knowledge agent
    agent_state.add_retrieved_document(
        content = "To reset password, clcik 'Forgot Password' on login page",
        score = 0.92,
        metadata = {"source": "kb_article_42"}
    )
    agent_state.knowledge_confidence = 0.92
    agent_state.add_agent_to_history("knowledge")
    agent_state.set_workflow_step("resolution")
    print(f"   ✅ Knowledge agent processed")
    print(f"    - Retrieved {len(agent_state.retrieved_documents)} documents")
    print(f"    - Knowledge confidence: {agent_state.knowledge_confidence}")

    # Resolution agent 
    agent_state.proposed_response = (
        "I can help you reset your password. I've sent a reset link to "
        "your registered email address. Please check your inbox!"
    )
    agent_state.response_confidence = 0.95
    agent_state.requires_action = True
    agent_state.add_agent_to_history("resolution")
    agent_state.set_workflow_step("action")
    print(f"   ✅  Resolution agent processed")
    print(f"    - Response confidence: {agent_state.response_confidence}")

    # Action agent
    agent_state.add_action(
        action_type = "send_password_reset_email",
        params = {"email": customer.email}
    )
    agent_state.mark_action_executed(
        action_type = "send_password_reset_email",
        result = {"status": "sent", "email": customer.email}
    )
    agent_state.add_agent_to_history("action")
    print(f"   ✅ Action agent processed")
    print(f"    - Actions executed: {len(agent_state.actions_executed)}")

    # 6. Check escalation decision
    print("\n 6️⃣ Checking escalation ...")
    if agent_state.has_high_confidence_response and not agent_state.has_error:
        print(f"   ✅ No escalation needed (confidence: {agent_state.response_confidence})")
    else:
        agent_state.trigger_escalation(
            reason = "Low confidence response",
            context = {"confidence": agent_state.response_confidence}
        )
        print(f"   ⚠️ Escalate to human agent")

    # 7. Resolve ticket
    print("\n7️⃣  Resolving ticket ...")
    ticket.resolve(
        summary = "Password reset link sent successfully.",
        satisfaction = 5
    )
    customer.update_satisfaction(90.0)
    customer.increment_ticket_count()
    print(f"    ✅ Ticket resolved")
    print(f"    - Resolution time: {ticket.resolution_time:.2f}s")
    print(f"    - Automated: {ticket.automated}")
    print(f"    - Customer satisfaction: {ticket.satisfaction_rating} / 5")

    # 8. Print Summary
    print("\n" + "="*60)
    print("📊 WORKFLOW SUMMARY")
    print("="*60)

    ticket_metrics = ticket.calculate_metrics()
    print(f"\n🎫 Ticket Metrics:")
    for key, value in ticket_metrics.items():
        print(f"    -  {key}: {value}")

    state_summary = agent_state.to_summary()
    print(f"\n🤖 Agent State Summary: ")
    for key, value in state_summary.items():
        print(f"    - {key}: {value}")

    print(f"\n👤 Customer Stats: ")
    print(f"    - Total tickets: {customer.lifetime_tickets}")
    print(f"    - Satisfaction: {customer.satisfaction_score:.1f}%")
    print(f"    - Is Premium: {customer.is_premium}")

    print(f"\n👤 Customer Stats: ")
    print(f"    - Total tickets: {customer.lifetime_tickets}")
    print(f"    - Satisfaction: {customer.satisfaction_score:.1f}%")
    print(f"    - Is Premium: {customer.is_premium}")

    print("\n✅ All models validated successfully!")
    print("="*60)

if __name__ == "__main__":
    test_models()