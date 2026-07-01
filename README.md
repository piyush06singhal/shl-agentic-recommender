# Conversational SHL Assessment Recommender

Conversational AI Agent system designed to help recruiters discover suitable candidate assessments from the official SHL Individual Test Solutions catalog. The assistant functions as a talent acquisition hiring consultant, probing for criteria, evaluating constraints, and performing direct test comparisons.

---

## Architecture Summary

The application is built on a stateless FastAPI backend using a Retrieval-Augmented Generation (RAG) pattern. It reconstructs requirements context dynamically from stateless incoming histories using a "latest value wins" method.

```
                  +----------------------------------+
                  |           User Client            |
                  +----------------------------------+
                                   │
                           POST /chat Payload
                                   ▼
                  +----------------------------------+
                  |            API Layer             |
                  +----------------------------------+
                                   │
                                   ▼
                  +----------------------------------+
                  |       Conversation Parser        |
                  +----------------------------------+
                                   │
                                   ▼
                  +----------------------------------+
                  |          Intent Detector         |
                  +----------------------------------+
                                   │
                                   ▼
                  +----------------------------------+
                  |          Context Builder         |
                  +----------------------------------+
                                   │
                                   ▼
                  +----------------------------------+
                  |          Decision Engine         |
                  +----------------------------------+
                                  / \
                     Complete?  No   Yes
                               /       \
                              ▼         ▼
             +------------------+     +------------------+
             |   LLM Service    |     |    Retriever     |
             |  (Clarification) |     +------------------+
             +------------------+               │
                      │                         ▼
                      │               +------------------+
                      │               | Catalog Manager  |
                      │               +------------------+
                      │                         │
                      │                         ▼
                      │               +------------------+
                      │               |   LLM Service    |
                      │               | (Recommendation) |
                      │               +------------------+
                      \                         /
                       ▼                       ▼
                  +----------------------------------+
                  |        Response Validator        |
                  +----------------------------------+
                                   │
                       Validated ChatResponse JSON
                                   ▼
                  +----------------------------------+
                  |            User Client           |
                  +----------------------------------+
```

---

## Folder Structure

The repository file layout is organized as follows:
*   `app/api/`: API router files and dependencies.
*   `app/schemas/`: Pydantic payload models.
*   `app/agent/`: Recommender core agent state controllers (turn parsers, context builders, decision engines, validators).
*   `app/retriever/`: Database search query wrappers.
*   `app/catalog/`: Ingestion managers and static catalog file locations.
*   `app/llm/`: LLM provider integration engines and prompt template manager.
*   `app/configs/`: Settings and rotating log formats.
*   `app/services/`: Base helpers, string formatters, and custom exception files.
*   `tests/`: Unit and integration Pytest suites.
*   `scripts/`: Command execution scripts.

---

## Installation & Setup

### Prerequisites
*   Python 3.12+
*   Docker (Optional, for containerized execution)

### Environment Configurations
1. Copy the `.env.example` template:
   ```bash
   cp .env.example .env
   ```
2. Populate the parameters in `.env` with your credentials:
   ```env
   OPENAI_API_KEY=your-api-key
   ```

---

## Running Locally

### Using a Local Environment
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Boot the API server:
   ```bash
   python scripts/run.py
   ```
   The service will launch at `http://127.0.0.1:8000`.

### Using Docker & Compose
1. Build and run the service containers:
   ```bash
   docker-compose up --build
   ```

---

## Testing

Execute standard Pytest suites:
```bash
pytest
```

---

## Development Workflow

A Makefile is provided to automate workflow steps:
*   `make install`: Installs dependencies.
*   `make lint`: Audits formatting and types with Ruff and MyPy.
*   `make format`: Formats code with Black and isort.
*   `make test`: Runs pytest suites.
*   `make run`: Launches the FastAPI server locally.
*   `make clean`: Cleans compiler caches.
