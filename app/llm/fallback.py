"""Fallback engine providing template-based fallback responses when the LLM is offline."""

import logging
from typing import Any

from app.agent.models import AgentAction
from app.agent.state import ConversationState
from app.llm.models import LLMOutput, LLMRecommendation

logger = logging.getLogger(__name__)


class LLMFallbackEngine:
    """Generates standard, schema-compliant responses without LLM interaction."""

    def get_fallback_response(
        self,
        state: ConversationState,
        retrieved_candidates: list[Any] | None = None,
    ) -> LLMOutput:
        """Assembles a static, fully compliant LLMOutput matching the action.

        Args:
            state: ConversationState.
            retrieved_candidates: Retrieved candidate list.

        Returns:
            An LLMOutput wrapper.
        """
        action = state.next_action
        logger.info("LLMFallbackEngine: Generating fallback template response for action %s.", action)

        recs: list[LLMRecommendation] = []
        end_of_conversation = False

        if action == AgentAction.ASK_CLARIFICATION:
            # Generate clarification question using simple heuristics
            missing = state.missing_fields
            if "job_family" in missing and "skills" in missing:
                reply = (
                    "Could you specify what job family (e.g. Technology, Sales, Finance) and what skills "
                    "you would like to evaluate?"
                )
            elif "candidate_level" in missing:
                reply = (
                    "What candidate experience levels are you looking to assess (e.g. Graduate/Entry, "
                    "Professional, Leadership)?"
                )
            else:
                reply = "Could you clarify what candidate seniority level or skills you need to measure?"

        elif action == AgentAction.COMPARE:
            reply = "Here is a comparison of the requested assessments:\n"
            for c in (retrieved_candidates or []):
                name = getattr(c, "name", "") or c.get("name", "")
                desc = getattr(c, "description", "") or c.get("description", "")
                url = getattr(c, "url", "") or c.get("url", "")
                reply += f"- **{name}**: {desc} (Link: {url})\n"

        elif action == AgentAction.RETRIEVE:
            # Map candidates exactly
            for c in (retrieved_candidates or [])[:10]:
                name = getattr(c, "name", "") or c.get("name", "")
                url = getattr(c, "url", "") or c.get("url", "")
                test_type = getattr(c, "test_type", "") or c.get("test_type", "")
                recs.append(LLMRecommendation(name=name, url=url, test_type=test_type))

            names_str = ", ".join(r.name for r in recs)
            reply = (
                f"We found the following matching SHL assessments for your query: {names_str}. "
                "Please find the links below."
            )

        elif action == AgentAction.RESPOND_GREETING:
            reply = (
                "Hello! I am your SHL assessment hiring consultant. I can help you discover, "
                "recommend, and compare official SHL assessment products for recruitment. "
                "What role or job family are you hiring for?"
            )

        elif action == AgentAction.RESPOND_HELP:
            reply = (
                "I can recommend suitable SHL assessments based on candidate experience levels, "
                "target job families, languages, duration limits, or specific skills. You can also "
                "ask me to compare assessments (e.g. 'Compare OPQ and Verify G+'). What role are you focused on?"
            )

        elif action == AgentAction.REFUSE:
            reply = (
                "I apologize, but I can only assist with discovering, recommending, or comparing "
                "official SHL assessment products for recruitment. Let me know if you would like "
                "help finding a test for your candidate seniority levels."
            )

        elif action == AgentAction.END_CONVERSATION:
            reply = (
                "Thank you for consulting with me. I hope you found the right SHL assessments. "
                "Good luck with your hiring! Let me know if you would like to start a new search."
            )
            end_of_conversation = True

        else:
            reply = (
                "I'm not sure how to assist with that request. I can help you recommend, search, "
                "or compare SHL assessments. Could you specify which candidate skills or job families "
                "you are hiring for?"
            )

        return LLMOutput(
            reply=reply,
            recommendations=recs,
            end_of_conversation=end_of_conversation,
        )
