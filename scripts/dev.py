"""FastAPI application local development runner script with auto-reload configurations."""

import os
import sys
import uvicorn

# Append root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def start_dev_server() -> None:
    """Launches local dev uvicorn listener with directory watcher properties."""
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"Launching local Development Server on {host}:{port} with auto-reload...")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,  # Enables hot-reloading for code edits
        log_level="debug",
    )


if __name__ == "__main__":
    start_dev_server()
