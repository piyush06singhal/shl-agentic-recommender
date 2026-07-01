"""Data schemas and enums defining conversation state and extracted context."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AgentIntent(str, Enum):
    """Supported dialogue intents detected from user input."""

    GREETING = "Greeting"
    CLARIFICATION = "Clarification"
    RECOMMENDATION = "Recommendation"
    REFINEMENT = "Refinement"
    COMPARISON = "Comparison"
    HELP = "Help"
    CONVERSATION_END = "Conversation End"
    OUT_OF_SCOPE = "Out Of Scope"
    PROMPT_INJECTION = "Prompt Injection"
    UNKNOWN = "Unknown"


class AgentAction(str, Enum):
    """Next logical execution actions decided by the engine."""

    ASK_CLARIFICATION = "ASK_CLARIFICATION"
    RETRIEVE = "RETRIEVE"
    COMPARE = "COMPARE"
    REFUSE = "REFUSE"
    RESPOND_GREETING = "RESPOND_GREETING"
    RESPOND_HELP = "RESPOND_HELP"
    END_CONVERSATION = "END_CONVERSATION"
    UNKNOWN = "UNKNOWN"


class ExtractedContext(BaseModel):
    """Reconstructed hiring criteria requirements gathered over the dialogue session."""

    job_family: list[str] = Field(default_factory=list, description="Target industry sectors.")
    candidate_level: list[str] = Field(default_factory=list, description="Target candidate seniority levels.")
    assessment_type: list[str] = Field(default_factory=list, description="Target assessment types.")
    skills: list[str] = Field(default_factory=list, description="Target technical or soft skills.")
    competencies: list[str] = Field(default_factory=list, description="Audited behaviors or competencies.")
    languages: list[str] = Field(default_factory=list, description="Required test languages.")
    max_duration_mins: int | None = Field(default=None, description="Maximum test duration limit.")
    constraints: list[str] = Field(default_factory=list, description="Miscellaneous requirements constraints.")
    preferred_assessments: list[str] = Field(default_factory=list, description="Specific preferred assessments.")
    comparison_targets: list[str] = Field(default_factory=list, description="Assessments target comparison list.")


class TurnStatistics(BaseModel):
    """Statistics tracking current dialogue session flow parameters."""

    user_turns: int = Field(default=0, description="Total messages sent by the user.")
    assistant_turns: int = Field(default=0, description="Total messages sent by the assistant.")
    total_turns: int = Field(default=0, description="Sum of all dialogue messages.")
    is_at_limit: bool = Field(default=False, description="True if maximum turn boundary is reached.")


class ConversationState(BaseModel):
    """Immutable snapshot containing the current parsed dialogue parameters."""

    model_config = ConfigDict(frozen=True)

    intent: AgentIntent = Field(..., description="Detected dialogue intent.")
    active_context: ExtractedContext = Field(..., description="Aggregated parsed requirements.")
    turn_count: TurnStatistics = Field(..., description="Dialogue turn details statistics.")
    missing_fields: list[str] = Field(default_factory=list, description="Necessary fields still not resolved.")
    next_action: AgentAction = Field(..., description="Logical next action determined.")
    is_valid: bool = Field(default=True, description="Dialogue flow sequence validation status.")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal dialogue check anomalies warnings.")


class RecommendedAssessment(BaseModel):
    """Cleaned assessment recommendations formatted for LLM context / client display."""

    name: str = Field(..., description="Official assessment name.")
    test_type: str = Field(..., description="Assessment modality type classification.")
    duration_mins: int = Field(..., description="Duration limit in minutes.")
    url: str = Field(..., description="Official whitelisted SHL link URL.")
    skills: list[str] = Field(default_factory=list, description="Target audited skills list.")
    competencies: list[str] = Field(default_factory=list, description="Canonical behavioral competencies.")
    seniority_levels: list[str] = Field(default_factory=list, description="Target seniority levels.")
    reasoning: str = Field(..., description="Reasoning statement justifying the suggestion.")


class ChatResponse(BaseModel):
    """The structured response envelope returned to the client API."""

    reply: str = Field(..., description="The conversational chatbot response text message.")
    recommendations: list[RecommendedAssessment] = Field(
        default_factory=list,
        description="Structured assessment recommendations list.",
    )
    end_of_conversation: bool = Field(
        default=False,
        description="True if the turn finishes the conversation or triggers exits.",
    )


class AgentStatistics(BaseModel):
    """Stats tracking metric events of agent actions and queries."""

    recommendations_generated: int = Field(default=0, description="Total recommendation lists generated.")
    comparisons_generated: int = Field(default=0, description="Total side-by-side comparison tables generated.")
    clarification_requests: int = Field(default=0, description="Total clarifying questions asked.")
    refinement_requests: int = Field(default=0, description="Total context refinement occurrences.")
    refusals: int = Field(default=0, description="Total prompt injection or out-of-scope refusals.")
    average_recommendations: float = Field(default=0.0, description="Average number of recommendations returned.")
    conversation_completion_rate: float = Field(default=0.0, description="Completion rate statistics.")
    validation_failures: int = Field(default=0, description="Total output scheme validation failures.")

