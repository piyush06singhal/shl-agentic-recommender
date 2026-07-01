"""Decision engine mapping conversation state and intents to next system actions."""

import logging

from app.agent.models import AgentAction, AgentIntent, ExtractedContext, TurnStatistics

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Deterministic routing module deciding the next logical action for the AI Agent."""

    def decide_next_action(
        self,
        intent: AgentIntent,
        context: ExtractedContext,
        turn_stats: TurnStatistics,
        has_sufficient_context: bool,
    ) -> AgentAction:
        """Determines next execution action based on active state parameters.

        Logic:
        1. Prompt Injection or Out of Scope -> REFUSE
        2. Turn statistics limit reached -> END_CONVERSATION
        3. Greeting -> RESPOND_GREETING
        4. Help -> RESPOND_HELP
        5. Conversation End -> END_CONVERSATION
        6. Comparison -> COMPARE
        7. Recommendation/Refinement/Clarification:
           - If context is sufficient -> RETRIEVE
           - If context is insufficient -> ASK_CLARIFICATION
        8. Unknown intent -> UNKNOWN (or fall back to ASK_CLARIFICATION)

        Args:
            intent: Reconstructed active intent classification.
            context: Current extracted context requirements.
            turn_stats: Active dialogue statistics.
            has_sufficient_context: True if context allows retrieval.

        Returns:
            An AgentAction resolved enum value.
        """
        # 1. Reject security violations or domain violations
        if intent == AgentIntent.PROMPT_INJECTION:
            logger.warning("DecisionEngine: Injection intent mapped to REFUSE.")
            return AgentAction.REFUSE

        if intent == AgentIntent.OUT_OF_SCOPE:
            logger.info("DecisionEngine: Out-of-Scope query mapped to REFUSE.")
            return AgentAction.REFUSE

        # 2. Limit checks
        if turn_stats.is_at_limit:
            logger.warning("DecisionEngine: Dialogue turn limit reached. Mapping to END_CONVERSATION.")
            return AgentAction.END_CONVERSATION

        # 3. Handle Greeting
        if intent == AgentIntent.GREETING:
            return AgentAction.RESPOND_GREETING

        # 4. Handle Help
        if intent == AgentIntent.HELP:
            return AgentAction.RESPOND_HELP

        # 5. Handle Termination
        if intent == AgentIntent.CONVERSATION_END:
            return AgentAction.END_CONVERSATION

        # 6. Handle Comparison targets
        if intent == AgentIntent.COMPARISON:
            if context.comparison_targets:
                return AgentAction.COMPARE
            # Fall back to retrieval if they didn't name targets
            return AgentAction.RETRIEVE if has_sufficient_context else AgentAction.ASK_CLARIFICATION

        # 7. Core Retrieval vs Clarification routing
        if intent in {AgentIntent.RECOMMENDATION, AgentIntent.REFINEMENT, AgentIntent.CLARIFICATION}:
            if has_sufficient_context:
                logger.info("DecisionEngine: Context is sufficient. Mapping to RETRIEVE.")
                return AgentAction.RETRIEVE
            else:
                logger.info("DecisionEngine: Context is insufficient. Mapping to ASK_CLARIFICATION.")
                return AgentAction.ASK_CLARIFICATION

        # 8. Unhandled or unknown intents fallback
        if has_sufficient_context:
            return AgentAction.RETRIEVE
        return AgentAction.UNKNOWN
