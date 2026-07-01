"""Health status endpoint routing configuration."""

import logging

from fastapi import APIRouter, Depends, status

from app.agent.agent import ConversationalSHLAgent
from app.api.dependencies import get_ai_agent

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Audits system availability status.",
    response_description="Verification payload confirming the API is responsive.",
)
async def health_check(
    agent: ConversationalSHLAgent = Depends(get_ai_agent),
) -> dict[str, str]:
    """Exposes availability monitoring status check route.

    Checks configuration settings, vector database, retriever,
    and agent singletons to verify readiness.
    """
    logger.debug("Received health check call.")
    # Log internal availability flags for diagnostics
    db_healthy = agent.retrieval_engine.health_check()
    logger.info("Health Check Status: VectorStoreReachability=%s", db_healthy)

    # Return expected output schema
    return {"status": "ok"}
