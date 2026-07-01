"""AI Agent Core orchestrator coordinating conversation engine and retriever."""

import logging
from typing import Any

from app.agent.action_executor import ActionExecutor
from app.agent.conversation import ConversationEngine
from app.agent.conversation_manager import ConversationManager
from app.agent.memory import AgentMemory
from app.agent.models import ChatResponse
from app.agent.orchestrator import AgentOrchestrator
from app.agent.statistics import ConversationStatisticsCollector
from app.retriever.engine import RetrievalEngine

logger = logging.getLogger(__name__)


class ConversationalSHLAgent:
    """The complete conversational AI agent coordinating parser, retrieval, and decision executors."""

    def __init__(
        self,
        retrieval_engine: RetrievalEngine | None = None,
        conversation_engine: ConversationEngine | None = None,
        memory: AgentMemory | None = None,
        stats_collector: ConversationStatisticsCollector | None = None,
        llm_service: Any = None,
    ) -> None:
        # Connect hybrid engines
        from app.llm.service import LLMService
        self.retrieval_engine = retrieval_engine or RetrievalEngine()
        self.conversation_engine = conversation_engine or ConversationEngine()
        self.memory = memory or AgentMemory()
        self.stats_collector = stats_collector or ConversationStatisticsCollector()
        self.llm_service = llm_service or LLMService()

        # Connect response validation and formatting execution pipeline
        action_executor = ActionExecutor(
            retrieval_engine=self.retrieval_engine,
            llm_service=self.llm_service,
        )
        self.orchestrator = AgentOrchestrator(action_executor=action_executor)

        self.manager = ConversationManager(
            conversation_engine=self.conversation_engine,
            orchestrator=self.orchestrator,
            memory=self.memory,
        )

    def chat(self, messages: list[Any], session_id: str = "default_session") -> ChatResponse:
        """Handles incoming dialogue user request and routes execution pipeline.

        Args:
            messages: Chronological dialogue turns list.
            session_id: Unique session identifier string.

        Returns:
            A validated ChatResponse.
        """
        logger.info("ConversationalSHLAgent: Incoming turn for session '%s'.", session_id)
        try:
            # Process turn via manager
            res = self.manager.continue_conversation(session_id, messages)

            # Record stats
            state = self.memory.get_latest_state(session_id)
            if state:
                intents_str = [state.intent.value]
                self.stats_collector.record_session(
                    total_turns=state.turn_count.total_turns,
                    intents=intents_str,
                    ended_gracefully=res.end_of_conversation,
                )

            return res

        except Exception as e:
            logger.error("ConversationalSHLAgent: Chat turn processing failed: %s", e, exc_info=True)
            # Default fallback recovery
            fallback_reply = (
                "I apologize, but we encountered an error while processing your request. "
                "Let's refine your criteria. Could you re-specify which seniority levels "
                "or job families you are hiring for?"
            )
            return self.orchestrator.executor.response_builder.build_response(reply=fallback_reply)

    def restart(self, session_id: str) -> ChatResponse:
        """Purges active constraints history, returning starting welcome prompts.

        Args:
            session_id: Unique session identifier string.

        Returns:
            Greeting ChatResponse.
        """
        return self.manager.restart_conversation(session_id)

    def compare(self, names: list[str]) -> ChatResponse:
        """Trigger-based metadata comparison lookup outside active conversation history loops.

        Args:
            names: Assessment names.

        Returns:
            Comparison ChatResponse.
        """
        logger.info("ConversationalSHLAgent: Triggering direct comparison lookup for %s...", names)
        # Direct delegator bypasses history replay
        try:
            retrieval_res = self.retrieval_engine.retrieve_for_comparison(names=names)
            comparison_text = self.orchestrator.executor.comparison_engine.compare_assessments(
                retrieval_res.candidates
            )
            return self.orchestrator.executor.response_builder.build_response(reply=comparison_text)
        except Exception as e:
            logger.error("ConversationalSHLAgent: Direct comparison lookup failed: %s", e)
            return self.orchestrator.executor.response_builder.build_response(
                reply="An error occurred while compiling the side-by-side metadata breakdown."
            )

    def statistics(self) -> dict[str, Any]:
        """Exposes collected agent performance stats.

        Returns:
            Dict containing compiled conversation and agent stats.
        """
        return self.stats_collector.compile()
