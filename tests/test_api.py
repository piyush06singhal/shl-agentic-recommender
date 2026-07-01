"""API integration tests for health check, request validation, and chat response formats."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.agent.models import ChatResponse, RecommendedAssessment


def test_health_endpoint(client: TestClient) -> None:
    """Verifies GET /health returns HTTP 200 and status ok payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_interaction_schema(
    client: TestClient,
    sample_chat_request_payload: dict[str, Any],
    monkeypatch: Any,
) -> None:
    """Verifies POST /chat validates request schema and propagates structured responses."""
    # Mock agent.chat return value to keep unit testing decoupled and fast
    mock_response = ChatResponse(
        reply="Mocked conversational response.",
        recommendations=[
            RecommendedAssessment(
                name="Verify G+ Cognitive Assessment",
                url="https://shl.com/verify",
                test_type="Cognitive",
                duration_mins=30,
                skills=["Problem Solving"],
                competencies=["Logical Reasoning"],
                seniority_levels=["Graduate"],
                reasoning="Matches cognitive requirements.",
            )
        ],
        end_of_conversation=False,
    )

    # Inject mock into app state agent instance
    app_state: Any = client.app.state  # type: ignore[attr-defined]
    monkeypatch.setattr(
        app_state.ai_agent,
        "chat",
        MagicMock(return_value=mock_response),
    )

    response = client.post("/chat", json=sample_chat_request_payload)
    assert response.status_code == 200

    data = response.json()
    assert "reply" in data
    assert "recommendations" in data
    assert "end_of_conversation" in data
    assert isinstance(data["end_of_conversation"], bool)

    recs = data["recommendations"]
    assert len(recs) == 1
    assert recs[0]["name"] == "Verify G+ Cognitive Assessment"
    assert recs[0]["url"] == "https://shl.com/verify"
    assert recs[0]["test_type"] == "Cognitive"


def test_chat_invalid_schema(client: TestClient) -> None:
    """Verifies POST /chat rejects empty payloads or missing properties."""
    response = client.post("/chat", json={})
    assert response.status_code == 422
    data = response.json()
    assert "error_type" in data
    assert data["error_type"] == "RequestValidationError"
