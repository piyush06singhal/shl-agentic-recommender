"""Data models defining the catalog database schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class ScrapedAssessment(BaseModel):
    """Represents a raw scraped assessment profile parsed from detail web pages."""

    name: str = Field(..., description="Raw official name of assessment.")
    url: str = Field(..., description="Raw page URL source.")
    description: str = Field("", description="Raw product description details.")
    test_type: str | None = Field(default=None, description="Raw categorizations of tests.")
    job_family: str | None = Field(default=None, description="Raw targeted industries sector description.")
    target_level: str | None = Field(default=None, description="Raw targeted candidate experience groups.")
    duration: str | None = Field(default=None, description="Raw test time limits duration description.")
    languages: str | None = Field(default=None, description="Raw list or comma-separated translations available.")
    skills: str | None = Field(default=None, description="Raw competencies or specific skills audited.")
    competencies: str | None = Field(default=None, description="Raw competency domains.")
    remote_testing: str | None = Field(default=None, description="Raw text describing remote configurations support.")
    adaptive: str | None = Field(default=None, description="Raw indicators of adaptive testing systems.")
    category: str | None = Field(default=None, description="Raw class category classification.")


class CatalogAssessment(BaseModel):
    """Conforms cleaned, validated, and normalized records to the RAG database schema."""

    id: UUID = Field(..., description="System unique primary key ID.")
    name: str = Field(..., description="Normalized official product name.")
    url: str = Field(..., description="Validated product link page.")
    test_type: str = Field(..., description="Normalized category classification.")
    description: str = Field(..., description="Normalized clean description text.")
    job_family: list[str] = Field(default_factory=list, description="List of targeted job sectors.")
    target_level: list[str] = Field(default_factory=list, description="Target levels of seniority.")
    duration_mins: int = Field(..., description="Parsed integer duration in minutes.")
    languages: list[str] = Field(default_factory=list, description="Standardized lists of languages.")
    skills: list[str] = Field(default_factory=list, description="Standardized audited capabilities.")
    competencies: list[str] = Field(default_factory=list, description="Audited competency mappings.")
    remote_testing: bool = Field(default=True, description="Indicates if remote administration is supported.")
    adaptive: bool = Field(default=False, description="Indicates adaptive question formats.")
    category: str = Field(default="Standard", description="Subcategory categorization profile.")
