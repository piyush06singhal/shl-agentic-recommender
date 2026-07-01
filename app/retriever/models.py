"""Data models for indexing statistics and validation reports."""

from pydantic import BaseModel, Field


class IndexingResult(BaseModel):
    """Result summary of an indexing execution run."""

    collection_name: str = Field(..., description="Target ChromaDB collection name.")
    total_processed: int = Field(default=0, description="Total assessments processed.")
    added: int = Field(default=0, description="Count of newly indexed records.")
    updated: int = Field(default=0, description="Count of updated assessments.")
    deleted: int = Field(default=0, description="Count of assessments pruned.")
    skipped: int = Field(default=0, description="Count of records matching hashes.")
    failed: int = Field(default=0, description="Count of records failing to index.")
    execution_duration_sec: float = Field(default=0.0, description="Run duration in seconds.")
    errors: list[str] = Field(default_factory=list, description="List of exception messages.")


class VectorStats(BaseModel):
    """Statistics report details for the vector collection."""

    total_vectors: int = Field(..., description="Total vector count in ChromaDB.")
    embedding_model: str = Field(..., description="Name of the embedding model.")
    embedding_dimensions: int = Field(..., description="Dimensions length of embeddings.")
    collection_name: str = Field(..., description="Name of the ChromaDB collection.")
    generation_timestamp: str = Field(..., description="Timestamp of statistics generation.")
    average_document_length: float = Field(0.0, description="Average character length of documents.")
    failed_embeddings: int = Field(0, description="Failed embedding operations.")
    skipped_embeddings: int = Field(0, description="Skipped embedding operations.")
    updated_embeddings: int = Field(0, description="Updated embedding operations.")


class IndexValidationResult(BaseModel):
    """Reports discrepancies between catalog records and the vector index database."""

    is_valid: bool = Field(..., description="Indicator of database alignment health.")
    total_catalog_records: int = Field(..., description="Count of active records in catalog.json.")
    total_vector_records: int = Field(..., description="Count of active records in ChromaDB.")
    missing_ids: list[str] = Field(default_factory=list, description="IDs present in catalog but not in index.")
    orphan_ids: list[str] = Field(default_factory=list, description="IDs present in index but not in catalog.")
    mismatched_hashes: list[str] = Field(default_factory=list, description="IDs with hash differences.")
    validation_errors: list[str] = Field(default_factory=list, description="Audit warning/error descriptions.")


# ---------------------------------------------------------------------------
# Phase 4 — Retrieval Engine Data Models
# ---------------------------------------------------------------------------


class MetadataFilters(BaseModel):
    """Structured filter parameters constraining the retrieval search space."""

    job_family: list[str] = Field(default_factory=list, description="Target job sector filters.")
    test_type: list[str] = Field(default_factory=list, description="Assessment type filters.")
    target_level: list[str] = Field(default_factory=list, description="Candidate seniority level filters.")
    languages: list[str] = Field(default_factory=list, description="Required language filters.")
    max_duration_mins: int | None = Field(default=None, description="Maximum test duration in minutes.")
    skills: list[str] = Field(default_factory=list, description="Required skills filters.")
    competencies: list[str] = Field(default_factory=list, description="Required competency filters.")
    remote_testing: bool | None = Field(default=None, description="Filter by remote testing support.")

    def is_empty(self) -> bool:
        """Returns True if no filter constraints are set."""
        return (
            not self.job_family
            and not self.test_type
            and not self.target_level
            and not self.languages
            and self.max_duration_mins is None
            and not self.skills
            and not self.competencies
            and self.remote_testing is None
        )


class SearchQuery(BaseModel):
    """Fully built and normalized retrieval query."""

    raw_text: str = Field(..., description="Original raw query text.")
    semantic_query: str = Field(..., description="Normalized semantic query for embedding.")
    filters: MetadataFilters = Field(default_factory=MetadataFilters, description="Applied metadata filters.")
    top_k: int = Field(default=10, description="Maximum candidates to retrieve.")
    similarity_threshold: float = Field(default=0.0, description="Minimum similarity cutoff.")


class RetrievedCandidate(BaseModel):
    """A single retrieved and scored assessment candidate."""

    assessment_id: str = Field(..., description="Unique UUID of the assessment.")
    name: str = Field(..., description="Official assessment name.")
    url: str = Field(..., description="Official product URL.")
    test_type: str = Field(..., description="Assessment category classification.")
    description: str = Field(..., description="Cleaned assessment description.")
    job_family: list[str] = Field(default_factory=list, description="Target job sectors.")
    target_level: list[str] = Field(default_factory=list, description="Seniority levels.")
    duration_mins: int = Field(..., description="Test duration in minutes.")
    languages: list[str] = Field(default_factory=list, description="Available languages.")
    skills: list[str] = Field(default_factory=list, description="Skills assessed.")
    competencies: list[str] = Field(default_factory=list, description="Competencies assessed.")
    remote_testing: bool = Field(default=True, description="Supports remote testing.")
    adaptive: bool = Field(default=False, description="Uses adaptive question format.")
    category: str = Field(default="Standard", description="Subcategory classification.")
    # Scoring fields
    semantic_score: float = Field(default=0.0, description="Vector similarity score [0,1].")
    keyword_score: float = Field(default=0.0, description="Keyword relevance score [0,1].")
    metadata_score: float = Field(default=0.0, description="Metadata filter match score [0,1].")
    composite_score: float = Field(default=0.0, description="Aggregate ranking score.")
    rank: int = Field(default=0, description="Final ranked position (1-indexed).")


class RetrievalResult(BaseModel):
    """Final output bundle returned by the RetrievalEngine."""

    query: SearchQuery = Field(..., description="The query that produced these results.")
    candidates: list[RetrievedCandidate] = Field(default_factory=list, description="Ranked retrieved candidates.")
    context_blocks: list[str] = Field(default_factory=list, description="LLM-ready formatted text blocks.")
    context_text: str = Field(default="", description="Joined context string for the LLM.")
    total_candidates: int = Field(default=0, description="Count of candidates before top-K.")
    cache_hit: bool = Field(default=False, description="Whether result was served from cache.")
    latency_ms: float = Field(default=0.0, description="End-to-end retrieval latency in ms.")
    errors: list[str] = Field(default_factory=list, description="Non-fatal error messages.")


class CacheEntry(BaseModel):
    """Cached retrieval result with expiration metadata."""

    result: RetrievalResult = Field(..., description="The cached retrieval result.")
    cached_at: float = Field(..., description="Unix timestamp of cache insertion.")
    ttl_seconds: float = Field(..., description="Cache entry time-to-live.")
    hits: int = Field(default=0, description="Number of cache hits for this entry.")


class RetrievalStatistics(BaseModel):
    """Aggregated retrieval quality and performance statistics."""

    total_queries: int = Field(default=0, description="Total retrieval queries processed.")
    cache_hits: int = Field(default=0, description="Queries served from cache.")
    cache_misses: int = Field(default=0, description="Queries requiring full retrieval.")
    average_latency_ms: float = Field(default=0.0, description="Mean end-to-end latency.")
    average_candidates_returned: float = Field(default=0.0, description="Mean candidates per query.")
    average_semantic_score: float = Field(default=0.0, description="Mean semantic similarity score.")
    top_searched_skills: list[str] = Field(default_factory=list, description="Most frequent skill queries.")
    top_searched_job_families: list[str] = Field(default_factory=list, description="Most frequent job family queries.")
    metadata_filter_usage_rate: float = Field(default=0.0, description="Fraction of queries using filters.")
    generation_timestamp: str = Field(default="", description="Report generation timestamp.")

