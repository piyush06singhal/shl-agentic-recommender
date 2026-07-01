"""Main application entrypoint configuring the FastAPI server, lifespans, and global exception handlers."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agent.agent import ConversationalSHLAgent
from app.api.exceptions import register_exception_handlers
from app.api.middleware import register_middlewares
from app.api.routes import router as api_router
from app.catalog.manager import CatalogManager
from app.configs.constants import API_PREFIX
from app.configs.logging import setup_logging
from app.configs.settings import get_settings as load_initial_settings
from app.llm.service import LLMService
from app.retriever.engine import RetrievalEngine

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown lifecycles, initializing system components."""
    # 1. Initialize structured loggers
    setup_logging()
    logger.info("Initializing Conversational SHL Assessment Recommender API server...")

    # 2. Parse configuration settings
    settings = load_initial_settings()
    app.state.settings = settings
    logger.info(
        "Settings parsed. LLM Model: %s, Threshold: %.2f",
        settings.model_name,
        settings.similarity_threshold,
    )

    # 3. Load catalog database
    catalog_manager = CatalogManager()
    app.state.catalog_manager = catalog_manager
    logger.info("Catalog database loaded into memory successfully.")

    # 4. Connect Vector Database and Retrieval Engine
    retrieval_engine = RetrievalEngine()
    if retrieval_engine.health_check():
        logger.info("Vector database health check succeeded.")
    else:
        logger.error("Vector database health check failed.")
    app.state.retrieval_engine = retrieval_engine

    # 5. Initialize LLM Service
    llm_service = LLMService()
    app.state.llm_service = llm_service
    logger.info("LLM integration layer initialized.")

    # 6. Initialize Conversational AI Agent Core
    ai_agent = ConversationalSHLAgent(
        retrieval_engine=retrieval_engine,
        llm_service=llm_service,
    )
    app.state.ai_agent = ai_agent
    logger.info("Conversational SHL Agent initialized.")

    yield

    # 7. Tearing down application resources on shutdown
    logger.info("Tearing down application processes...")
    try:
        app.state.llm_service.shutdown()
        logger.info("LLM connection resources shut down.")
    except Exception as e:
        logger.error("Error shutting down LLM resources: %s", e)

    try:
        app.state.retrieval_engine.shutdown()
        logger.info("Retrieval database connections closed.")
    except Exception as e:
        logger.error("Error shutting down Retrieval database resources: %s", e)

    logger.info("API server processes teardown complete.")


app = FastAPI(
    title="Conversational SHL Assessment Recommender API",
    description="Stateless conversational TA helper to discover SHL assessments.",
    version="1.0.0",
    lifespan=lifespan,
)

# Register global middlewares (CORS, Request Timings, Correlation IDs)
register_middlewares(app)

# Register exception handlers (centralized JSON mapping)
register_exception_handlers(app)

# Register endpoint routers
app.include_router(api_router, prefix=API_PREFIX)
app.include_router(api_router)  # Fallback mappings for clean routes without prefix
