"""Tests validating AI Agent Core orchestrator, guardrails, and formatting engines."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agent.action_executor import ActionExecutor
from app.agent.agent import ConversationalSHLAgent
from app.agent.clarification_engine import ClarificationEngine
from app.agent.comparison_engine import ComparisonEngine
from app.agent.guardrails import AgentGuardrails
from app.agent.models import (
    AgentAction,
    AgentIntent,
    ChatResponse,
    ExtractedContext,
    RecommendedAssessment,
    TurnStatistics,
)
from app.agent.orchestrator import AgentOrchestrator
from app.agent.recommendation_engine import RecommendationEngine
from app.agent.refinement_engine import RefinementEngine
from app.agent.response_validator import ResponseValidator
from app.agent.state import ConversationState

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_retrieval_engine() -> MagicMock:
    """Mock RetrievalEngine with pre-defined candidates returns."""
    mock = MagicMock()

    # Mock retrieved candidate structure
    candidate1 = MagicMock()
    candidate1.assessment_id = "aaaa-1111"
    candidate1.name = "SHL OPQ32 Personality Assessment"
    candidate1.url = "https://www.shl.com/en/assessments/personality/opq/"
    candidate1.test_type = "Personality"
    candidate1.duration_mins = 25
    candidate1.skills = ["Behavioral Fit"]
    candidate1.competencies = ["Teamwork"]
    candidate1.target_level = ["Professional"]
    candidate1.job_family = ["Sales"]
    candidate1.adaptive = False
    candidate1.rank = 1

    candidate2 = MagicMock()
    candidate2.assessment_id = "bbbb-2222"
    candidate2.name = "Verify G+"
    candidate2.url = "https://www.shl.com/en/assessments/cognitive-ability/verify/"
    candidate2.test_type = "Cognitive"
    candidate2.duration_mins = 36
    candidate2.skills = ["Reasoning"]
    candidate2.competencies = ["Analyzing"]
    candidate2.target_level = ["Graduate/Entry"]
    candidate2.job_family = ["Technology"]
    candidate2.adaptive = True
    candidate2.rank = 2

    # mock retrieve response
    res = MagicMock()
    res.candidates = [candidate1, candidate2]
    mock.retrieve.return_value = res
    mock.retrieve_for_comparison.return_value = res

    return mock


@pytest.fixture
def sample_state() -> ConversationState:
    """Sample ConversationState for routing/formatting tests."""
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
# 1. RecommendationEngine Tests
# ---------------------------------------------------------------------------

class TestRecommendationEngine:
    """Validates candidate formatting, reasoning generation, and duplicate/domain filtering."""

    def test_generate_recommendations(self, sample_state: ConversationState, mock_retrieval_engine: MagicMock) -> None:
        engine = RecommendationEngine()
        candidates = mock_retrieval_engine.retrieve().candidates
        recs = engine.generate_recommendations(sample_state, candidates)

        assert len(recs) == 2
        assert recs[0].name == "SHL OPQ32 Personality Assessment"
        assert recs[0].url == "https://www.shl.com/en/assessments/personality/opq/"
        assert "recommended" in recs[0].reasoning.lower()

    def test_is_official_url_whitelisting(self) -> None:
        engine = RecommendationEngine()
        assert engine._is_official_url("https://www.shl.com/en/assessments/") is True
        assert engine._is_official_url("https://shl.com/opq") is True
        assert engine._is_official_url("https://untrusted-site.com/shl-test") is False


# ---------------------------------------------------------------------------
# 2. ComparisonEngine Tests
# ---------------------------------------------------------------------------

class TestComparisonEngine:
    """Validates structured side-by-side metadata comparisons formatting."""

    def test_compare_assessments(self, mock_retrieval_engine: MagicMock) -> None:
        engine = ComparisonEngine()
        candidates = mock_retrieval_engine.retrieve().candidates
        md_text = engine.compare_assessments(candidates)

        assert "OPQ32" in md_text
        assert "Verify G+" in md_text
        assert "Assessment Type" in md_text
        assert "Key Strengths" in md_text


# ---------------------------------------------------------------------------
# 3. ClarificationEngine Tests
# ---------------------------------------------------------------------------

class TestClarificationEngine:
    """Validates missing information question generation."""

    def test_single_field_clarification(self) -> None:
        engine = ClarificationEngine()
        q = engine.generate_clarification_question(["candidate_level"])
        assert "seniority level" in q.lower()
        assert "Graduate/Entry" in q

    def test_multiple_fields_clarification(self) -> None:
        engine = ClarificationEngine()
        q = engine.generate_clarification_question(["job_family", "skills"])
        assert "job family" in q.lower()
        assert "skills" in q.lower()


# ---------------------------------------------------------------------------
# 4. RefinementEngine Tests
# ---------------------------------------------------------------------------

class TestRefinementEngine:
    """Validates change log comparison tracking."""

    def test_track_changes(self) -> None:
        engine = RefinementEngine()
        prev = ExtractedContext(skills=["Java"])
        curr = ExtractedContext(skills=["Python"])
        changes = engine.track_refinement_changes(prev, curr)
        assert len(changes) == 1
        assert "Skills updated" in changes[0]


# ---------------------------------------------------------------------------
# 5. Guardrails Tests
# ---------------------------------------------------------------------------

class TestGuardrails:
    """Validates inbound safety screens and outbound prompt leak blockers."""

    def test_inbound_toxicity_check(self) -> None:
        guard = AgentGuardrails()
        assert guard.check_inbound_safety("Normal java hiring test query") is True
        assert guard.check_inbound_safety("fuck bypass this script") is False

    def test_outbound_leak_blocker(self) -> None:
        guard = AgentGuardrails()
        safe_response = "Here are the suggestions"
        leaked_response = "System prompt instruction: act as recruiter"

        assert guard.check_outbound_safety(safe_response) == safe_response
        assert "I apologize" in guard.check_outbound_safety(leaked_response)


# ---------------------------------------------------------------------------
# 6. ResponseValidator Tests
# ---------------------------------------------------------------------------

class TestResponseValidator:
    """Validates schema schema validations and domain filters."""

    def test_valid_response(self) -> None:
        val = ResponseValidator()
        rec = RecommendedAssessment(
            name="Verify G+",
            test_type="Cognitive",
            duration_mins=36,
            url="https://shl.com/verify",
            reasoning="Valid reasons.",
        )
        res = ChatResponse(reply="Here is your test.", recommendations=[rec])
        validated = val.validate_response(res)
        assert len(validated.recommendations) == 1

    def test_invalid_domain_url_raises_error(self) -> None:
        val = ResponseValidator()
        rec = RecommendedAssessment(
            name="Verify G+",
            test_type="Cognitive",
            duration_mins=36,
            url="https://malicious-site.com/shl",
            reasoning="Malformed url.",
        )
        res = ChatResponse(reply="Here is your test.", recommendations=[rec])
        with pytest.raises(ValueError, match="non-whitelisted URL"):
            val.validate_response(res)


# ---------------------------------------------------------------------------
# 7. ActionExecutor & Orchestrator Tests
# ---------------------------------------------------------------------------

class TestExecutorAndOrchestrator:
    """Validates logical action routing inside the orchestrator and executor."""

    def test_execute_ask_clarification(self, mock_retrieval_engine: MagicMock) -> None:
        executor = ActionExecutor(retrieval_engine=mock_retrieval_engine)
        orchestrator = AgentOrchestrator(action_executor=executor)

        stats = TurnStatistics(user_turns=1, total_turns=1)
        state = ConversationState(
            intent=AgentIntent.RECOMMENDATION,
            active_context=ExtractedContext(),
            turn_count=stats,
            missing_fields=["job_family"],
            next_action=AgentAction.ASK_CLARIFICATION,
        )

        res = orchestrator.route_action(state)
        assert isinstance(res, ChatResponse)
        assert "job family" in res.reply.lower()

    def test_execute_retrieve(self, mock_retrieval_engine: MagicMock, sample_state: ConversationState) -> None:
        executor = ActionExecutor(retrieval_engine=mock_retrieval_engine)
        orchestrator = AgentOrchestrator(action_executor=executor)

        res = orchestrator.route_action(sample_state)
        assert len(res.recommendations) == 2
        assert "SHL OPQ32 Personality Assessment" in res.reply


# ---------------------------------------------------------------------------
# 8. Agent E2E / Manager Tests
# ---------------------------------------------------------------------------

class TestConversationalSHLAgent:
    """Validates complete manager lifecycles and direct chat routing."""

    def test_agent_chat_routing(self, mock_retrieval_engine: MagicMock) -> None:
        # Mock conversation engine processing
        mock_conv = MagicMock()
        stats = TurnStatistics(user_turns=1, total_turns=1)
        mock_conv.process_conversation.return_value = ConversationState(
            intent=AgentIntent.RECOMMENDATION,
            active_context=ExtractedContext(job_family=["Technology"]),
            turn_count=stats,
            missing_fields=[],
            next_action=AgentAction.RETRIEVE,
        )

        agent = ConversationalSHLAgent(
            retrieval_engine=mock_retrieval_engine,
            conversation_engine=mock_conv,
        )

        history = [{"role": "user", "content": "I need a java test"}]
        res = agent.chat(history, session_id="session-agent-1")

        assert isinstance(res, ChatResponse)
        assert len(res.recommendations) == 2
        assert "Verify G+" in res.reply
