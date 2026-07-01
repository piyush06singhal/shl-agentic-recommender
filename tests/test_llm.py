"""Tests validating the LLM integration layer, including factories, parsers, and fallbacks."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agent.models import AgentAction, AgentIntent, ExtractedContext, TurnStatistics
from app.agent.state import ConversationState
from app.llm.factory import LLMProviderFactory
from app.llm.fallback import LLMFallbackEngine
from app.llm.models import LLMOutput, LLMRecommendation
from app.llm.prompt_manager import PromptManager
from app.llm.provider import OpenAIProvider
from app.llm.structured_output import StructuredOutputParser
from app.llm.validator import LLMResponseValidator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_state() -> ConversationState:
    """Sample ConversationState mapping RETRIEVE action."""
    stats = TurnStatistics(user_turns=1, total_turns=1)
    ctx = ExtractedContext(job_family=["Technology"], skills=["Java"])
    return ConversationState(
        intent=AgentIntent.RECOMMENDATION,
        active_context=ctx,
        turn_count=stats,
        missing_fields=[],
        next_action=AgentAction.RETRIEVE,
    )


# ---------------------------------------------------------------------------
# 1. PromptManager Tests
# ---------------------------------------------------------------------------

class TestPromptManager:
    """Validates prompt templates selections and variable bindings."""

    def test_assemble_recommendation_prompt(self, sample_state: ConversationState) -> None:
        manager = PromptManager()
        prompt = manager.assemble_prompt(sample_state, retrieved_context="[1] Verify G+")

        assert "ROLE:" in prompt
        assert "Java" in prompt
        assert "[1] Verify G+" in prompt

    def test_assemble_clarification_prompt(self) -> None:
        manager = PromptManager()
        stats = TurnStatistics(user_turns=1, total_turns=1)
        state = ConversationState(
            intent=AgentIntent.RECOMMENDATION,
            active_context=ExtractedContext(),
            turn_count=stats,
            missing_fields=["job_family", "skills"],
            next_action=AgentAction.ASK_CLARIFICATION,
        )
        prompt = manager.assemble_prompt(state)
        assert "MISSING FIELDS:" in prompt
        assert "job_family, skills" in prompt


# ---------------------------------------------------------------------------
# 2. StructuredOutputParser Tests
# ---------------------------------------------------------------------------

class TestStructuredOutputParser:
    """Validates raw completions parsing and JSON cleaning."""

    def test_parse_valid_json_markdown(self) -> None:
        parser = StructuredOutputParser()
        raw = """
        Some thinking or garbage prefix
        ```json
        {
          "reply": "Here is the recommendation.",
          "recommendations": [
            {
              "name": "Verify G+",
              "url": "https://shl.com/verify",
              "test_type": "Cognitive"
            }
          ],
          "end_of_conversation": false
        }
        ```
        postfix noise
        """
        output = parser.parse_completions(raw)
        assert output.reply == "Here is the recommendation."
        assert len(output.recommendations) == 1
        assert output.recommendations[0].name == "Verify G+"

    def test_parse_invalid_json_raises_error(self) -> None:
        parser = StructuredOutputParser()
        with pytest.raises(ValueError, match="malformed JSON"):
            parser.parse_completions("This is not JSON at all.")


# ---------------------------------------------------------------------------
# 3. LLMResponseValidator Tests
# ---------------------------------------------------------------------------

class TestLLMResponseValidator:
    """Validates generated recommendations URL whitelist check and name filters."""

    def test_validate_whitelisted_urls(self) -> None:
        val = LLMResponseValidator()
        rec1 = LLMRecommendation(name="Verify G+", url="https://www.shl.com/verify", test_type="Cognitive")
        rec2 = LLMRecommendation(name="OPQ32", url="https://untrusted.com/opq", test_type="Personality")

        output = LLMOutput(reply="reply", recommendations=[rec1, rec2])
        validated = val.validate(output)

        # rec2 should be pruned because of non-whitelisted domain URL
        assert len(validated.recommendations) == 1
        assert validated.recommendations[0].name == "Verify G+"

    def test_validate_allowed_names(self) -> None:
        val = LLMResponseValidator()
        rec1 = LLMRecommendation(name="Verify G+", url="https://shl.com/verify", test_type="Cognitive")
        rec2 = LLMRecommendation(name="Hallucinated Test", url="https://shl.com/fake", test_type="Cognitive")

        output = LLMOutput(reply="reply", recommendations=[rec1, rec2])
        validated = val.validate(output, allowed_assessment_names=["Verify G+"])

        # rec2 should be pruned because its name is not in the allowed list
        assert len(validated.recommendations) == 1
        assert validated.recommendations[0].name == "Verify G+"


# ---------------------------------------------------------------------------
# 4. LLMFallbackEngine Tests
# ---------------------------------------------------------------------------

class TestLLMFallbackEngine:
    """Validates pre-templated output generation."""

    def test_get_fallback_greeting(self) -> None:
        engine = LLMFallbackEngine()
        stats = TurnStatistics(user_turns=1, total_turns=1)
        state = ConversationState(
            intent=AgentIntent.GREETING,
            active_context=ExtractedContext(),
            turn_count=stats,
            missing_fields=[],
            next_action=AgentAction.RESPOND_GREETING,
        )
        output = engine.get_fallback_response(state)
        assert "hiring consultant" in output.reply.lower()
        assert len(output.recommendations) == 0

    def test_get_fallback_retrieve(self, sample_state: ConversationState) -> None:
        engine = LLMFallbackEngine()
        candidate = MagicMock()
        candidate.name = "Verify G+"
        candidate.url = "https://shl.com/verify"
        candidate.test_type = "Cognitive"

        output = engine.get_fallback_response(sample_state, retrieved_candidates=[candidate])
        assert "Verify G+" in output.reply
        assert len(output.recommendations) == 1
        assert output.recommendations[0].url == "https://shl.com/verify"


# ---------------------------------------------------------------------------
# 5. ProviderFactory Tests
# ---------------------------------------------------------------------------

class TestLLMProviderFactory:
    """Validates factory model matching."""

    def test_get_openai_provider(self) -> None:
        factory = LLMProviderFactory()
        provider = factory.get_provider("openai-gpt-4o")
        assert isinstance(provider, OpenAIProvider)
