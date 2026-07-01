"""Conversation state wrapper enforcing immutability of session snapshots."""

from pydantic import BaseModel, ConfigDict, Field

from app.agent.models import AgentAction, AgentIntent, ExtractedContext, TurnStatistics


class ImmutableConversationState(BaseModel):
    """Immutable snapshot of the conversation state at a specific dialogue turn."""

    model_config = ConfigDict(frozen=True)

    intent: AgentIntent = Field(..., description="Detected user intent.")
    active_context: ExtractedContext = Field(..., description="Active hiring requirements gathered.")
    turn_count: TurnStatistics = Field(..., description="Turn counting details.")
    missing_fields: list[str] = Field(default_factory=list, description="Context fields still needed.")
    next_action: AgentAction = Field(..., description="Next logical execution action.")
    is_valid: bool = Field(default=True, description="Dialogue flow sequence validation status.")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings compiled.")


# Alias for backward compatibility and clean naming
ConversationState = ImmutableConversationState
