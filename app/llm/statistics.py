"""Statistics collector accumulating LLM token counts and request latencies."""

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class LLMStatisticsCollector:
    """Accumulates LLM request latencies, token counts, and failure rates to llm_statistics.json."""

    def __init__(self) -> None:
        self._total_requests: int = 0
        self._prompt_tokens: int = 0
        self._completion_tokens: int = 0
        self._latencies_ms: list[float] = []
        self._retries_count: int = 0
        self._failures_count: int = 0
        self._fallbacks_count: int = 0
        self._provider_usage: dict[str, int] = {}
        self._prompt_types: dict[str, int] = {}

    def record_request(
        self,
        provider: str,
        prompt_type: str,
        latency_ms: float,
        prompt_text: str = "",
        response_text: str = "",
        retries: int = 0,
        failed: bool = False,
        fallback_triggered: bool = False,
    ) -> None:
        """Records metrics for a single LLM request.

        Args:
            provider: Name of provider.
            prompt_type: Intent action prompt category.
            latency_ms: completions API call latency.
            prompt_text: Input prompt text for token estimation.
            response_text: Output response text for token estimation.
            retries: counts of retries issued.
            failed: True if request failed.
            fallback_triggered: True if fallback engine resolved completion.
        """
        self._total_requests += 1
        self._latencies_ms.append(latency_ms)
        self._retries_count += retries

        if failed:
            self._failures_count += 1
        if fallback_triggered:
            self._fallbacks_count += 1

        # Track usage dicts
        self._provider_usage[provider] = self._provider_usage.get(provider, 0) + 1
        self._prompt_types[prompt_type] = self._prompt_types.get(prompt_type, 0) + 1

        # Simple token estimation: ~4 characters per token
        if prompt_text:
            self._prompt_tokens += max(1, len(prompt_text) // 4)
        if response_text:
            self._completion_tokens += max(1, len(response_text) // 4)

    def compile(self) -> dict[str, Any]:
        """Compiles accumulated statistics into a dictionary format.

        Returns:
            Dictionary containing compiled LLM statistics.
        """
        avg_latency = sum(self._latencies_ms) / len(self._latencies_ms) if self._latencies_ms else 0.0

        return {
            "total_requests": self._total_requests,
            "total_tokens": self._prompt_tokens + self._completion_tokens,
            "prompt_tokens": self._prompt_tokens,
            "completion_tokens": self._completion_tokens,
            "average_latency_ms": round(avg_latency, 2),
            "retries_count": self._retries_count,
            "failures_count": self._failures_count,
            "fallbacks_count": self._fallbacks_count,
            "provider_usage": self._provider_usage,
            "prompt_types": self._prompt_types,
            "generation_timestamp": datetime.now(UTC).isoformat(),
        }

    def save(self, path: str) -> None:
        """Saves the compiled statistics report to a JSON file.

        Args:
            path: Target JSON file path.
        """
        stats = self.compile()
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logger.info("LLMStatistics: Report saved to %s.", path)
