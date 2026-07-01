"""Embedding provider wrappers defining configurable vector generation implementations."""

import logging
from abc import ABC, abstractmethod

import numpy as np

from app.configs.settings import get_settings
from app.services.utils import retry

# Conditional import for OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(ABC):
    """Abstract base class defining interface contracts for all embedding providers."""

    @abstractmethod
    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generates dense vector representation embeddings for a list of documents.

        Args:
            texts: List of document string chunks.

        Returns:
            A list of float vector lists matching the text sequences.
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Returns the dimensionality length of generated vector lists."""
        pass


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Generates text embeddings using OpenAI's API client SDK."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI SDK is not installed or available in this runtime environment.")

        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.embedding_model

        if not self.api_key:
            logger.warning("Initializing OpenAI client with missing API Key. Ensure OPENAI_API_KEY env is set.")

        # Initialize client SDK
        self.client = OpenAI(api_key=self.api_key)

    @retry(retries=3, delay=1.0)
    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Invokes OpenAI embeddings endpoints, applying exponential connection backoffs.

        Args:
            texts: Text list blocks.

        Returns:
            A list of float vectors.
        """
        if not texts:
            return []

        logger.info("Requesting OpenAI embeddings for batch of %d items...", len(texts))
        response = self.client.embeddings.create(
            input=texts,
            model=self.model,
        )

        # Extract float coordinates arrays
        return [data.embedding for data in response.data]

    def get_dimension(self) -> int:
        """Returns default dimensions associated with OpenAI target models."""
        if "small" in self.model:
            return 1536
        if "large" in self.model:
            return 3072
        # Fallback default
        return 1536


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Standardized mock provider generating deterministic mock coordinates vectors for local offline runs."""

    def __init__(self, dimension: int = 1536) -> None:
        self.dimension = dimension

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generates deterministic mock float coordinate arrays using string hashes.

        Args:
            texts: Document list string blocks.

        Returns:
            A list of normalized float coordinate vectors.
        """
        vectors: list[list[float]] = []
        for text in texts:
            # Deterministic generation using a pseudorandom seed derived from text length/hash
            seed = sum(ord(c) for c in text) % 1000
            rng = np.random.default_rng(seed)
            # Generate random normalized vector
            vec = rng.standard_normal(self.dimension)
            norm = np.linalg.norm(vec)
            normalized_vec = (vec / norm if norm > 0 else vec).tolist()
            # Explicitly type cast float values
            vectors.append([float(val) for val in normalized_vec])

        return vectors

    def get_dimension(self) -> int:
        return self.dimension


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Factory helper loading embedding providers configured in settings parameters."""
    settings = get_settings()

    if get_settings().model_name.lower() == "mock":
        logger.info("Using MockEmbeddingProvider (mode config matches 'mock').")
        return MockEmbeddingProvider()

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY env parameter is empty. Swapping to MockEmbeddingProvider.")
        return MockEmbeddingProvider()

    logger.info("Using OpenAIEmbeddingProvider (Model: %s).", settings.embedding_model)
    return OpenAIEmbeddingProvider()
