# Changelog

All notable changes to the Conversational SHL Assessment Recommender project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-07-01

### Added
- **Project Foundation**: Core FastAPI shell with middlewares, error routing, CORS, and request lifespan.
- **Data Scraping Pipeline**: BS4 crawler downloading the SHL assessment profiles, cleaning inconsistent parameters, and normalising output records to `catalog.json`.
- **Vector Storage Pipeline**: ChromaDB persistence setup with text-embeddings generation, incremental delta indexing, and validation verification checks.
- **Retrieval Engine**: Multi-dimensional search scorer combining exact metadata filters, word frequency matches, and semantic embeddings similarity queries.
- **Decision Engine**: Rule-based intent and action dispatcher orchestrating queries, clarifications, greetings, help guides, out-of-scope refusals, and comparison blocks.
- **Output Validator**: Response parser filtering output links, capping recommends to 10 entries, and preventing prompt leaks.
- **Fallback Integration**: Graceful templates fallback engine maintaining system availability under live API timeout or quota exceptions.
- **Deployment Setups**: Docker configurations, GitHub CI workflows, Render build specifications, and Railway schemas.
- **Testing Coverage**: Automated Pytest suites covering API routes, prompt engines, retrieval calculations, and agent intents.

---
## [0.1.0] - 2026-06-30
- Initial workspace project initialization and setup.
