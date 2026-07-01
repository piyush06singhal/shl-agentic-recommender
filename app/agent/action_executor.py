"""Action executor coordinating task flows for decided actions."""

import logging
from typing import Any

from app.agent.clarification_engine import ClarificationEngine
from app.agent.comparison_engine import ComparisonEngine
from app.agent.guardrails import AgentGuardrails
from app.agent.models import AgentAction, ChatResponse, RecommendedAssessment
from app.agent.recommendation_engine import RecommendationEngine
from app.agent.refinement_engine import RefinementEngine
from app.agent.response_builder import ResponseBuilder
from app.agent.response_validator import ResponseValidator
from app.agent.state import ConversationState

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Orchestrates task executors delegates to run the decided logical action flow."""

    def __init__(
        self,
        retrieval_engine: Any,  # Avoid circular import, type verified at runtime
        recommendation_engine: RecommendationEngine | None = None,
        comparison_engine: ComparisonEngine | None = None,
        clarification_engine: ClarificationEngine | None = None,
        refinement_engine: RefinementEngine | None = None,
        guardrails: AgentGuardrails | None = None,
        response_builder: ResponseBuilder | None = None,
        response_validator: ResponseValidator | None = None,
        llm_service: Any = None,  # Injected LLMService instance
    ) -> None:
        self.retrieval_engine = retrieval_engine
        self.recommendation_engine = recommendation_engine or RecommendationEngine()
        self.comparison_engine = comparison_engine or ComparisonEngine()
        self.clarification_engine = clarification_engine or ClarificationEngine()
        self.refinement_engine = refinement_engine or RefinementEngine()
        self.guardrails = guardrails or AgentGuardrails()
        self.response_builder = response_builder or ResponseBuilder()
        self.response_validator = response_validator or ResponseValidator()
        self.llm_service = llm_service

    def execute_action(self, state: ConversationState) -> ChatResponse:
        """Invokes appropriate handler delegate based on the state's next_action.

        Args:
            state: Reconstructed ConversationState.

        Returns:
            A validated ChatResponse.
        """
        action = state.next_action
        logger.info("ActionExecutor: Executing action: %s", action)

        # 1. Perform retrieval if required
        candidates: list[Any] = []
        retrieved_context_text = ""

        if action == AgentAction.RETRIEVE:
            candidates = self._query_retriever(state)
        elif action == AgentAction.COMPARE:
            candidates = self._query_comparison_retriever(state)

        # Build context blocks if candidates were found
        if candidates:
            from app.retriever.context_builder import ContextBuilder
            _, retrieved_context_text = ContextBuilder().build(candidates)

        # 2. Check if LLM Service is injected and configured for generation
        if self.llm_service is not None:
            try:
                logger.info("ActionExecutor: Delegating reply generation to LLMService...")
                llm_output = self.llm_service.generate_response(
                    state=state,
                    retrieved_candidates=candidates,
                    retrieved_context_text=retrieved_context_text,
                )

                # Convert LLMOutput to RecommendedAssessments using RecommendationEngine verification
                recs = []
                if action == AgentAction.RETRIEVE and llm_output.recommendations:
                    # Let the recommendation engine validate and reason about LLM recommendations
                    # or map them directly
                    for r in llm_output.recommendations:
                        # Find matching candidate from candidates
                        matching = None
                        for c in candidates:
                            name_val = getattr(c, "name", "") or c.get("name", "")
                            if name_val.lower() == r.name.lower():
                                matching = c
                                break

                        if matching:
                            # Build Reasoning
                            reasoning = self.recommendation_engine._generate_reasoning(
                                state=state,
                                name=r.name,
                                test_type=r.test_type,
                                skills=getattr(matching, "skills", []) or matching.get("skills", []),
                                levels=getattr(matching, "target_level", []) or matching.get("target_level", []),
                            )
                            m_skills = list(getattr(matching, "skills", []) or matching.get("skills", []))
                            m_comps = list(getattr(matching, "competencies", []) or matching.get("competencies", []))
                            m_levels = list(getattr(matching, "target_level", []) or matching.get("target_level", []))
                            recs.append(RecommendedAssessment(
                                name=r.name,
                                test_type=r.test_type,
                                duration_mins=getattr(matching, "duration_mins", 0) or matching.get("duration_mins", 0),
                                url=r.url,
                                skills=m_skills,
                                competencies=m_comps,
                                seniority_levels=m_levels,
                                reasoning=reasoning,
                            ))

                res = self.response_builder.build_response(
                    reply=llm_output.reply,
                    recommendations=recs,
                    end_of_conversation=llm_output.end_of_conversation,
                )

                # Sanitize and validate
                res.reply = self.guardrails.check_outbound_safety(res.reply)
                return self.response_validator.validate_response(res)

            except Exception as e:
                logger.error(
                    "ActionExecutor: LLM completions delegation failed: %s. Falling back.",
                    e,
                )

        # 3. Local templates fallback logic (if LLM is offline or not injected)
        if action == AgentAction.REFUSE:
            reply = self.guardrails.get_safe_refusal_message()
            res = self.response_builder.build_response(reply=reply)

        elif action == AgentAction.ASK_CLARIFICATION:
            reply = self.clarification_engine.generate_clarification_question(state.missing_fields)
            res = self.response_builder.build_response(reply=reply)

        elif action == AgentAction.RETRIEVE:
            if not candidates:
                reply = (
                    "I couldn't find any SHL assessments matching your specific criteria. "
                    "Could you adjust your constraints (e.g. skills or seniority levels) or "
                    "mention a different role?"
                )
                res = self.response_builder.build_response(reply=reply)
            else:
                recommendations = self.recommendation_engine.generate_recommendations(state, candidates)
                names_str = ", ".join(r.name for r in recommendations)
                reply = (
                    f"Based on your hiring requirements, we recommend the following assessments: {names_str}. "
                    "Please review the detailed list below for individual links and reasoning."
                )
                res = self.response_builder.build_response(reply=reply, recommendations=recommendations)

        elif action == AgentAction.COMPARE:
            if not candidates:
                reply = (
                    "I could not locate the requested assessments in the SHL catalog. "
                    "Could you verify the names and try again?"
                )
                res = self.response_builder.build_response(reply=reply)
            else:
                comparison_text = self.comparison_engine.compare_assessments(candidates)
                res = self.response_builder.build_response(reply=comparison_text)

        elif action == AgentAction.RESPOND_GREETING:
            reply = (
                "Hello! I am your SHL assessment hiring consultant. I can help you discover, "
                "recommend, and compare official SHL assessment products for recruitment. "
                "What role or job family are you hiring for?"
            )
            res = self.response_builder.build_response(reply=reply)

        elif action == AgentAction.RESPOND_HELP:
            reply = (
                "I can recommend suitable SHL assessments based on candidate experience levels, "
                "target job families, languages, duration limits, or specific skills. You can also "
                "ask me to compare assessments (e.g. 'Compare OPQ and Verify G+'). What role are you focused on?"
            )
            res = self.response_builder.build_response(reply=reply)

        elif action == AgentAction.END_CONVERSATION:
            reply = (
                "Thank you for consulting with me. I hope you found the right SHL assessments. "
                "Good luck with your hiring! Let me know if you would like to start a new search."
            )
            res = self.response_builder.build_response(reply=reply, end_of_conversation=True)

        else:
            reply = (
                "I'm not sure how to assist with that request. I can help you recommend, search, "
                "or compare SHL assessments. Could you specify which candidate skills or job families "
                "you are hiring for?"
            )
            res = self.response_builder.build_response(reply=reply)

        # Apply outbound safety guardrails
        res.reply = self.guardrails.check_outbound_safety(res.reply)

        # Validate response schema
        validated_res = self.response_validator.validate_response(res)
        return validated_res

    def _query_retriever(self, state: ConversationState) -> list[Any]:
        ctx = state.active_context
        query_parts = []
        if ctx.preferred_assessments:
            query_parts.extend(ctx.preferred_assessments)
        if ctx.skills:
            query_parts.extend(ctx.skills)
        if ctx.job_family:
            query_parts.extend(ctx.job_family)

        query_text = " ".join(query_parts) if query_parts else "SHL assessment"

        from app.retriever.models import MetadataFilters as RetrievalFilters
        retriever_filters = RetrievalFilters(
            job_family=ctx.job_family,
            test_type=ctx.assessment_type,
            target_level=ctx.candidate_level,
            languages=ctx.languages,
            max_duration_mins=ctx.max_duration_mins,
            skills=ctx.skills,
            competencies=ctx.competencies,
        )

        try:
            retrieval_res = self.retrieval_engine.retrieve(
                query_text=query_text,
                filters=retriever_filters,
            )
            return list(retrieval_res.candidates)
        except Exception as e:
            logger.error("ActionExecutor: RetrievalEngine retrieve failed: %s", e)
            return []

    def _query_comparison_retriever(self, state: ConversationState) -> list[Any]:
        targets = state.active_context.comparison_targets
        try:
            retrieval_res = self.retrieval_engine.retrieve_for_comparison(names=targets)
            return list(retrieval_res.candidates)
        except Exception as e:
            logger.error("ActionExecutor: RetrievalEngine retrieve_for_comparison failed: %s", e)
            return []
