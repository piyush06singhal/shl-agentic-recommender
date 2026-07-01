"""Guardrails module protecting against prompt injection, toxic prompts, and system leaks."""

import logging
import re

logger = logging.getLogger(__name__)

# Outbound leak check patterns
_LEAK_PATTERNS = [
    r"system\s*prompt",
    r"developer\s*instructions",
    r"ignore\s*previous",
    r"sk-",  # OpenAI API key pattern
    r"db_path",
    r"chroma",
]


class AgentGuardrails:
    """Inbound and outbound security filter enforcing system guardrails."""

    def __init__(self) -> None:
        self.leak_regexes = [re.compile(p, re.IGNORECASE) for p in _LEAK_PATTERNS]

    def check_inbound_safety(self, text: str) -> bool:
        """Audits incoming user message text for toxicity, prompt injection, or unsafe statements.

        Args:
            text: Raw user message.

        Returns:
            True if user message is safe, False if it violates guardrails.
        """
        # Basic toxicity check (rudimentary keyword matching for safety demo)
        toxic_words = {"fuck", "shit", "bitch", "asshole", "kill", "die", "hack", "bypass"}
        tokens = set(re.findall(r"\b\w+\b", text.lower()))
        if tokens & toxic_words:
            logger.warning("Guardrails: Toxic keywords detected in user input.")
            return False

        # Check injection
        # Note: classifier/rules already detect PROMPT_INJECTION, but we run a secondary safeguard
        if "ignore rules" in text.lower() or "reveal system prompt" in text.lower():
            logger.warning("Guardrails: Injection signature detected.")
            return False

        return True

    def check_outbound_safety(self, reply: str) -> str:
        """Scans outgoing assistant reply to ensure no prompt leaks or API keys exist.

        If a leak is found, replaces it with a generic safe refusal message.

        Args:
            reply: The outgoing response text.

        Returns:
            Sanitized response string or safe default.
        """
        for regex in self.leak_regexes:
            if regex.search(reply):
                logger.error("Guardrails: Outbound prompt leak or API key pattern matched: %s", regex.pattern)
                return self.get_safe_refusal_message()

        return reply

    def get_safe_refusal_message(self) -> str:
        """Returns standard safe refusal message for out-of-scope or blocked requests.

        Returns:
            Standard safe refusal text response.
        """
        return (
            "I apologize, but I can only assist with discovering, recommending, or comparing "
            "official SHL assessment products for recruitment. Let me know if you would like "
            "help finding a test for your candidate seniority levels."
        )
