"""Response builder assembling fully formed ChatResponse envelopes."""

import logging

from app.agent.models import ChatResponse, RecommendedAssessment

logger = logging.getLogger(__name__)


class ResponseBuilder:
    """Assembles structured ChatResponse envelopes conforming to system schemas."""

    def build_response(
        self,
        reply: str,
        recommendations: list[RecommendedAssessment] | None = None,
        end_of_conversation: bool = False,
    ) -> ChatResponse:
        """Assembles a ChatResponse object from individual constituents.

        Args:
            reply: The chat text reply message string.
            recommendations: Optional list of structured RecommendedAssessment items.
            end_of_conversation: Boolean exit flag.

        Returns:
            A ChatResponse object.
        """
        recs = recommendations or []
        logger.debug(
            "ResponseBuilder: Assembling ChatResponse (recs=%d, end=%s)...",
            len(recs),
            end_of_conversation,
        )

        return ChatResponse(
            reply=reply,
            recommendations=recs,
            end_of_conversation=end_of_conversation,
        )
