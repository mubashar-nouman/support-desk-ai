"""
Agent state model for LangGraph workflows.

This is the core state object that flows through the agent graph.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import Field

from .base import BaseModelWithConfig, TicketCategory, TicketPriority, SentimentScore
from .message import Message

class AgentState(BaseModelWithConfig):
    """
    State object that flows through the LangGraph agent workflow.

    This represents the complete context available to all agents
    at any point in the workflow. Agents read from and write to this state.

    Attributes:
        # Input
        ticket_id: current ticket being processed.
        customer_id: Customer who created the ticket.
        messages: Conversation history
        current_message: The latest user message to process.

        # Classification (from Intake Agent)
        category: Classified ticket category
        priority: Assigned priority level
        sentiment: Detected sentiment
        intent: Detected user intent
        entities: Extracted entities (product names, order IDs, etc.)

        # Knowledge Retrieval (from Knowledge Agent)
        retrieved_documents: Relevant KB arcticles / docs
        knowledge_confidence: confidence in retrieved knowledge
        similar_tickets: Previously resolved similar tickets

        # Resolution (from Resolution Agent)
        proposed_resoponse: Generated response to user
        response_confidence: Confidence in the response
        requires_action: Whether actions need to be executed.

        # Actions (from Action Agent)
        actions_to_execute: List of actions to perform
        actions_executed: List of completed actions
        action_results: Results from executed actions

        # Escalation (from Escalation Agent)
        should_escalate: Whether to escalate to human
        escalation_reason: Why escalation is needed
        escalation_context: Context to pass to human agent

        # Metadata
        workflow_step: Current step in the workflow
        agent_history: Which agents have processed this
        metadata: Flexible storage for agent-specific data
        error: Any error that occurred during processing
    """

    # ===== Core Identifiers =====
    ticket_id: UUID = Field(..., description = "Ticket being processed")
    customer_id: UUID = Field(..., description = "Customer who created ticket")

    # ==== Messages =====
    messages: List[Message] = Field(
        default_factory = list,
        description = "Full conversation history"
    )
    current_message: str = Field(
        ...,
        min_length = 1,
        description = "Latest user message to process"
    )

    # ==== Classification (Intake Agent) ====
    category: Optional[TicketCategory] = Field(
        None,
        description = "Assigned Priority"
    )
    priority: Optional[TicketPriority] = Field(
        None,
        description = "Assigned Priority"
    )
    sentiment: Optional[SentimentScore] = Field(
        None,
        description = "Detected Sentiment"
    )
    intent: Optional[str] = Field(
        None,
        description = "Detected user intent"
    )
    entities: Dict[str, Any] = Field(
        default_factory = dict,
        description = "Extracted entities (order_id, product_name, etc.))"
    )

    # ===== Knowledge Retrieval (Knowledge Agent) ====
    retrieved_documents: List[Dict[str, Any]] = Field(
        default_factory = list,
        description = "Retrieved KB documents"
    )
    knowledge_confidence: Optional[float] = Field(
        None,
        ge = 0.0,
        le = 1.0,
        description = "Confidence in retrieved knowledge"
    )
    similar_tickets: List[Dict[str, Any]] = Field(
        default_factory = list,
        description = "Previously resolved similar tickets"
    )

    # ==== Resolution (Resolution Agent) ====
    proposed_response: Optional[str] = Field(
        None,
        description = "Generated response to user."
    )
    response_confidence: Optional[float] = Field(
        None,
        ge = 0.0,
        le = 1.0,
        description = "Confidence in the response"
    )
    requires_action: bool = Field(
        default = False,
        description = "Whether actions need execution"
    )
    
    # ==== Actions (Action Agent) ====
    actions_to_execute: List[Dict[str, Any]] = Field(
        default_factory = list,
        description = "Actions to perform"
    )
    actions_executed: List[str] = Field(
        default_factory = list,
        description = "Completed actions"
    )
    action_results: Dict[str, Any] = Field(
        default_factory = dict,
        description = "Results from actions"
    )

    # ==== Escalation (Escalation Agent) ====
    should_escalate: bool = Field(
        default = False,
        description = "Whether to escalate to human"
    )
    escalation_reason: Optional[str] = Field(
        None,
        description = "Reason for escalation"
    )
    escalation_context: Dict[str, Any] = Field(
        default_factory = dict,
        description = "Context for human agent"
    )

    # ==== Workflow Metadata =====
    workflow_step: str = Field(
        default = "intake",
        description = "Current workflow step"
    )
    agent_history: List[str] = Field(
        default_factory = list,
        description = "Agents that have processed this state."
    )
    metadata: Dict[str, Any] = Field(
        default_factory = dict,
        description = "Additional metadata"
    )
    error: Optional[str] = Field(
        None,
        description = "Error message if processing failed"
    )

    # ==== Helper Functions =====

    @property
    def has_error(self) -> bool:
        """ Check if there was an error. """
        return self.error is not None

    @property
    def is_high_priority(self) -> bool:
        """ Check if ticket is high priority. """
        return self.priority in [TicketPriority.HIGH, TicketPriority.URGENT]

    @property
    def has_negative_sentiment(self) -> bool:
        """ Check if sentiment is negative. """
        return self.sentiment in [
            SentimentScore.NEGATIVE,
            SentimentScore.VERY_NEGATIVE
        ]

    @property
    def has_sufficient_knowledge(self) -> bool:
        """ Check if we have good knowledge to respond. """
        return (
            self.knowledge_confidence is not None
            and self.knowledge_confidence >= 0.7
            and len(self.retrieved_documents) > 0
        )

    @property
    def has_high_confidence_response(self) -> bool:
        """ Check if response has high confidence. """
        return (
            self.response_confidence is not None
            and self.response_confidence >= 0.8
        )

    # ==== Helper Methods =====

    def add_agent_to_history(self, agent_name: str) -> None:
        """ Record that an agent has processed this state. """
        if agent_name not in self.agent_history:
            self.agent_history.append(agent_name)

    def set_workflow_step(self, step: str) -> None:
        """ Update the current workflow step. """
        self.workflow_step = step

    def add_retrieved_document(
        self,
        content: str,
        score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """ Add a retrievd document to the state. """
        doc = {
            "content": content,
            "score": score,
            "metadata": metadata or {}
        }
        self.retrieved_documents.append(doc)

    def add_action(
        self,
        action_type: str,
        params: Dict[str, Any]
    ) -> None:
        """ Add an action to be executed. """
        action = {
            "type": action_type,
            "params": params
        }
        self.actions_to_execute.append(action)

    def mark_action_executed(
        self,
        action_type: str,
        result: Any
    ) -> None:
        """ Mark an action as executed with its results. """
        self.actions_executed.append(action_type)
        self.action_results[action_type] = result

    def trigger_escalation(
        self,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """ Trigger escalation to human agent. """
        self.should_escalate = True
        self.escalation_reason = reason
        if context:
            self.escalation_context.update(context)

    def get_conversation_for_llm(self) -> List[Dict[str, str]]:
        """
        Get conversation history in LLM format.

        Returns:
            List of message dicts with "role" and "content"
        """
        history = [msg.to_llm_format() for msg in self.messages]
        # Add current message
        history.append(
            {
                "role": "user",
                "content": self.current_message
            }
        )
        return history

    def to_summary(self) -> Dict[str, Any]:
        """
        Create a summary of the current state.

        Useful for logging and debugging.
        """
        return {
            "ticket_id": str(self.ticket_id),
            "workflow_step": self.workflow_step,
            "category": self.category,
            "priority": self.priority,
            "sentiment": self.sentiment,
            "has_response": self.proposed_response is not None,
            "response_confidence": self.response_confidence,
            "requires_action": self.requires_action,
            "should_escalate": self.should_escalate,
            "escalation_reason": self.escalation_reason,
            "agents_processed": self.agent_history,
            "error": self.error
        }

    def __str__(self) -> str:
        return (
            f"AgentState(ticket = {self.ticket_id}, step = {self.workflow_step}, "
            f"category = {self.category}, escalate = {self.should_escalate}"
        )

class AgentStateCreate(BaseModelWithConfig):
    """ Schema for creating iniial agent state. """

    ticket_id: UUID
    customer_id: UUID
    current_message: str = Field(..., min_length = 1)
    messages: List[Message] = Field(default_factory = list)

