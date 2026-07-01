"""Prompt manager selecting templates and injecting state metadata constraints."""

import logging

from app.agent.models import AgentAction
from app.agent.state import ConversationState
from app.llm import template_manager

logger = logging.getLogger(__name__)


class PromptManager:
    """Assembles final prompt contexts, injecting active filters and catalog details."""

    def assemble_prompt(
        self,
        state: ConversationState,
        retrieved_context: str = "",
    ) -> str:
        """Selects template matching next_action and binds context.

        Args:
            state: Active ConversationState.
            retrieved_context: Joined catalog text blocks context.

        Returns:
            The compiled prompt string content.
        """
        action = state.next_action
        ctx = state.active_context

        # 1. Base system instruction rules prefix
        prefix = template_manager.SYSTEM_INSTRUCTIONS

        # 2. Select matching task template
        if action == AgentAction.ASK_CLARIFICATION:
            task = template_manager.CLARIFICATION_TEMPLATE.format(
                missing_fields=", ".join(state.missing_fields)
            )
        elif action == AgentAction.COMPARE:
            task = template_manager.COMPARISON_TEMPLATE.format(
                retrieved_context=retrieved_context
            )
        elif action == AgentAction.RETRIEVE:
            duration_str = f"{ctx.max_duration_mins} mins" if ctx.max_duration_mins else "Any"
            task = template_manager.RECOMMENDATION_TEMPLATE.format(
                job_family=", ".join(ctx.job_family) if ctx.job_family else "Any",
                candidate_level=", ".join(ctx.candidate_level) if ctx.candidate_level else "Any",
                skills=", ".join(ctx.skills) if ctx.skills else "Any",
                duration=duration_str,
                retrieved_context=retrieved_context,
            )
        elif action == AgentAction.RESPOND_GREETING:
            task = template_manager.GREETING_TEMPLATE
        elif action == AgentAction.RESPOND_HELP:
            task = template_manager.HELP_TEMPLATE
        elif action == AgentAction.REFUSE:
            task = template_manager.REFUSAL_TEMPLATE
        elif action == AgentAction.END_CONVERSATION:
            task = template_manager.END_CONVERSATION_TEMPLATE
        else:
            task = template_manager.UNKNOWN_TEMPLATE

        # 3. Combine parts
        full_prompt = f"{prefix}\n\n{task}"
        logger.debug("PromptManager: Prompt assembled for action %s.", action)
        return full_prompt
