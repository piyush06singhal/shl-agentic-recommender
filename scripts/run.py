"""FastAPI application production runner script."""

import os
import sys
import uvicorn

# Append root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.configs.settings import get_settings


def start_server() -> None:
    """Launches Uvicorn ASGI server instance mapping global settings properties."""
    settings = get_settings()
    
    # Configure production binding params
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"Starting API server on {host}:{port} using {settings.model_name}...")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,  # False for production entrypoint
        workers=1,
    )


if __name__ == "__main__":
    start_server()
