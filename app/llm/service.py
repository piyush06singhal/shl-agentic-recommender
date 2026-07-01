"""LLM service orchestrating prompts, clients, validations, retries, and fallbacks."""

import logging
from typing import Any

from app.agent.models import AgentAction
from app.agent.state import ConversationState
from app.configs.settings import get_settings
from app.llm.client import LLMClient
from app.llm.fallback import LLMFallbackEngine
from app.llm.models import LLMConfig, LLMOutput
from app.llm.prompt_manager import PromptManager
from app.llm.statistics import LLMStatisticsCollector
from app.llm.structured_output import StructuredOutputParser
from app.llm.validator import LLMResponseValidator

logger = logging.getLogger(__name__)


class LLMService:
    """The central LLM service orchestrator providing provider-independent completion responses."""

    def __init__(
        self,
        client: LLMClient | None = None,
        prompt_manager: PromptManager | None = None,
        output_parser: StructuredOutputParser | None = None,
        validator: LLMResponseValidator | None = None,
        fallback_engine: LLMFallbackEngine | None = None,
        stats_collector: LLMStatisticsCollector | None = None,
    ) -> None:
        self.settings = get_settings()
        self.client = client or LLMClient()
        self.prompt_manager = prompt_manager or PromptManager()
        self.output_parser = output_parser or StructuredOutputParser()
        self.validator = validator or LLMResponseValidator()
        self.fallback_engine = fallback_engine or LLMFallbackEngine()
        self.stats_collector = stats_collector or LLMStatisticsCollector()

    def generate_response(
        self,
        state: ConversationState,
        retrieved_candidates: list[Any] | None = None,
        retrieved_context_text: str = "",
    ) -> LLMOutput:
        """Assembles prompt context and executes completions query with auto retries and fallbacks.

        Args:
            state: ConversationState.
            retrieved_candidates: Candidates returned from vector search.
            retrieved_context_text: Joined catalog blocks text.

        Returns:
            A schema-compliant LLMOutput.
        """
        action = state.next_action

        # 1. Determine model configuration temperature based on action intent
        temperature = 0.0  # Default low temperature for high facts constraints
        if action == AgentAction.RESPOND_GREETING:
            temperature = 0.7

        config = LLMConfig(
            model=self.settings.model_name,
            temperature=temperature,
            max_tokens=1500,
            timeout=self.settings.api_timeout,
            retries=3,
        )

        # 2. Select and build prompt
        prompt = self.prompt_manager.assemble_prompt(
            state=state,
            retrieved_context=retrieved_context_text,
        )

        allowed_names = [getattr(c, "name", "") or c.get("name", "") for c in (retrieved_candidates or [])]

        retries_attempted = 0
        while retries_attempted < config.retries:
            try:
                # 3. Call client completion
                raw_text, latency_ms = self.client.generate_completion(
                    prompt=prompt,
                    config=config,
                )

                # 4. Parse structured JSON outputs
                parsed_output = self.output_parser.parse_completions(raw_text)

                # 5. Validate output criteria (URL whitelist, candidate matches)
                validated_output = self.validator.validate(
                    output=parsed_output,
                    allowed_assessment_names=allowed_names if action == AgentAction.RETRIEVE else None,
                )

                # Record successful completions metrics
                self.stats_collector.record_request(
                    provider=self.client.provider.__class__.__name__,
                    prompt_type=action.value,
                    latency_ms=latency_ms,
                    prompt_text=prompt,
                    response_text=raw_text,
                    retries=retries_attempted,
                )

                return validated_output

            except Exception as e:
                retries_attempted += 1
                logger.warning(
                    "LLMService: Turn completions failed on attempt %d: %s. Retrying...",
                    retries_attempted,
                    e,
                )

        # 6. Fallback Triggered when completions retry limits are exceeded
        logger.error(
            "LLMService: All API completions retry loops exhausted. Triggering FallbackEngine fallback."
        )
        self.stats_collector.record_request(
            provider=self.client.provider.__class__.__name__,
            prompt_type=action.value,
            latency_ms=0.0,
            prompt_text=prompt,
            failed=True,
            fallback_triggered=True,
        )

        return self.fallback_engine.get_fallback_response(
            state=state,
            retrieved_candidates=retrieved_candidates,
        )

    def shutdown(self) -> None:
        """Gracefully closes socket connections and saves statistics."""
        self.client.shutdown()
        # Save stats to path
        stats_path = getattr(self.settings, "llm_statistics_path", "app/catalog/data/llm_statistics.json")
        self.stats_collector.save(stats_path)
