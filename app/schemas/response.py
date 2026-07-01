"""Pydantic schemas validating outgoing system chat API response payloads."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.configs.constants import DEFAULT_MAX_RECOMMENDATIONS


class Recommendation(BaseModel):
    """Represents a single matching recommended assessment payload object."""

    name: str = Field(
        ...,
        description="The official name of the SHL assessment.",
    )
    url: str = Field(
        ...,
        description="The whitelisted product URL path page.",
    )
    test_type: str = Field(
        ...,
        description="The psychometric category classification modality.",
    )


class ChatResponse(BaseModel):
    """The outgoing chat processing response API payload schema."""

    reply: str = Field(
        ...,
        description="The natural language answer text synthesized by the agent.",
    )
    recommendations: list[Recommendation] = Field(
        default_factory=list,
        description="Array containing 1 to 10 matching assessment configurations.",
    )
    end_of_conversation: bool = Field(
        ...,
        description="Boolean status indicating conversation turn limits are reached.",
    )

    @field_validator("recommendations")
    @classmethod
    def validate_recommendations_count(cls, v: list[Recommendation]) -> list[Recommendation]:
        """Validates that the recommendation list complies with target size limits."""
        if len(v) > DEFAULT_MAX_RECOMMENDATIONS:
            raise ValueError(f"recommendations count must be <= {DEFAULT_MAX_RECOMMENDATIONS}")
        return v


class Assessment(BaseModel):
    """In-memory metadata model representing a single SHL catalog database entry."""

    id: UUID = Field(
        ...,
        description="The unique system record identifier.",
    )
    name: str = Field(
        ...,
        description="Official assessment name.",
    )
    url: str = Field(
        ...,
        description="Whitelisted product landing page URL.",
    )
    test_type: str = Field(
        ...,
        description="Psychometric modality category.",
    )
    description: str = Field(
        ...,
        description="Assessment profile detailing measured competencies.",
    )
    job_family: list[str] = Field(
        ...,
        description="Target job categories/families.",
    )
    target_level: list[str] = Field(
        ...,
        description="Target experience seniority tiers.",
    )
    duration_mins: int = Field(
        ...,
        description="Average test completion duration in minutes.",
    )
    languages: list[str] = Field(
        ...,
        description="List of supported translation languages.",
    )


class ComparisonResult(BaseModel):
    """Structured data comparison of assessments containing catalog characteristics."""

    assessment_a: Assessment = Field(
        ...,
        description="Database entry profile for assessment target A.",
    )
    assessment_b: Assessment = Field(
        ...,
        description="Database entry profile for assessment target B.",
    )
    comparison_matrix: str = Field(
        ...,
        description="The compiled markdown table comparing attributes.",
    )
