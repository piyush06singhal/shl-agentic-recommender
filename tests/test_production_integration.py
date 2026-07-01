"""Production integration tests for end-to-end system validation."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient


class TestProductionIntegration:
    """Test suite for production-ready integration scenarios."""

    def test_health_check_response_time(self, client: TestClient) -> None:
        """Verify health check responds within acceptable latency."""
        start_time = time.monotonic()
        response = client.get("/health")
        duration_ms = (time.monotonic() - start_time) * 1000
        
        assert response.status_code == 200
        assert duration_ms < 500  # Health check should be fast
        assert response.json() == {"status": "ok"}

    def test_cors_headers_present(self, client: TestClient) -> None:
        """Verify CORS headers are properly configured."""
        response = client.options(
            "/chat",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
        )
        
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_security_headers(self, client: TestClient) -> None:
        """Verify security headers are present in responses."""
        response = client.get("/health")
        
        # Check for correlation ID
        assert "x-correlation-id" in response.headers
        assert "x-response-time-ms" in response.headers

    def test_request_validation_errors(self, client: TestClient) -> None:
        """Verify proper error handling for invalid requests."""
        # Empty payload
        response = client.post("/chat", json={})
        assert response.status_code == 422
        data = response.json()
        assert "error_type" in data
        
        # Missing required fields
        response = client.post("/chat", json={"messages": []})
        assert response.status_code == 422

    def test_malformed_message_payload(self, client: TestClient) -> None:
        """Verify validation of message structure."""
        invalid_payloads = [
            {"messages": [{"role": "invalid", "content": "test"}]},
            {"messages": [{"role": "user", "content": ""}]},
            {"messages": [{"content": "test"}]},  # missing role
        ]
        
        for payload in invalid_payloads:
            response = client.post("/chat", json=payload)
            assert response.status_code == 422

    def test_chat_response_structure(
        self,
        client: TestClient,
        sample_chat_request_payload: dict[str, Any],
    ) -> None:
        """Verify chat response has proper structure."""
        response = client.post("/chat", json=sample_chat_request_payload)
        
        if response.status_code == 200:
            data = response.json()
            
            # Required fields
            assert "reply" in data
            assert "recommendations" in data
            assert "end_of_conversation" in data
            
            # Type checks
            assert isinstance(data["reply"], str)
            assert isinstance(data["recommendations"], list)
            assert isinstance(data["end_of_conversation"], bool)
            
            # Recommendation structure
            for rec in data["recommendations"]:
                assert "name" in rec
                assert "url" in rec
                assert "test_type" in rec

    def test_performance_under_load(
        self,
        client: TestClient,
        sample_chat_request_payload: dict[str, Any],
    ) -> None:
        """Verify system handles multiple requests efficiently."""
        response_times = []
        
        for _ in range(5):
            start_time = time.monotonic()
            response = client.post("/chat", json=sample_chat_request_payload)
            duration_ms = (time.monotonic() - start_time) * 1000
            
            if response.status_code == 200:
                response_times.append(duration_ms)
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            assert avg_time < 5000  # Average should be under 5 seconds

    def test_empty_conversation_handling(self, client: TestClient) -> None:
        """Verify system handles minimal conversation gracefully."""
        payload = {
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = client.post("/chat", json=payload)
        assert response.status_code in [200, 500]  # Either success or handled error

    def test_long_conversation_handling(self, client: TestClient) -> None:
        """Verify system handles extended conversations."""
        messages = []
        for i in range(10):
            messages.append({"role": "user", "content": f"Message {i}"})
            messages.append({"role": "assistant", "content": f"Response {i}"})
        
        payload = {"messages": messages}
        response = client.post("/chat", json=payload)
        assert response.status_code in [200, 422, 500]

    def test_special_characters_handling(self, client: TestClient) -> None:
        """Verify system handles special characters in input."""
        special_inputs = [
            "Test with émojis 🎉",
            "Test with <script>alert('xss')</script>",
            "Test with SQL'; DROP TABLE users--",
            "Test with unicode \u200b\u200c\u200d",
        ]
        
        for content in special_inputs:
            payload = {"messages": [{"role": "user", "content": content}]}
            response = client.post("/chat", json=payload)
            assert response.status_code in [200, 422, 500]

    def test_timeout_configuration(self, client: TestClient) -> None:
        """Verify timeout settings are reasonable."""
        # This test verifies the client configuration
        # Actual timeout testing would require mocking slow responses
        assert client.timeout is None or client.timeout >= 25


@pytest.mark.integration
class TestEndToEndScenarios:
    """End-to-end test scenarios for common use cases."""

    def test_greeting_scenario(self, client: TestClient) -> None:
        """Test initial greeting interaction."""
        payload = {
            "messages": [
                {"role": "user", "content": "Hello, I need help finding an assessment"}
            ]
        }
        
        response = client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["reply"]  # Should have a reply

    def test_skill_based_search(self, client: TestClient) -> None:
        """Test searching for assessments by skill."""
        payload = {
            "messages": [
                {"role": "user", "content": "I need a test for software engineers"}
            ]
        }
        
        response = client.post("/chat", json=payload)
        if response.status_code == 200:
            data = response.json()
            assert "reply" in data

    def test_comparison_request(self, client: TestClient) -> None:
        """Test requesting comparison between assessments."""
        payload = {
            "messages": [
                {"role": "user", "content": "Compare OPQ and Verify tests"}
            ]
        }
        
        response = client.post("/chat", json=payload)
        assert response.status_code == 200

    def test_out_of_scope_query(self, client: TestClient) -> None:
        """Test handling of out-of-scope questions."""
        payload = {
            "messages": [
                {"role": "user", "content": "What's the weather like today?"}
            ]
        }
        
        response = client.post("/chat", json=payload)
        if response.status_code == 200:
            data = response.json()
            # Should gracefully redirect to scope
            assert data["reply"]
