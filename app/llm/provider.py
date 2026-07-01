"""Provider abstractions and concrete LLM client integrations (OpenAI)."""

import abc
import logging
from typing import Any

from app.configs.settings import get_settings
from app.llm.models import LLMConfig

logger = logging.getLogger(__name__)


class BaseLLMProvider(abc.ABC):
    """Abstract Base Class defining provider independent interface."""

    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        config: LLMConfig,
        response_model: type[Any] | None = None,
    ) -> str:
        """Sends a request to the LLM backend provider and returns the raw string response.

        Args:
            prompt: Formatted system and user prompt.
            config: LLMConfig options.
            response_model: Optional Pydantic model for structured outputs.

        Returns:
            The raw text string response.
        """
        pass


class OpenAIProvider(BaseLLMProvider):
    """Concrete provider wrapping OpenAI's chat completions API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.settings = get_settings()
        self.api_key = api_key or self.settings.openai_api_key
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            if not self.api_key:
                logger.warning("OpenAIProvider: API key missing, requests will fail unless mocked.")
            from openai import OpenAI
            # Ensure custom client settings, e.g. base_url if applicable, or default
            self._client = OpenAI(api_key=self.api_key or "mock-key", timeout=30.0)
        return self._client

    def generate(
        self,
        prompt: str,
        config: LLMConfig,
        response_model: type[Any] | None = None,
    ) -> str:
        client = self._get_client()

        logger.info(
            "OpenAIProvider: Generating completion using model=%s | temp=%.1f",
            config.model,
            config.temperature,
        )

        messages = [
            {"role": "user", "content": prompt},
        ]

        kwargs: dict[str, Any] = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
        }

        # Handle structured outputs with Pydantic model formatting if supported
        if response_model is not None:
            try:
                # Use beta completions helper if using structured output format
                completion = client.beta.chat.completions.parse(
                    response_format=response_model,
                    **kwargs
                )
                raw_res = completion.choices[0].message.content
                if raw_res is None:
                    raise ValueError("Received empty content from completions.")
                return str(raw_res)
            except Exception as e:
                logger.warning("OpenAIProvider: structured completions format call failed: %s. Falling back.", e)
                # Fallback to standard chat completions
                pass

        # Standard non-structured completion fallback
        completion = client.chat.completions.create(**kwargs)
        result = completion.choices[0].message.content
        if result is None:
            raise ValueError("Completions returned empty content.")
        return str(result)
