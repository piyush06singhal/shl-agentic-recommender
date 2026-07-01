"""Data schemas and request/response models for the LLM integration layer."""

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configuration parameters for single LLM provider requests."""

    model: str = Field(..., description="Target model identifier.")
    temperature: float = Field(default=0.0, description="Sampling temperature settings.")
    max_tokens: int = Field(default=1000, description="Maximum tokens boundary.")
    top_p: float = Field(default=1.0, description="Nucleus sampling threshold.")
    frequency_penalty: float = Field(default=0.0, description="Repetition reduction factor.")
    presence_penalty: float = Field(default=0.0, description="Topic diversification factor.")
    timeout: float = Field(default=30.0, description="Timeout limit in seconds.")
    retries: int = Field(default=3, description="Maximum auto retry counts.")


class LLMRecommendation(BaseModel):
    """Assessment recommendations schema generated directly by the LLM."""

    name: str = Field(..., description="Assessment name.")
    url: str = Field(..., description="Product catalog link URL.")
    test_type: str = Field(..., description="Assessment type classification.")


class LLMOutput(BaseModel):
    """Parsed structured response envelope returned by LLM semantic reasoning."""

    reply: str = Field(..., description="The conversational text message response.")
    recommendations: list[LLMRecommendation] = Field(
        default_factory=list,
        description="List of suggested assessment products.",
    )
    end_of_conversation: bool = Field(
        default=False,
        description="True if dialogue termination is reached.",
    )
