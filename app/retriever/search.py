"""Semantic search module executing vector similarity queries against ChromaDB."""

import logging
from typing import Any, cast

from app.retriever.embeddings import BaseEmbeddingProvider
from app.retriever.metadata_filter import MetadataFilterBuilder
from app.retriever.models import MetadataFilters, RetrievedCandidate
from app.retriever.vector_store import VectorStoreWrapper

logger = logging.getLogger(__name__)


def _parse_list_field(value: Any) -> list[str]:
    """Parses a comma-separated string back into a list.

    Args:
        value: The stored metadata value (str or other primitive).

    Returns:
        A list of stripped string items.
    """
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v]
    return [item.strip() for item in str(value).split(",") if item.strip()]


class SemanticSearch:
    """Executes vector similarity queries against the ChromaDB collection."""

    def __init__(
        self,
        vector_store: VectorStoreWrapper,
        embedding_provider: BaseEmbeddingProvider,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.filter_builder = MetadataFilterBuilder()

    def search(
        self,
        query_text: str,
        filters: MetadataFilters | None = None,
        n_results: int = 20,
        similarity_threshold: float = 0.0,
    ) -> list[RetrievedCandidate]:
        """Embeds query text and queries ChromaDB for nearest neighbours.

        Args:
            query_text: Normalized semantic query string.
            filters: Optional metadata pre-filters.
            n_results: Number of candidates to request from ChromaDB.
            similarity_threshold: Minimum similarity score to include (0 = no cutoff).

        Returns:
            List of RetrievedCandidate objects with semantic scores set.
        """
        active_filters = filters or MetadataFilters()

        # Build ChromaDB where clause from filters
        where_clause = self.filter_builder.build_where_clause(active_filters)

        # Embed the query
        try:
            query_embeddings = self.embedding_provider.generate_embeddings([query_text])
        except Exception as e:
            logger.error("SemanticSearch: Embedding generation failed: %s", e)
            return []

        # Execute ChromaDB query
        try:
            logger.info(
                "SemanticSearch: Querying ChromaDB (n_results=%d, where=%s)...",
                n_results,
                where_clause,
            )
            raw_results = self.vector_store.collection.query(
                query_embeddings=query_embeddings,  # type: ignore
                n_results=min(n_results, self.vector_store.count() or 1),
                where=cast(Any, where_clause) if where_clause else None,
                include=cast(Any, ["metadatas", "documents", "distances"]),
            )
        except Exception as e:
            logger.error("SemanticSearch: ChromaDB query failed: %s", e)
            return []

        # Parse raw ChromaDB results
        return self._parse_query_results(raw_results, similarity_threshold)

    def _parse_query_results(
        self,
        raw_results: Any,
        similarity_threshold: float,
    ) -> list[RetrievedCandidate]:
        """Parses raw ChromaDB QueryResult into scored RetrievedCandidate objects.

        Args:
            raw_results: Raw ChromaDB query result dict.
            similarity_threshold: Minimum similarity to include.

        Returns:
            List of parsed and scored candidates.
        """
        candidates: list[RetrievedCandidate] = []

        ids_batch = (raw_results.get("ids") or [[]])[0]
        metadatas_batch = (raw_results.get("metadatas") or [[]])[0]
        distances_batch = (raw_results.get("distances") or [[]])[0]

        for rid, meta, distance in zip(ids_batch, metadatas_batch, distances_batch, strict=False):
            if meta is None:
                continue

            # ChromaDB returns L2 or cosine distance — convert to similarity
            # For cosine distance: similarity = 1 - distance (clamped to [0, 1])
            similarity = max(0.0, min(1.0, 1.0 - float(distance)))

            if similarity < similarity_threshold:
                logger.debug(
                    "SemanticSearch: Candidate %s dropped (similarity=%.3f < threshold=%.3f)",
                    rid,
                    similarity,
                    similarity_threshold,
                )
                continue

            try:
                candidate = RetrievedCandidate(
                    assessment_id=str(meta.get("assessment_id", rid)),
                    name=str(meta.get("assessment_name", "")),
                    url=str(meta.get("url", "")),
                    test_type=str(meta.get("assessment_type", "")),
                    description=str(meta.get("description", "")),
                    job_family=_parse_list_field(meta.get("job_family")),
                    target_level=_parse_list_field(meta.get("candidate_level")),
                    duration_mins=int(meta.get("duration", 0)),
                    languages=_parse_list_field(meta.get("languages")),
                    skills=_parse_list_field(meta.get("skills")),
                    competencies=_parse_list_field(meta.get("competencies")),
                    remote_testing=bool(meta.get("remote_testing", True)),
                    adaptive=bool(meta.get("adaptive", False)),
                    category=str(meta.get("category", "Standard")),
                    semantic_score=round(similarity, 4),
                )
                candidates.append(candidate)
            except Exception as e:
                logger.warning("SemanticSearch: Failed parsing candidate %s: %s", rid, e)

        logger.info(
            "SemanticSearch: Retrieved %d candidates (threshold=%.2f).",
            len(candidates),
            similarity_threshold,
        )
        return candidates
