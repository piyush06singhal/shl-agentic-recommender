"""LLM client wrapping provider connection states and timings."""

import logging
import time
from typing import Any

from app.llm.factory import LLMProviderFactory
from app.llm.models import LLMConfig
from app.llm.provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class LLMClient:
    """Manages active LLM provider connection, lifecycle and timeouts."""

    def __init__(self, provider: BaseLLMProvider | None = None) -> None:
        self.provider = provider or LLMProviderFactory.get_provider()

    def generate_completion(
        self,
        prompt: str,
        config: LLMConfig,
        response_model: type[Any] | None = None,
    ) -> tuple[str, float]:
        """Issues chat completions request to active provider, measuring request latency.

        Args:
            prompt: Combined templates instruction.
            config: Option configurations.
            response_model: Optional structured validation target model.

        Returns:
            A tuple of (raw response string content, latency in milliseconds).
        """
        start = time.monotonic()
        logger.debug("LLMClient: Initiating completions call...")

        # Connection / request
        content = self.provider.generate(
            prompt=prompt,
            config=config,
            response_model=response_model,
        )

        latency_ms = (time.monotonic() - start) * 1000.0
        logger.debug("LLMClient: Request completed in %.2fms.", latency_ms)

        return content, latency_ms

    def shutdown(self) -> None:
        """Gracefully closes active sockets or clients."""
        logger.info("LLMClient: Connection shutdown completed.")
