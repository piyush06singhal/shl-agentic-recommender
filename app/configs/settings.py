"""Application settings configuration module using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application configuration settings loader.

    Reads variables from environment variables or a local `.env` file,
    running type validation and checking boundaries.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI API configuration settings
    openai_api_key: str | None = Field(
        default=None,
        alias="OPENAI_API_KEY",
        description="Optional API access key for OpenAI services.",
    )

    # Large Language Model configurations
    model_name: str = Field(
        default="gpt-4o",
        alias="MODEL_NAME",
        description="The target Large Language Model name identifier.",
    )

    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="EMBEDDING_MODEL",
        description="The target Dense Vector Embedding generation model name.",
    )

    # Search and retrieval boundaries
    top_k: int = Field(
        default=15,
        alias="TOP_K",
        description="The maximum number of matches returned from catalog searches.",
    )

    similarity_threshold: float = Field(
        default=0.70,
        alias="SIMILARITY_THRESHOLD",
        description="The similarity cutoff score for vector similarity matches.",
    )

    # Latency limits and logging thresholds
    api_timeout: float = Field(
        default=25.0,
        alias="API_TIMEOUT",
        description="The maximum execution timeout in seconds for external API calls.",
    )

    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="The logging reporting limit threshold (DEBUG, INFO, WARNING, etc.).",
    )

    # Folder paths mapping parameters
    catalog_path: str = Field(
        default="app/catalog/data/catalog.json",
        alias="CATALOG_PATH",
        description="The path to the local offline JSON catalog database.",
    )

    vector_db_path: str = Field(
        default="app/catalog/data/vector_db",
        alias="VECTOR_DB_PATH",
        description="The path to the local vector index database folder.",
    )

    vector_collection_name: str = Field(
        default="shl_assessments",
        alias="VECTOR_COLLECTION_NAME",
        description="The collection name identifier within the vector database.",
    )

    cache_max_size: int = Field(
        default=200,
        alias="CACHE_MAX_SIZE",
        description="Maximum number of entries stored in the retrieval LRU cache.",
    )

    cache_ttl_seconds: float = Field(
        default=3600.0,
        alias="CACHE_TTL_SECONDS",
        description="Time-to-live in seconds for each cache entry.",
    )

    retrieval_stats_path: str = Field(
        default="app/catalog/data/retrieval_statistics.json",
        alias="RETRIEVAL_STATS_PATH",
        description="Path to the generated retrieval statistics JSON report file.",
    )

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        """Verifies top_k is within realistic bounds."""
        if v < 1 or v > 100:
            raise ValueError("TOP_K must be an integer between 1 and 100.")
        return v

    @field_validator("similarity_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """Verifies similarity cutoff values fall between 0 and 1."""
        if v < 0.0 or v > 1.0:
            raise ValueError("SIMILARITY_THRESHOLD must be a float between 0.0 and 1.0.")
        return v

    @field_validator("api_timeout")
    @classmethod
    def validate_timeout(cls, v: float) -> float:
        """Verifies timeout values are positive and within gateway SLA limits."""
        if v <= 0.0 or v > 28.0:
            raise ValueError("API_TIMEOUT must be a positive float under 28.0 seconds.")
        return v


@lru_cache
def get_settings() -> Settings:
    """Retrieves the cached global singleton configuration settings instance."""
    return Settings()
