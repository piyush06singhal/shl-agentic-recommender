"""Statistics module aggregating ChromaDB vector statistics reports."""

import logging
from datetime import UTC, datetime

from app.retriever.models import IndexingResult, RetrievalStatistics, VectorStats
from app.retriever.vector_store import VectorStoreWrapper

logger = logging.getLogger(__name__)


class IndexStatisticsGenerator:
    """Compiles statistics reports summarizing vector database and indexing characteristics."""

    def compile_statistics(
        self,
        vector_store: VectorStoreWrapper,
        embedding_model: str,
        embedding_dimension: int,
        indexing_result: IndexingResult,
    ) -> VectorStats:
        """Gathers collection details to build vector statistics metrics.

        Args:
            vector_store: The active persistent VectorStoreWrapper.
            embedding_model: The name identifier of the embedding model.
            embedding_dimension: Dimensionality length of float coordinate arrays.
            indexing_result: Details of the last indexing execution run.

        Returns:
            A compiled VectorStats object containing collection metrics.
        """
        logger.info("Statistics: Generating vector index statistics report...")

        total_vectors = vector_store.count()
        db_records = vector_store.get_all_records()
        documents = db_records.get("documents", []) or []

        # Calculate average character length of documents
        avg_doc_len = 0.0
        if documents:
            total_chars = sum(len(str(doc)) for doc in documents if doc)
            avg_doc_len = float(total_chars) / len(documents)

        return VectorStats(
            total_vectors=total_vectors,
            embedding_model=embedding_model,
            embedding_dimensions=embedding_dimension,
            collection_name=vector_store.collection_name,
            generation_timestamp=datetime.now(UTC).isoformat(),
            average_document_length=round(avg_doc_len, 2),
            failed_embeddings=indexing_result.failed,
            skipped_embeddings=indexing_result.skipped,
            updated_embeddings=indexing_result.updated,
        )


# ---------------------------------------------------------------------------
# Phase 4 — Retrieval Statistics Collector
# ---------------------------------------------------------------------------


class RetrievalStatisticsCollector:
    """Accumulates retrieval performance metrics and writes retrieval_statistics.json."""

    def __init__(self) -> None:
        self._total_queries: int = 0
        self._cache_hits: int = 0
        self._latencies_ms: list[float] = []
        self._candidates_returned: list[int] = []
        self._semantic_scores: list[float] = []
        self._skill_counter: dict[str, int] = {}
        self._job_family_counter: dict[str, int] = {}
        self._queries_with_filters: int = 0

    def record(
        self,
        latency_ms: float,
        cache_hit: bool,
        candidates_returned: int,
        avg_semantic_score: float,
        queried_skills: list[str] | None = None,
        queried_job_families: list[str] | None = None,
        has_filters: bool = False,
    ) -> None:
        """Records metrics for a single retrieval query.

        Args:
            latency_ms: End-to-end retrieval latency in milliseconds.
            cache_hit: True if this query was served from cache.
            candidates_returned: Number of candidates returned.
            avg_semantic_score: Mean semantic similarity of returned candidates.
            queried_skills: Skills mentioned in the query filters.
            queried_job_families: Job families mentioned in the query filters.
            has_filters: True if metadata filters were applied.
        """
        self._total_queries += 1
        if cache_hit:
            self._cache_hits += 1
        self._latencies_ms.append(latency_ms)
        self._candidates_returned.append(candidates_returned)
        if avg_semantic_score > 0:
            self._semantic_scores.append(avg_semantic_score)
        if has_filters:
            self._queries_with_filters += 1

        for skill in (queried_skills or []):
            self._skill_counter[skill] = self._skill_counter.get(skill, 0) + 1
        for jf in (queried_job_families or []):
            self._job_family_counter[jf] = self._job_family_counter.get(jf, 0) + 1

    def compile(self) -> RetrievalStatistics:
        """Compiles accumulated metrics into a RetrievalStatistics report.

        Returns:
            A RetrievalStatistics model.
        """
        total = self._total_queries or 1
        avg_latency = sum(self._latencies_ms) / len(self._latencies_ms) if self._latencies_ms else 0.0
        avg_candidates = (
            sum(self._candidates_returned) / len(self._candidates_returned)
            if self._candidates_returned
            else 0.0
        )
        avg_semantic = sum(self._semantic_scores) / len(self._semantic_scores) if self._semantic_scores else 0.0

        top_skills = sorted(self._skill_counter, key=lambda k: self._skill_counter[k], reverse=True)[:10]
        top_jf = sorted(self._job_family_counter, key=lambda k: self._job_family_counter[k], reverse=True)[:10]

        return RetrievalStatistics(
            total_queries=self._total_queries,
            cache_hits=self._cache_hits,
            cache_misses=self._total_queries - self._cache_hits,
            average_latency_ms=round(avg_latency, 2),
            average_candidates_returned=round(avg_candidates, 2),
            average_semantic_score=round(avg_semantic, 4),
            top_searched_skills=top_skills,
            top_searched_job_families=top_jf,
            metadata_filter_usage_rate=round(self._queries_with_filters / total, 4),
            generation_timestamp=datetime.now(UTC).isoformat(),
        )

    def save(self, path: str) -> None:
        """Saves the compiled statistics report to a JSON file.

        Args:
            path: Absolute or relative file path to write.
        """
        import json
        import os

        stats = self.compile()
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats.model_dump(), f, indent=2, ensure_ascii=False)
        logger.info("RetrievalStatistics: Report saved to %s.", path)

