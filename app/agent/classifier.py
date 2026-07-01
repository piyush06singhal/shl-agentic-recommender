"""Intent classifier resolver resolving conflicting intent signals."""

import logging

from app.agent.intent import IntentDetector
from app.agent.models import AgentIntent
from app.schemas.request import Message

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Resolves conflicting user turn intent signals using deterministic priority rules."""

    def __init__(self, detector: IntentDetector | None = None) -> None:
        self.detector = detector or IntentDetector()

    def resolve_intent(
        self,
        latest_message: Message,
        turn_idx: int,
        unresolved_fields: list[str],
    ) -> AgentIntent:
        """Determines the single resolved AgentIntent, resolving conflicting signals.

        Priority Rules:
        1. Prompt Injection: Always takes absolute precedence.
        2. Out of Scope: Overrides general keyword matches if out-of-scope triggers occur.
        3. First Turn Greeting + Recommendation: If the user says "Hello, I need OPQ",
           we want to recommend. If it contains actual requirements keywords, resolve to
           RECOMMENDATION instead of GREETING.
        4. Refinement vs Recommendation: Refinement overrides Recommendation when
           there is previous context and replacement keywords are used.
        5. Clarification: If the system has outstanding questions and the user gives
           relevant words, resolve to CLARIFICATION.

        Args:
            latest_message: The latest Message turn from the user.
            turn_idx: The current user turn count.
            unresolved_fields: List of active missing fields in context.

        Returns:
            The resolved AgentIntent.
        """
        raw_intent = self.detector.detect_intent(
            latest_message.content,
            turn_idx=turn_idx,
            unresolved_fields=unresolved_fields,
        )

        content_lower = latest_message.content.lower()

        # Rule 1: Prompt Injection is terminal
        if raw_intent == AgentIntent.PROMPT_INJECTION:
            return AgentIntent.PROMPT_INJECTION

        # Rule 2: Out of Scope is absolute
        if raw_intent == AgentIntent.OUT_OF_SCOPE:
            return AgentIntent.OUT_OF_SCOPE

        # Rule 3: Resolve Greeting vs Recommendation/Comparison on early turns.
        # If greeting is detected but they also ask for assessments, prioritize the request.
        if raw_intent == AgentIntent.GREETING:
            hiring_keywords = {"need", "want", "look", "recommend", "suggest", "compare", "opq", "verify"}
            words = set(content_lower.split())
            if words & hiring_keywords:
                # Up-rank to Recommendation or Comparison
                if "compare" in content_lower or "vs" in content_lower:
                    logger.info("Resolving Greeting/Comparison conflict to COMPARISON.")
                    return AgentIntent.COMPARISON
                logger.info("Resolving Greeting/Recommendation conflict to RECOMMENDATION.")
                return AgentIntent.RECOMMENDATION

        # Rule 4: Refinement vs Recommendation
        # If refinement keyword is used but it's the very first turn, it's just Recommendation
        if raw_intent == AgentIntent.REFINEMENT and turn_idx <= 1:
            logger.info("Resolving early turn Refinement to RECOMMENDATION.")
            return AgentIntent.RECOMMENDATION

        # Rule 5: Clarification vs Recommendation
        # If user provides a single word or short phrase like "Technology" or "Graduate" on a turn,
        # and we are expecting clarification, resolve to CLARIFICATION.
        if raw_intent == AgentIntent.RECOMMENDATION and unresolved_fields and len(content_lower.split()) <= 4:
            # Short answer to clarification question
            logger.info("Resolving short Recommendation query to CLARIFICATION.")
            return AgentIntent.CLARIFICATION

        return raw_intent
