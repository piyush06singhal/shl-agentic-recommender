"""RetrievalEngine — public façade orchestrating the complete hybrid retrieval pipeline."""

import logging
import time
from typing import Any

from app.configs.settings import get_settings
from app.retriever.cache import RetrievalCache
from app.retriever.context_builder import ContextBuilder
from app.retriever.embeddings import BaseEmbeddingProvider, get_embedding_provider
from app.retriever.filters import CandidateFilter
from app.retriever.keyword_matcher import KeywordMatcher
from app.retriever.metadata_filter import MetadataFilterBuilder
from app.retriever.models import (
    MetadataFilters,
    RetrievalResult,
    RetrievedCandidate,
    SearchQuery,
)
from app.retriever.query_builder import QueryBuilder
from app.retriever.ranker import CandidateRanker
from app.retriever.reranker import Reranker
from app.retriever.search import SemanticSearch
from app.retriever.statistics import RetrievalStatisticsCollector
from app.retriever.vector_store import VectorStoreWrapper

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """Orchestrates the complete hybrid retrieval pipeline.

    Pipeline:
        retrieve() → QueryBuilder → SemanticSearch → KeywordMatcher
                   → CandidateFilter → CandidateRanker.merge → Reranker
                   → CandidateRanker.top_k → ContextBuilder → RetrievalResult

    Public methods:
        retrieve()                 — full hybrid pipeline
        retrieve_by_name()         — exact name lookup (bypasses semantic search)
        retrieve_by_url()          — exact URL lookup
        retrieve_for_comparison()  — multi-name exact batch lookup
        health_check()             — vector DB connectivity check
        statistics()               — aggregated stats report dict
    """

    def __init__(
        self,
        vector_store: VectorStoreWrapper | None = None,
        embedding_provider: BaseEmbeddingProvider | None = None,
        cache: RetrievalCache | None = None,
    ) -> None:
        settings = get_settings()
        self.settings = settings
        self.vector_store = vector_store or VectorStoreWrapper()
        self.embedding_provider = embedding_provider or get_embedding_provider()

        self._query_builder = QueryBuilder()
        self._semantic_search = SemanticSearch(self.vector_store, self.embedding_provider)
        self._keyword_matcher = KeywordMatcher()
        self._filter_builder = MetadataFilterBuilder()
        self._candidate_filter = CandidateFilter()
        self._reranker = Reranker()
        self._ranker = CandidateRanker()
        self._context_builder = ContextBuilder()
        self._stats_collector = RetrievalStatisticsCollector()
        self._cache = cache or RetrievalCache(
            max_size=settings.cache_max_size,
            ttl_seconds=settings.cache_ttl_seconds,
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def retrieve(
        self,
        query_text: str,
        filters: MetadataFilters | None = None,
        top_k: int | None = None,
    ) -> RetrievalResult:
        """Executes the full hybrid retrieval pipeline.

        Args:
            query_text: Raw user query or conversation context.
            filters: Optional metadata constraints.
            top_k: Maximum candidates to return (hard cap: 10).

        Returns:
            A RetrievalResult containing ranked candidates and LLM context.
        """
        start_time = time.monotonic()
        active_filters = filters or MetadataFilters()

        # 1. Build normalized search query
        query = self._query_builder.build(query_text, active_filters, top_k)

        logger.info(
            "RetrievalEngine.retrieve(): query='%s' | filters=%s | top_k=%d",
            query.semantic_query[:80],
            active_filters.model_dump(exclude_none=True, exclude_defaults=True),
            query.top_k,
        )

        # 2. Check cache
        cached = self._cache.get(query)
        if cached is not None:
            cached_result = cached.model_copy(
                update={"cache_hit": True, "latency_ms": _elapsed_ms(start_time)}
            )
            self._record_stats(cached_result, active_filters, cache_hit=True)
            return cached_result

        errors: list[str] = []

        # 3. Semantic search (over-fetch to allow post-filtering)
        over_fetch = min(query.top_k * 3, 30)
        try:
            candidates = self._semantic_search.search(
                query_text=query.semantic_query,
                filters=active_filters,
                n_results=over_fetch,
                similarity_threshold=query.similarity_threshold,
            )
        except Exception as e:
            logger.error("RetrievalEngine: Semantic search failed: %s", e)
            errors.append(f"Semantic search error: {e}")
            candidates = []

        # 4. Attach metadata scores from filter builder
        scored_candidates: list[RetrievedCandidate] = []
        for c in candidates:
            meta_score = self._filter_builder.compute_metadata_score(
                active_filters,
                {
                    "job_family": ", ".join(c.job_family),
                    "candidate_level": ", ".join(c.target_level),
                    "languages": ", ".join(c.languages),
                    "skills": ", ".join(c.skills),
                    "competencies": ", ".join(c.competencies),
                    "duration": c.duration_mins,
                    "remote_testing": c.remote_testing,
                },
            )
            scored_candidates.append(c.model_copy(update={"metadata_score": meta_score}))

        # 5. Keyword scoring
        scored_candidates = self._keyword_matcher.score_all(scored_candidates, query.semantic_query)

        # 6. Post-filter: apply strict constraints soft-mode to avoid empty results
        filtered = self._candidate_filter.apply_soft(scored_candidates, active_filters)

        # 7. Rerank
        reranked = self._reranker.rerank(filtered, active_filters)

        # 8. Top-K with deduplication
        top_candidates = self._ranker.top_k(reranked, k=query.top_k)

        # 9. Build LLM context
        context_blocks, context_text = self._context_builder.build(top_candidates)

        # 10. Assemble result
        latency_ms = _elapsed_ms(start_time)
        result = RetrievalResult(
            query=query,
            candidates=top_candidates,
            context_blocks=context_blocks,
            context_text=context_text,
            total_candidates=len(scored_candidates),
            cache_hit=False,
            latency_ms=round(latency_ms, 2),
            errors=errors,
        )

        # 11. Cache and record stats
        self._cache.set(query, result)
        self._record_stats(result, active_filters, cache_hit=False)

        logger.info(
            "RetrievalEngine: Returned %d candidates in %.1fms (total_pool=%d).",
            len(top_candidates),
            latency_ms,
            len(scored_candidates),
        )
        return result

    def retrieve_by_name(self, name: str) -> RetrievalResult:
        """Exact name lookup — bypasses semantic search entirely.

        Args:
            name: Official assessment name (case-insensitive).

        Returns:
            RetrievalResult with the matching assessment if found.
        """
        logger.info("RetrievalEngine.retrieve_by_name(): '%s'", name)
        start_time = time.monotonic()

        candidate = self._exact_name_lookup(name)
        candidates = [candidate] if candidate else []

        if not candidates:
            logger.warning("RetrievalEngine: No assessment found with name='%s'.", name)

        context_blocks, context_text = self._context_builder.build(candidates)
        query = SearchQuery(raw_text=name, semantic_query=name)

        return RetrievalResult(
            query=query,
            candidates=candidates,
            context_blocks=context_blocks,
            context_text=context_text,
            total_candidates=len(candidates),
            cache_hit=False,
            latency_ms=round(_elapsed_ms(start_time), 2),
        )

    def retrieve_by_url(self, url: str) -> RetrievalResult:
        """Exact URL lookup — bypasses semantic search entirely.

        Args:
            url: Official SHL assessment product URL.

        Returns:
            RetrievalResult with the matching assessment if found.
        """
        logger.info("RetrievalEngine.retrieve_by_url(): '%s'", url)
        start_time = time.monotonic()

        candidate = self._exact_url_lookup(url)
        candidates = [candidate] if candidate else []

        if not candidates:
            logger.warning("RetrievalEngine: No assessment found with url='%s'.", url)

        context_blocks, context_text = self._context_builder.build(candidates)
        query = SearchQuery(raw_text=url, semantic_query=url)

        return RetrievalResult(
            query=query,
            candidates=candidates,
            context_blocks=context_blocks,
            context_text=context_text,
            total_candidates=len(candidates),
            cache_hit=False,
            latency_ms=round(_elapsed_ms(start_time), 2),
        )

    def retrieve_for_comparison(self, names: list[str]) -> RetrievalResult:
        """Batch exact-name lookup for assessment comparison requests.

        Bypasses semantic search — looks up each name exactly in stored metadata.
        Used when user requests: "Compare OPQ and Verify G+".

        Args:
            names: List of official assessment names.

        Returns:
            RetrievalResult with all matched assessments for side-by-side comparison.
        """
        logger.info("RetrievalEngine.retrieve_for_comparison(): %s", names)
        start_time = time.monotonic()

        candidates: list[RetrievedCandidate] = []
        for name in names:
            candidate = self._exact_name_lookup(name)
            if candidate:
                candidates.append(candidate.model_copy(update={"rank": len(candidates) + 1}))
            else:
                logger.warning("RetrievalEngine: Assessment not found for comparison: '%s'.", name)

        query_text = f"Compare {' and '.join(names)}"
        query = SearchQuery(raw_text=query_text, semantic_query=query_text)

        context_blocks, context_text = self._context_builder.build_comparison_block(candidates), ""
        if candidates:
            _, context_text = self._context_builder.build(candidates)

        return RetrievalResult(
            query=query,
            candidates=candidates,
            context_blocks=[context_blocks] if isinstance(context_blocks, str) else context_blocks,
            context_text=context_text,
            total_candidates=len(candidates),
            cache_hit=False,
            latency_ms=round(_elapsed_ms(start_time), 2),
        )

    def health_check(self) -> bool:
        """Checks vector database connectivity.

        Returns:
            True if ChromaDB client is healthy.
        """
        is_healthy = self.vector_store.health_check()
        if not is_healthy:
            logger.error("RetrievalEngine: Vector DB health check FAILED.")
        return is_healthy

    def statistics(self) -> dict[str, Any]:
        """Returns aggregated retrieval statistics.

        Returns:
            Dict containing retrieval quality and performance metrics.
        """
        stats = self._stats_collector.compile()
        cache_stats = self._cache.stats()
        return {
            "retrieval": stats.model_dump(),
            "cache": cache_stats,
        }

    def save_statistics(self) -> None:
        """Persists retrieval statistics report to the configured path."""
        self._stats_collector.save(self.settings.retrieval_stats_path)

    def shutdown(self) -> None:
        """Graceful teardown: saves stats and closes the vector store."""
        self.save_statistics()
        self.vector_store.close()

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _exact_name_lookup(self, name: str) -> RetrievedCandidate | None:
        """Looks up an assessment by exact name match in stored metadata.

        Args:
            name: Case-insensitive assessment name.

        Returns:
            Matched RetrievedCandidate or None.
        """
        try:
            all_records = self.vector_store.get_all_records()
            ids = all_records.get("ids", []) or []
            metadatas = all_records.get("metadatas", []) or []

            for rid, meta in zip(ids, metadatas, strict=False):
                if meta and str(meta.get("assessment_name", "")).lower() == name.lower():
                    return _meta_to_candidate(rid, meta, rank=1)
        except Exception as e:
            logger.error("RetrievalEngine: Name lookup failed: %s", e)
        return None

    def _exact_url_lookup(self, url: str) -> RetrievedCandidate | None:
        """Looks up an assessment by exact URL match in stored metadata.

        Args:
            url: The assessment product URL.

        Returns:
            Matched RetrievedCandidate or None.
        """
        try:
            all_records = self.vector_store.get_all_records()
            ids = all_records.get("ids", []) or []
            metadatas = all_records.get("metadatas", []) or []

            for rid, meta in zip(ids, metadatas, strict=False):
                if meta and str(meta.get("url", "")).lower() == url.lower():
                    return _meta_to_candidate(rid, meta, rank=1)
        except Exception as e:
            logger.error("RetrievalEngine: URL lookup failed: %s", e)
        return None

    def _record_stats(
        self,
        result: RetrievalResult,
        filters: MetadataFilters,
        cache_hit: bool,
    ) -> None:
        """Records a query result into the statistics collector.

        Args:
            result: The retrieval result to record.
            filters: Applied metadata filters.
            cache_hit: Whether this result was served from cache.
        """
        avg_sem = (
            sum(c.semantic_score for c in result.candidates) / len(result.candidates)
            if result.candidates
            else 0.0
        )
        self._stats_collector.record(
            latency_ms=result.latency_ms,
            cache_hit=cache_hit,
            candidates_returned=len(result.candidates),
            avg_semantic_score=avg_sem,
            queried_skills=filters.skills,
            queried_job_families=filters.job_family,
            has_filters=not filters.is_empty(),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _elapsed_ms(start: float) -> float:
    """Returns elapsed milliseconds since start timestamp.

    Args:
        start: monotonic start timestamp in seconds.

    Returns:
        Elapsed time in milliseconds.
    """
    return (time.monotonic() - start) * 1000.0


def _parse_list_field(value: Any) -> list[str]:
    """Parses comma-separated string metadata back into a list.

    Args:
        value: Stored metadata value.

    Returns:
        Parsed list of strings.
    """
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _meta_to_candidate(
    rid: str,
    meta: dict[str, Any],
    rank: int = 1,
    semantic_score: float = 1.0,
) -> RetrievedCandidate:
    """Converts a raw ChromaDB metadata dict into a RetrievedCandidate.

    Args:
        rid: ChromaDB record ID.
        meta: Stored metadata dictionary.
        rank: Assigned rank position.
        semantic_score: Score to assign (default 1.0 for exact lookups).

    Returns:
        A populated RetrievedCandidate.
    """
    return RetrievedCandidate(
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
        semantic_score=semantic_score,
        keyword_score=0.0,
        metadata_score=1.0,
        composite_score=1.0,
        rank=rank,
    )
