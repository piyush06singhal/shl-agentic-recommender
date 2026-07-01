"""ConversationEngine façade coordinating history analysis, parsing, and decisions."""

import logging
import time
from typing import Any

from app.agent.classifier import IntentClassifier
from app.agent.context import ActiveContextBuilder
from app.agent.decision import DecisionEngine
from app.agent.history import HistoryAnalyzer
from app.agent.models import AgentAction, AgentIntent, ExtractedContext, TurnStatistics
from app.agent.parser import ConversationParser
from app.agent.state import ConversationState
from app.agent.turns import TurnManager
from app.agent.validator import HistoryValidator

logger = logging.getLogger(__name__)


class ConversationEngine:
    """Coordinating façade processing raw histories to reconstruct conversation state."""

    def __init__(
        self,
        parser: ConversationParser | None = None,
        turn_manager: TurnManager | None = None,
        validator: HistoryValidator | None = None,
        context_builder: ActiveContextBuilder | None = None,
        classifier: IntentClassifier | None = None,
        decision_engine: DecisionEngine | None = None,
        analyzer: HistoryAnalyzer | None = None,
    ) -> None:
        self.parser = parser or ConversationParser()
        self.turn_manager = turn_manager or TurnManager()
        self.validator = validator or HistoryValidator()
        self.context_builder = context_builder or ActiveContextBuilder()
        self.classifier = classifier or IntentClassifier()
        self.decision_engine = decision_engine or DecisionEngine()
        self.analyzer = analyzer or HistoryAnalyzer()

    def process_conversation(
        self,
        raw_messages: list[Any],
        conversation_id: str = "default_session",
    ) -> ConversationState:
        """Processes raw stateless conversation messages history to build the latest state.

        Args:
            raw_messages: Chronological messages list (dict or Message models).
            conversation_id: Session identifier string.

        Returns:
            An immutable ConversationState snapshot representing the resolved turn.
        """
        start_time = time.monotonic()
        logger.info(
            "ConversationEngine: Processing session '%s' with %d messages...",
            conversation_id,
            len(raw_messages),
        )

        try:
            # 1. Parse and validate history structure
            messages = self.parser.parse_and_validate(raw_messages)

            # 2. Calculate turn statistics
            turn_stats = self.turn_manager.calculate_statistics(messages)
            # Enforce limits
            self.turn_manager.check_turn_limit(turn_stats)

            # 3. Check message levels integrity warnings
            warnings = self.validator.validate_message_integrity(messages)

            # 4. Reconstruct intents chronologically to build active context
            # We iterate through user turns to track requirements updates
            user_messages = [m for m in messages if m.role == "user"]
            intents: list[AgentIntent] = []
            running_context = ExtractedContext()

            # We build context and intents turn-by-turn to support "Latest Value Wins" refinement
            for idx, u_msg in enumerate(user_messages):
                # Unresolved fields up to this turn
                unresolved = self.context_builder.detect_missing_fields(running_context)

                # Resolve intent for this turn
                intent = self.classifier.resolve_intent(
                    latest_message=u_msg,
                    turn_idx=idx + 1,
                    unresolved_fields=unresolved,
                )
                intents.append(intent)

                # Temporarily build context up to this turn
                running_context = self.context_builder.rebuild_context(
                    user_messages[: idx + 1],
                    intents[: idx + 1],
                )

            # 5. Extract final context attributes and unresolved fields
            final_context = running_context
            missing_fields = self.context_builder.detect_missing_fields(final_context)
            has_sufficient = self.context_builder.has_sufficient_context(final_context)

            # Resolved intent is the intent of the last user turn
            resolved_intent = intents[-1] if intents else AgentIntent.UNKNOWN

            # 6. Analyze dialogue for contradictions or repeated statement warnings
            contradiction_warns = self.analyzer.detect_contradictions(final_context, messages)
            warnings.extend(contradiction_warns)

            if self.analyzer.detect_repeated_questions(messages):
                warnings.append("User sent the same query twice consecutively.")

            # 7. Decide next logical execution action
            next_action = self.decision_engine.decide_next_action(
                intent=resolved_intent,
                context=final_context,
                turn_stats=turn_stats,
                has_sufficient_context=has_sufficient,
            )

            latency_ms = (time.monotonic() - start_time) * 1000.0
            logger.info(
                "ConversationEngine: Resolved session '%s' | Turn=%d | Intent=%s | Action=%s | Latency=%.2fms",
                conversation_id,
                turn_stats.total_turns,
                resolved_intent,
                next_action,
                latency_ms,
            )

            return ConversationState(
                intent=resolved_intent,
                active_context=final_context,
                turn_count=turn_stats,
                missing_fields=missing_fields,
                next_action=next_action,
                is_valid=True,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(
                "ConversationEngine: Processing failed for session '%s': %s",
                conversation_id,
                e,
                exc_info=True,
            )
            # Graceful recovery fallback state
            fallback_stats = TurnStatistics(
                user_turns=0,
                assistant_turns=0,
                total_turns=len(raw_messages),
                is_at_limit=False,
            )
            return ConversationState(
                intent=AgentIntent.UNKNOWN,
                active_context=ExtractedContext(),
                turn_count=fallback_stats,
                missing_fields=["job_family", "skills"],
                next_action=AgentAction.UNKNOWN,
                is_valid=False,
                warnings=[f"Error: {e}"],
            )
