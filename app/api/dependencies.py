"""FastAPI dependencies provider configurations."""

import logging
from typing import cast

from fastapi import Request

from app.agent.agent import ConversationalSHLAgent
from app.agent.conversation import ConversationEngine
from app.catalog.manager import CatalogManager
from app.configs.settings import Settings
from app.llm.service import LLMService
from app.retriever.engine import RetrievalEngine

logger = logging.getLogger(__name__)


def get_settings(request: Request) -> Settings:
    """Retrieves settings configuration singleton from app state.

    Args:
        request: FastAPI HTTP request context.

    Returns:
        The Settings singleton instance.
    """
    return cast(Settings, request.app.state.settings)


def get_catalog_manager(request: Request) -> CatalogManager:
    """Injects CatalogManager caching services from app state.

    Args:
        request: FastAPI HTTP request context.

    Returns:
        The CatalogManager instance.
    """
    return cast(CatalogManager, request.app.state.catalog_manager)


def get_retrieval_engine(request: Request) -> RetrievalEngine:
    """Injects RetrievalEngine façade from app state.

    Args:
        request: FastAPI HTTP request context.

    Returns:
        The RetrievalEngine instance.
    """
    return cast(RetrievalEngine, request.app.state.retrieval_engine)


def get_conversation_engine(request: Request) -> ConversationEngine:
    """Injects ConversationEngine façade from app state.

    Args:
        request: FastAPI HTTP request context.

    Returns:
        The ConversationEngine instance.
    """
    return cast(ConversationEngine, request.app.state.conversation_engine)


def get_llm_service(request: Request) -> LLMService:
    """Injects LLMService wrapper from app state.

    Args:
        request: FastAPI HTTP request context.

    Returns:
        The LLMService instance.
    """
    return cast(LLMService, request.app.state.llm_service)


def get_ai_agent(request: Request) -> ConversationalSHLAgent:
    """Injects ConversationalSHLAgent orchestrator from app state.

    Args:
        request: FastAPI HTTP request context.

    Returns:
        The ConversationalSHLAgent instance.
    """
    return cast(ConversationalSHLAgent, request.app.state.ai_agent)
