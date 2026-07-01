"""Deterministic rules and regexes for intent mapping and prompt injection detection."""

import logging
import re

from app.agent.models import AgentIntent

logger = logging.getLogger(__name__)

# Prompt injection signature patterns
_INJECTION_PATTERNS = [
    r"ignore\s+(?:the\s+)?(?:above|previous|directives|instructions|rules)",
    r"reveal\s+(?:the\s+)?(?:system\s+)?prompt",
    r"act\s+as\s+a\s+",
    r"system\s+prompt",
    r"developer\s+instructions",
    r"forget\s+(?:the\s+)?(?:previous|directives|instructions|rules)",
    r"\bdan\b",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"override\s+rules",
]

# Greeting regexes/keywords
_GREETING_PATTERNS = [
    r"\bhello\b",
    r"\bhi\b",
    r"\bhey\b",
    r"\bgreetings\b",
    r"\bhowdy\b",
]

# Help patterns
_HELP_PATTERNS = [
    r"\bhelp\b",
    r"\boptions\b",
    r"\bwhat\s+can\s+you\s+do\b",
    r"\bhow\s+to\s+use\b",
    r"\binstructions\b",
]

# Conversation End patterns
_END_PATTERNS = [
    r"\bquit\b",
    r"\bexit\b",
    r"\bbye\b",
    r"\bthank\s+you\b",
    r"\bthanks\b",
    r"\bfinished\b",
]

# Comparison patterns
_COMPARISON_PATTERNS = [
    r"\bcompare\b",
    r"\bvs\b",
    r"\bversus\b",
    r"\bdifference\b",
    r"\bdifferences\b",
    r"\bcontrast\b",
]

# Refinement patterns
_REFINEMENT_PATTERNS = [
    r"\bactually\b",
    r"\binstead\b",
    r"\bchange\b",
    r"\bno\b",
    r"\bprefer\b",
    r"\bupdate\b",
    r"\bmodify\b",
]


class RuleEngine:
    """Evaluates deterministic rules and regular expressions to classify intents."""

    def __init__(self) -> None:
        self.injection_regexes = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]
        self.greeting_regexes = [re.compile(p, re.IGNORECASE) for p in _GREETING_PATTERNS]
        self.help_regexes = [re.compile(p, re.IGNORECASE) for p in _HELP_PATTERNS]
        self.end_regexes = [re.compile(p, re.IGNORECASE) for p in _END_PATTERNS]
        self.comparison_regexes = [re.compile(p, re.IGNORECASE) for p in _COMPARISON_PATTERNS]
        self.refinement_regexes = [re.compile(p, re.IGNORECASE) for p in _REFINEMENT_PATTERNS]

    def detect_prompt_injection(self, text: str) -> bool:
        """Inspects text for prompt injection keywords or jailbreak attempt patterns.

        Args:
            text: Raw message content.

        Returns:
            True if prompt injection signatures are detected.
        """
        for regex in self.injection_regexes:
            if regex.search(text):
                logger.warning("Prompt Injection detected by rule pattern: %s", regex.pattern)
                return True
        return False

    def classify_intent_by_rules(self, text: str) -> AgentIntent | None:
        """Applies deterministic regex rules to identify user intent.

        Args:
            text: Lowercase or raw user message text.

        Returns:
            Matched AgentIntent enum or None.
        """
        if self.detect_prompt_injection(text):
            return AgentIntent.PROMPT_INJECTION

        # 1. Comparison
        for regex in self.comparison_regexes:
            if regex.search(text):
                return AgentIntent.COMPARISON

        # 2. Refinement
        for regex in self.refinement_regexes:
            if regex.search(text):
                return AgentIntent.REFINEMENT

        # 3. Help
        for regex in self.help_regexes:
            if regex.search(text):
                return AgentIntent.HELP

        # 4. Conversation End
        for regex in self.end_regexes:
            if regex.search(text):
                return AgentIntent.CONVERSATION_END

        # 5. Greeting
        for regex in self.greeting_regexes:
            if regex.search(text):
                return AgentIntent.GREETING

        return None
