"""LLM provider factory matching configured settings to client providers."""

import logging

from app.configs.settings import get_settings
from app.llm.provider import BaseLLMProvider, OpenAIProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory resolving appropriate provider wrappers from settings."""

    @staticmethod
    def get_provider(provider_name: str | None = None) -> BaseLLMProvider:
        """Resolves provider implementation matching name or settings configuration.

        Args:
            provider_name: Optional provider override name string.

        Returns:
            A BaseLLMProvider implementation instance.
        """
        settings = get_settings()
        name = (provider_name or settings.model_name or "openai").lower()

        # Extract provider from model string (e.g. "gpt-4o" matches openai)
        if "gpt" in name or "openai" in name:
            logger.info("LLMProviderFactory: Instantiating OpenAIProvider.")
            return OpenAIProvider()

        # Handle placeholders or other name matches
        if "gemini" in name:
            logger.warning("LLMProviderFactory: Gemini requested — placeholder fallback to OpenAI.")
            return OpenAIProvider()

        if "anthropic" in name or "claude" in name:
            logger.warning("LLMProviderFactory: Anthropic requested — placeholder fallback to OpenAI.")
            return OpenAIProvider()

        # Default fallback
        logger.info("LLMProviderFactory: Defaulting to OpenAIProvider.")
        return OpenAIProvider()
