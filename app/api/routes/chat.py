"""Conversational chat endpoint routing configuration."""

import logging

from fastapi import APIRouter, Depends, Request, status

from app.agent.agent import ConversationalSHLAgent
from app.api.dependencies import get_ai_agent
from app.schemas.request import ChatRequest
from app.schemas.response import ChatResponse as ClientChatResponse
from app.schemas.response import Recommendation as ClientRecommendation

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/chat",
    response_model=ClientChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Conversational chat endpoint handler.",
    response_description="The conversational agent response block schema.",
)
async def chat_endpoint(
    request: Request,
    payload: ChatRequest,
    agent: ConversationalSHLAgent = Depends(get_ai_agent),
) -> ClientChatResponse:
    """Processes incoming stateless dialogue histories.

    Runs validation, turn checks, context reconstruction, intent
    classification, and catalog recommendations.
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown_session")
    logger.info(
        "Received POST /chat request containing %d messages (Session ID: %s).",
        len(payload.messages),
        correlation_id,
    )

    # 1. Delegate request processing to the SHL Agent wrapper
    # It handles parsing, extraction, and decides retrieval or LLM response logic
    agent_res = agent.chat(messages=payload.messages, session_id=correlation_id)

    # 2. Map Agent Core response model to API response schema
    api_recommendations = [
        ClientRecommendation(
            name=r.name,
            url=r.url,
            test_type=r.test_type,
        )
        for r in agent_res.recommendations
    ]

    return ClientChatResponse(
        reply=agent_res.reply,
        recommendations=api_recommendations,
        end_of_conversation=agent_res.end_of_conversation,
    )
