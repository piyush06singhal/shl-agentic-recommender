"""Statistics collector tracking dialogue session characteristics and metrics."""

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class ConversationStatisticsCollector:
    """Accumulates conversational metrics and saves reports to conversation_statistics.json."""

    def __init__(self) -> None:
        self._total_conversations: int = 0
        self._total_turns: list[int] = []
        self._intents_count: dict[str, int] = {}
        self._clarification_count: int = 0
        self._refinement_count: int = 0
        self._comparison_count: int = 0
        self._completed_conversations: int = 0

    def record_session(
        self,
        total_turns: int,
        intents: list[str],
        ended_gracefully: bool = False,
    ) -> None:
        """Records metrics for a completed conversation session.

        Args:
            total_turns: Total turns in the conversation.
            intents: List of all intents detected during the conversation.
            ended_gracefully: True if the conversation reached END_CONVERSATION.
        """
        self._total_conversations += 1
        self._total_turns.append(total_turns)

        for intent in intents:
            self._intents_count[intent] = self._intents_count.get(intent, 0) + 1
            if intent == "Clarification":
                self._clarification_count += 1
            elif intent == "Refinement":
                self._refinement_count += 1
            elif intent == "Comparison":
                self._comparison_count += 1

        if ended_gracefully:
            self._completed_conversations += 1

    def compile(self) -> dict[str, Any]:
        """Compiles accumulated statistics into a dictionary report.

        Returns:
            A dictionary of compiled conversation statistics.
        """
        total_convs = self._total_conversations or 1
        avg_turns = sum(self._total_turns) / len(self._total_turns) if self._total_turns else 0.0
        completion_rate = self._completed_conversations / total_convs

        return {
            "total_conversations": self._total_conversations,
            "average_turns": round(avg_turns, 2),
            "intent_distribution": self._intents_count,
            "clarification_frequency": self._clarification_count,
            "refinement_frequency": self._refinement_count,
            "comparison_frequency": self._comparison_count,
            "conversation_completion_rate": round(completion_rate, 4),
            "generation_timestamp": datetime.now(UTC).isoformat(),
        }

    def save(self, path: str) -> None:
        """Saves the compiled statistics report to a JSON file.

        Args:
            path: Absolute or relative file path to write.
        """
        stats = self.compile()
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logger.info("ConversationStatistics: Report saved to %s.", path)


# ---------------------------------------------------------------------------
# Phase 6 — Agent Statistics Collector
# ---------------------------------------------------------------------------


class AgentStatisticsCollector:
    """Accumulates system execution metrics and writes agent_statistics.json."""

    def __init__(self) -> None:
        self._recommendations_generated: int = 0
        self._comparisons_generated: int = 0
        self._clarification_requests: int = 0
        self._refinement_requests: int = 0
        self._refusals: int = 0
        self._recommendations_returned_counts: list[int] = []
        self._completed_conversations: int = 0
        self._total_conversations: int = 0
        self._validation_failures: int = 0

    def record_chat_turn(
        self,
        action: str,
        recommendations_count: int = 0,
        is_ended: bool = False,
        is_new_session: bool = False,
    ) -> None:
        """Records metric signals for a completed chat turn.

        Args:
            action: The AgentAction resolved.
            recommendations_count: The count of suggested items returned (if RETRIEVE).
            is_ended: True if the conversation reached the exit node.
            is_new_session: True if this is the start of a session.
        """
        if is_new_session:
            self._total_conversations += 1

        if action == "RETRIEVE":
            self._recommendations_generated += 1
            self._recommendations_returned_counts.append(recommendations_count)
        elif action == "COMPARE":
            self._comparisons_generated += 1
        elif action == "ASK_CLARIFICATION":
            self._clarification_requests += 1
        elif action == "REFUSE":
            self._refusals += 1

        if is_ended:
            self._completed_conversations += 1

    def record_validation_failure(self) -> None:
        """Records a validation exception occurrence."""
        self._validation_failures += 1

    def record_refinement(self) -> None:
        """Records a refinement action occurrence."""
        self._refinement_requests += 1

    def compile(self) -> dict[str, Any]:
        """Compiles accumulated metrics into a dictionary format.

        Returns:
            Dictionary containing compiled metrics.
        """
        total_sessions = self._total_conversations or 1
        completion_rate = self._completed_conversations / total_sessions

        avg_recs = 0.0
        if self._recommendations_returned_counts:
            avg_recs = sum(self._recommendations_returned_counts) / len(self._recommendations_returned_counts)

        return {
            "recommendations_generated": self._recommendations_generated,
            "comparisons_generated": self._comparisons_generated,
            "clarification_requests": self._clarification_requests,
            "refinement_requests": self._refinement_requests,
            "refusals": self._refusals,
            "average_recommendations": round(avg_recs, 2),
            "conversation_completion_rate": round(completion_rate, 4),
            "validation_failures": self._validation_failures,
            "generation_timestamp": datetime.now(UTC).isoformat(),
        }

    def save(self, path: str) -> None:
        """Saves the compiled statistics report to a JSON file.

        Args:
            path: Target JSON file path.
        """
        stats = self.compile()
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logger.info("AgentStatistics: Report saved to %s.", path)

