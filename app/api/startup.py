"""App startup lifecycle triggers, establishing connections and engines."""

import logging

from fastapi import FastAPI

from app.agent.agent import ConversationalSHLAgent
from app.catalog.manager import CatalogManager
from app.configs.settings import get_settings
from app.llm.service import LLMService
from app.retriever.engine import RetrievalEngine

logger = logging.getLogger(__name__)


def setup_startup_events(app: FastAPI) -> None:
    """Configures application startup lifespan callbacks, loading DBs and catalog singletons.

    Args:
        app: FastAPI application instance.
    """

    @app.on_event("startup")
    def run_startup() -> None:
        logger.info("Starting API server startup lifecycle...")

        # 1. Load settings
        settings = get_settings()
        app.state.settings = settings
        logger.info("Settings loaded successfully.")

        # 2. Initialize Catalog Manager
        catalog_manager = CatalogManager()
        app.state.catalog_manager = catalog_manager
        logger.info("Catalog Manager initialized.")

        # 3. Initialize Retrieval Engine
        retrieval_engine = RetrievalEngine()
        # Verify db is reachable via health ping
        if retrieval_engine.health_check():
            logger.info("Vector Database ping check succeeded.")
        else:
            logger.error("Vector Database ping check failed on startup.")
        app.state.retrieval_engine = retrieval_engine

        # 4. Initialize LLM Service
        llm_service = LLMService()
        app.state.llm_service = llm_service
        logger.info("LLM service client initialized.")

        # 5. Initialize Conversational SHL Agent
        ai_agent = ConversationalSHLAgent(
            retrieval_engine=retrieval_engine,
        )
        app.state.ai_agent = ai_agent
        logger.info("Conversational SHL Agent initialized.")

        logger.info("API server startup lifecycle completed successfully.")
