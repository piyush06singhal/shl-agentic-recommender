"""Pydantic schemas validating client incoming chat requests."""


from pydantic import BaseModel, Field, model_validator

from app.configs.constants import MAX_MESSAGE_CHARACTER_LENGTH


class Message(BaseModel):
    """Represents a single message turn in the conversation history."""

    role: str = Field(
        ...,
        description="The sender role identifier. Allowed values: 'user', 'assistant'.",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_CHARACTER_LENGTH,
        description="The content of the message.",
    )

    @model_validator(mode="after")
    def validate_role(self) -> "Message":
        """Validates that the role matches permitted values."""
        allowed_roles = {"user", "assistant"}
        if self.role not in allowed_roles:
            raise ValueError(f"role must be one of {allowed_roles}")
        return self


class ChatRequest(BaseModel):
    """The incoming POST /chat request payload format schema validator."""

    messages: list[Message] = Field(
        ...,
        min_length=1,
        description="Chronological history list of dialogue messages.",
    )


class MetadataFilters(BaseModel):
    """The reconstructed active search criteria parsed from conversation history."""

    job_family: str | None = Field(
        default=None,
        description="The target job family/sector category filter.",
    )
    candidate_level: str | None = Field(
        default=None,
        description="The target experience level seniority tier filter.",
    )
    test_type: str | None = Field(
        default=None,
        description="The assessment type modality filter.",
    )
    duration_max_mins: int | None = Field(
        default=None,
        description="The maximum allowed test duration in minutes.",
    )
    languages: list[str] = Field(
        default_factory=list,
        description="Required languages target whitelist.",
    )
    target_skills: list[str] = Field(
        default_factory=list,
        description="Required competencies or skills whitelist.",
    )
