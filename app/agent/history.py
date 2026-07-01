"""History analyzer module investigating conversation transcripts and turn attributes."""

import logging

from app.agent.models import ExtractedContext
from app.schemas.request import Message

logger = logging.getLogger(__name__)

# Canonical assessments lists to search in assistant responses
_CANONICAL_ASSESSMENTS = [
    "SHL OPQ32 Personality Assessment",
    "SHL Cognitive Ability Test (Verify)",
    "SHL Java Developer Skills Test",
    "SHL English Language Communication Test",
    "SHL Graduate General Ability Test",
    "Verify G+",
    "OPQ32",
    "OPQ",
]


class HistoryAnalyzer:
    """Provides analytical tools scanning conversation histories for changes and anomalies."""

    def find_latest_user_request(self, messages: list[Message]) -> str:
        """Retrieves the content of the last message sent by the user.

        Args:
            messages: Dialogue history messages.

        Returns:
            The raw text string of the latest user query, or empty string.
        """
        for msg in reversed(messages):
            if msg.role == "user":
                return msg.content
        return ""

    def find_previous_recommendations(self, messages: list[Message]) -> list[str]:
        """Scans assistant turns in history to find previously suggested assessment names.

        Args:
            messages: Dialogue history messages.

        Returns:
            A list of canonical assessment names previously mentioned.
        """
        recommendations: list[str] = []
        for msg in messages:
            if msg.role != "assistant":
                continue
            content = msg.content.lower()
            for assessment in _CANONICAL_ASSESSMENTS:
                if assessment.lower() in content:
                    recommendations.append(assessment)
        return list(set(recommendations))

    def detect_refinements(self, messages: list[Message], latest_intent: str) -> bool:
        """Determines if the current turn updates/refines previous specifications.

        Args:
            messages: Dialogue history messages.
            latest_intent: Reconstructed active intent.

        Returns:
            True if user is modifying requirements.
        """
        return latest_intent == "Refinement"

    def detect_contradictions(self, context: ExtractedContext, messages: list[Message]) -> list[str]:
        """Detects contradictions between current context and past turns.

        Example: User previously requested a Senior/Leadership test, but now requests
        an Entry level assessment.

        Args:
            context: The currently reconstructed context.
            messages: Dialogue history messages.

        Returns:
            A list of contradiction warning strings.
        """
        contradictions: list[str] = []
        if len(messages) < 3:
            return contradictions

        # Check seniority level contradictions
        # Scan earlier user turns for seniority levels
        past_levels: set[str] = set()
        user_turns = [m for m in messages if m.role == "user"]
        # Skip the latest user message
        for msg in user_turns[:-1]:
            content = msg.content.lower()
            if "graduate" in content or "entry" in content or "junior" in content:
                past_levels.add("Graduate/Entry")
            if "leadership" in content or "manager" in content or "senior" in content:
                past_levels.add("Leadership")

        # Compare with currently resolved level
        current_levels = set(context.candidate_level)
        if current_levels and past_levels:
            # If current levels do not overlap with past levels, but user didn't say "Actually" or "instead"
            # we check if it is a flat contradiction
            latest_content = user_turns[-1].content.lower() if user_turns else ""
            is_refinement = any(w in latest_content for w in ["actually", "instead", "change"])
            if not is_refinement and not (current_levels & past_levels):
                contradictions.append(
                    f"Seniority contradiction: User previously indicated {list(past_levels)} "
                    f"but is now asking for {list(current_levels)} without explicit correction."
                )

        return contradictions

    def detect_repeated_questions(self, messages: list[Message]) -> bool:
        """Determines if the user has repeated the same question/text on consecutive turns.

        Args:
            messages: Dialogue history messages.

        Returns:
            True if repetition is found.
        """
        user_messages = [m.content.strip().lower() for m in messages if m.role == "user"]
        if len(user_messages) < 2:
            return False
        return user_messages[-1] == user_messages[-2]

    def generate_conversation_summary(self, messages: list[Message]) -> str:
        """Assembles a high-level summary of the conversation dialogue flow.

        Args:
            messages: Dialogue history messages.

        Returns:
            A short text summary of the conversation.
        """
        user_msg_count = sum(1 for m in messages if m.role == "user")
        assistant_msg_count = sum(1 for m in messages if m.role == "assistant")
        return (
            f"Conversation Dialogue Summary: {user_msg_count} user turns, "
            f"{assistant_msg_count} assistant turns. "
            f"Last statement: '{self.find_latest_user_request(messages)[:50]}...'"
        )
