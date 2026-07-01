"""App shutdown lifecycle events, closing connections and cleaning resources."""

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def setup_shutdown_events(app: FastAPI) -> None:
    """Configures application shutdown hook handler, closing active sockets and saving stats.

    Args:
        app: FastAPI application instance.
    """

    @app.on_event("shutdown")
    def run_shutdown() -> None:
        logger.info("Starting API server shutdown lifecycle...")

        # 1. Shutdown LLM Service client
        if hasattr(app.state, "llm_service"):
            try:
                app.state.llm_service.shutdown()
                logger.info("LLM service connection closed.")
            except Exception as e:
                logger.error("Error during LLM Service shutdown: %s", e)

        # 2. Shutdown Retrieval Engine
        if hasattr(app.state, "retrieval_engine"):
            try:
                app.state.retrieval_engine.shutdown()
                logger.info("Retrieval Engine connection closed.")
            except Exception as e:
                logger.error("Error during Retrieval Engine shutdown: %s", e)

        logger.info("API server shutdown lifecycle completed successfully.")
