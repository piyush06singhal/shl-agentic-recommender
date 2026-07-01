"""Intent detector orchestrating rule engine, keywords, and LLM placeholders."""

import logging
import re

from app.agent.models import AgentIntent
from app.agent.rules import RuleEngine

logger = logging.getLogger(__name__)

# Out-of-Scope keyword sets (e.g., weather, cooking, personal queries, general code writing, math)
_OUT_OF_SCOPE_KEYWORDS = {
    "weather", "recipe", "cook", "food", "movie", "song", "music", "joke",
    "sports", "football", "cricket", "basketball", "math", "calculator",
    "write a python function to", "generate code", "tell me a story",
    "how to fix my car", "definition of", "stock price", "travel guide",
}

# Domain keyword list to qualify if a request is within scope
_IN_SCOPE_KEYWORDS = {
    "shl", "assessment", "test", "assess", "evaluate", "hire", "hiring", "recruit",
    "recruitment", "candidate", "job", "role", "opq", "opq32", "verify", "cognitive",
    "aptitude", "personality", "skill", "skills", "competency", "competencies", "level",
    "duration", "language", "languages", "java", "python", "excel", "leadership", "sales",
    "finance", "management", "verbal", "numerical", "inductive", "deductive", "critical",
}

# Recommendation indicators (explicit intent to find, recommend, get, suggest tests)
_RECOMMENDATION_KEYWORDS = {
    "recommend", "suggest", "find", "get", "show", "search", "need", "want", "look for",
    "give me", "list", "suitable", "appropriate",
}

# Clarification indicators (providing answers to previous questions, like "entry", "senior", "30 mins", "english")
# We'll also cross-reference context fields
_CLARIFICATION_KEYWORDS = {
    "yes", "no", "english", "french", "german", "graduate", "junior", "senior", "entry",
    "minutes", "mins", "hours", "hrs", "manager", "professional",
}


class IntentDetector:
    """Detects user turn intents using rules, regex, keywords, and fallback mechanisms."""

    def __init__(self, rule_engine: RuleEngine | None = None) -> None:
        self.rule_engine = rule_engine or RuleEngine()

    def detect_intent(
        self,
        user_message: str,
        turn_idx: int = 0,
        unresolved_fields: list[str] | None = None,
    ) -> AgentIntent:
        """Determines the user intent for the current turn.

        Detection order:
        1. Rule Engine (Prompt Injection, Comparison, Refinement, Help, End, Greeting)
        2. Out-of-Scope detection
        3. Recommendation vs Clarification keyword heuristics
        4. LLM fallback (placeholder interface)

        Args:
            user_message: Sanitized user input string.
            turn_idx: Total user turns count context.
            unresolved_fields: Missing context fields list.

        Returns:
            The classified AgentIntent.
        """
        cleaned_text = user_message.lower().strip()

        # Step 1: Rule Engine (Regex & exact keyword matches)
        rule_intent = self.rule_engine.classify_intent_by_rules(cleaned_text)
        if rule_intent is not None:
            logger.info("Intent classified by RuleEngine: %s", rule_intent)
            return rule_intent

        # Step 2: Out of Scope detection
        if self._is_out_of_scope(cleaned_text):
            logger.info("Intent classified as OUT_OF_SCOPE.")
            return AgentIntent.OUT_OF_SCOPE

        # Step 3: Heuristic Keyword classification (Recommendation vs Clarification)
        # If there are unresolved fields and the user is providing info, it's a Clarification.
        tokens = set(re.findall(r"\b\w+\b", cleaned_text))

        # Check if the user is answering a question (Clarification)
        if unresolved_fields and (tokens & _CLARIFICATION_KEYWORDS):
            logger.info("Intent classified as CLARIFICATION based on active missing fields.")
            return AgentIntent.CLARIFICATION

        # Check for explicit recommendation request
        if tokens & _RECOMMENDATION_KEYWORDS:
            logger.info("Intent classified as RECOMMENDATION from keywords.")
            return AgentIntent.RECOMMENDATION

        # Step 4: LLM fallback placeholder
        fallback_intent = self._llm_intent_classifier_fallback(cleaned_text)
        logger.info("Intent resolved by fallback placeholder: %s", fallback_intent)
        return fallback_intent

    def _is_out_of_scope(self, text: str) -> bool:
        """Heuristics to determine if query is out of the SHL recruitment assessment domain.

        Args:
            text: Lowercase user input.

        Returns:
            True if query is out-of-scope.
        """
        tokens = set(re.findall(r"\b\w+\b", text))

        # Check explicit out-of-scope indicators
        if tokens & _OUT_OF_SCOPE_KEYWORDS:
            return True

        # If it contains absolutely no domain keywords and is not a simple greeting/end
        if len(text) > 10 and not (tokens & _IN_SCOPE_KEYWORDS):
            return True

        return False

    def _llm_intent_classifier_fallback(self, text: str) -> AgentIntent:
        """Placeholder interface representing future LLM semantic intent classification.

        In the offline codebase, this falls back to RECOMMENDATION if some hiring keywords
        are present, else UNKNOWN.

        Args:
            text: Cleaned text.

        Returns:
            Fallback AgentIntent.
        """
        tokens = set(re.findall(r"\b\w+\b", text))
        if tokens & _IN_SCOPE_KEYWORDS:
            return AgentIntent.RECOMMENDATION
        return AgentIntent.UNKNOWN
