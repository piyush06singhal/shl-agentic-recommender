"""Structured output parser deserializing raw LLM responses to JSON."""

import json
import logging
import re

from app.llm.models import LLMOutput

logger = logging.getLogger(__name__)


class StructuredOutputParser:
    """Cleans, parses, and validates JSON blocks from raw text replies."""

    def parse_completions(self, text: str) -> LLMOutput:
        """Parses JSON content out of markdown code blocks or text streams.

        Args:
            text: Raw completions string.

        Returns:
            A populated LLMOutput model.

        Raises:
            ValueError: If JSON is invalid or missing required properties.
        """
        cleaned = text.strip()

        # Remove markdown wrappers ```json ... ```
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
            if match:
                cleaned = match.group(1).strip()
            else:
                # Strip raw backticks
                cleaned = cleaned.replace("```", "").strip()

        # Parse JSON
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("StructuredOutputParser: Failed to decode JSON: %s\nRaw content: %s", e, text)
            raise ValueError(f"Completions returned malformed JSON: {e}") from e

        # Ensure required keys exist
        if "reply" not in payload:
            raise ValueError("Completions JSON is missing the required 'reply' property.")

        # Ensure recommendations exist and are list
        recommendations = payload.get("recommendations", [])
        if not isinstance(recommendations, list):
            payload["recommendations"] = []

        # Convert to LLMOutput model
        return LLMOutput.model_validate(payload)
