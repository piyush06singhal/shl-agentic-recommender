"""Tests for the Phase 4 hybrid retrieval engine modules."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.retriever.cache import RetrievalCache
from app.retriever.context_builder import ContextBuilder
from app.retriever.engine import RetrievalEngine
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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_candidate() -> RetrievedCandidate:
    """A sample candidate for testing."""
    return RetrievedCandidate(
        assessment_id="aaaa-1111",
        name="Verify G+",
        url="https://www.shl.com/verify-g-plus",
        test_type="Cognitive",
        description="Measures general cognitive ability and reasoning skills.",
        job_family=["Technology", "Engineering"],
        target_level=["Graduate", "Professional"],
        duration_mins=36,
        languages=["English", "French", "German"],
        skills=["Reasoning", "Numerical", "Verbal"],
        competencies=["Analytical Thinking", "Problem Solving"],
        remote_testing=True,
        adaptive=True,
        category="Cognitive Ability",
        semantic_score=0.85,
        keyword_score=0.6,
        metadata_score=0.9,
        composite_score=0.8,
        rank=1,
    )


@pytest.fixture
def sample_candidate_2() -> RetrievedCandidate:
    """A second sample candidate for dedup/merge tests."""
    return RetrievedCandidate(
        assessment_id="bbbb-2222",
        name="OPQ32",
        url="https://www.shl.com/opq32",
        test_type="Personality",
        description="Measures personality traits and occupational behaviours.",
        job_family=["Sales", "Marketing"],
        target_level=["Professional", "Manager"],
        duration_mins=25,
        languages=["English"],
        skills=["Communication", "Persuasion"],
        competencies=["Influencing Others", "Teamwork"],
        remote_testing=True,
        adaptive=False,
        category="Personality",
        semantic_score=0.72,
        keyword_score=0.4,
        metadata_score=0.75,
        composite_score=0.65,
        rank=2,
    )


@pytest.fixture
def sample_query() -> SearchQuery:
    """A sample SearchQuery for cache tests."""
    return SearchQuery(
        raw_text="cognitive test for graduates",
        semantic_query="graduate entry cognitive reasoning assessment",
        filters=MetadataFilters(),
        top_k=5,
        similarity_threshold=0.0,
    )


@pytest.fixture
def sample_result(
    sample_query: SearchQuery,
    sample_candidate: RetrievedCandidate,
) -> RetrievalResult:
    """A sample RetrievalResult for cache tests."""
    return RetrievalResult(
        query=sample_query,
        candidates=[sample_candidate],
        context_blocks=["[1] Verify G+\nType: Cognitive"],
        context_text="[1] Verify G+\nType: Cognitive",
        total_candidates=1,
        cache_hit=False,
        latency_ms=42.0,
    )


# ---------------------------------------------------------------------------
# QueryBuilder tests
# ---------------------------------------------------------------------------


class TestQueryBuilder:
    """Tests for the QueryBuilder normalization pipeline."""

    def test_basic_query_build(self) -> None:
        """Builds a SearchQuery from plain text."""
        builder = QueryBuilder()
        result = builder.build("Java developer assessment")
        assert result.semantic_query
        assert "java" in result.semantic_query.lower()
        assert result.top_k <= 10

    def test_abbreviation_expansion(self) -> None:
        """Expands known abbreviations in the query."""
        builder = QueryBuilder()
        result = builder.build("sr dev for backend engineering")
        assert "senior" in result.semantic_query
        assert "developer" in result.semantic_query

    def test_filters_merged_into_query(self) -> None:
        """Filter fields are included in the semantic query."""
        builder = QueryBuilder()
        filters = MetadataFilters(
            job_family=["Technology"],
            target_level=["Graduate"],
            skills=["Python"],
        )
        result = builder.build("programming test", filters=filters)
        assert "technology" in result.semantic_query.lower() or "graduate" in result.semantic_query.lower()

    def test_top_k_hard_cap(self) -> None:
        """Enforces hard maximum of 10 for top_k."""
        builder = QueryBuilder()
        result = builder.build("test", top_k=999)
        assert result.top_k == 10

    def test_deduplication(self) -> None:
        """Duplicate tokens are removed from semantic query."""
        builder = QueryBuilder()
        result = builder.build("java java java developer developer")
        tokens = result.semantic_query.split()
        assert len(tokens) == len(set(tokens))

    def test_empty_text_produces_query(self) -> None:
        """Even empty text produces a valid SearchQuery."""
        builder = QueryBuilder()
        result = builder.build("")
        assert isinstance(result.semantic_query, str)


# ---------------------------------------------------------------------------
# MetadataFilterBuilder tests
# ---------------------------------------------------------------------------


class TestMetadataFilterBuilder:
    """Tests for ChromaDB where-clause generation."""

    def test_empty_filters_returns_none(self) -> None:
        """Empty filters produce no where clause."""
        builder = MetadataFilterBuilder()
        result = builder.build_where_clause(MetadataFilters())
        assert result is None

    def test_single_test_type_eq(self) -> None:
        """Single test_type produces $eq clause."""
        builder = MetadataFilterBuilder()
        filters = MetadataFilters(test_type=["Cognitive"])
        result = builder.build_where_clause(filters)
        assert result is not None
        assert result == {"assessment_type": {"$eq": "Cognitive"}}

    def test_multiple_test_types_in(self) -> None:
        """Multiple test_types produce $in clause."""
        builder = MetadataFilterBuilder()
        filters = MetadataFilters(test_type=["Cognitive", "Personality"])
        result = builder.build_where_clause(filters)
        assert result is not None
        assert "$in" in str(result)

    def test_duration_filter(self) -> None:
        """Max duration produces $lte clause."""
        builder = MetadataFilterBuilder()
        filters = MetadataFilters(max_duration_mins=30)
        result = builder.build_where_clause(filters)
        assert result is not None
        assert "$lte" in str(result)

    def test_combined_filters_use_and(self) -> None:
        """Multiple conditions combine with $and."""
        builder = MetadataFilterBuilder()
        filters = MetadataFilters(test_type=["Cognitive"], max_duration_mins=45)
        result = builder.build_where_clause(filters)
        assert result is not None
        assert "$and" in result

    def test_metadata_score_full_match(self, sample_candidate: RetrievedCandidate) -> None:
        """Perfect filter match produces score of 1.0."""
        builder = MetadataFilterBuilder()
        filters = MetadataFilters(
            job_family=["Technology"],
            target_level=["Graduate"],
            languages=["English"],
        )
        meta = {
            "job_family": "Technology, Engineering",
            "candidate_level": "Graduate, Professional",
            "languages": "English, French, German",
            "skills": "Reasoning",
            "competencies": "Analytical Thinking",
            "duration": 36,
        }
        score = builder.compute_metadata_score(filters, meta)
        assert score == 1.0

    def test_metadata_score_partial_match(self) -> None:
        """Partial filter match produces score < 1.0."""
        builder = MetadataFilterBuilder()
        filters = MetadataFilters(
            job_family=["Finance"],
            target_level=["Executive"],
        )
        meta = {
            "job_family": "Technology",  # mismatch
            "candidate_level": "Executive",  # match
        }
        score = builder.compute_metadata_score(filters, meta)
        assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# KeywordMatcher tests
# ---------------------------------------------------------------------------


class TestKeywordMatcher:
    """Tests for keyword relevance scoring."""

    def test_exact_name_match_boosts_score(self, sample_candidate: RetrievedCandidate) -> None:
        """Exact assessment name in query receives highest boost."""
        matcher = KeywordMatcher()
        scored = matcher.score_all([sample_candidate], "Verify G+ assessment")
        assert scored[0].keyword_score > 0.5

    def test_no_overlap_low_score(self, sample_candidate: RetrievedCandidate) -> None:
        """Completely unrelated query produces low keyword score."""
        matcher = KeywordMatcher()
        scored = matcher.score_all([sample_candidate], "accounting finance bookkeeping")
        assert scored[0].keyword_score < 0.5

    def test_skill_overlap_raises_score(self, sample_candidate: RetrievedCandidate) -> None:
        """Matching skills token increases score."""
        matcher = KeywordMatcher()
        scored = matcher.score_all([sample_candidate], "reasoning numerical verbal")
        assert scored[0].keyword_score > 0.0

    def test_all_candidates_scored(
        self,
        sample_candidate: RetrievedCandidate,
        sample_candidate_2: RetrievedCandidate,
    ) -> None:
        """All candidates in the list receive a keyword score."""
        matcher = KeywordMatcher()
        scored = matcher.score_all([sample_candidate, sample_candidate_2], "cognitive personality")
        assert all(0.0 <= c.keyword_score <= 1.0 for c in scored)

    def test_score_clamped_to_one(self, sample_candidate: RetrievedCandidate) -> None:
        """Score does not exceed 1.0 for any candidate."""
        matcher = KeywordMatcher()
        # High overlap with every field
        query = f"{sample_candidate.name} reasoning numerical verbal analytical"
        scored = matcher.score_all([sample_candidate], query)
        assert scored[0].keyword_score <= 1.0


# ---------------------------------------------------------------------------
# CandidateFilter tests
# ---------------------------------------------------------------------------


class TestCandidateFilter:
    """Tests for post-retrieval metadata filtering."""

    def test_duration_filter_removes_long_tests(
        self,
        sample_candidate: RetrievedCandidate,
    ) -> None:
        """Candidates exceeding max duration are removed."""
        cf = CandidateFilter()
        filters = MetadataFilters(max_duration_mins=30)
        result = cf.apply([sample_candidate], filters)  # duration=36 > 30
        assert len(result) == 0

    def test_duration_filter_keeps_short_tests(
        self,
        sample_candidate: RetrievedCandidate,
    ) -> None:
        """Candidates within duration limit are retained."""
        cf = CandidateFilter()
        filters = MetadataFilters(max_duration_mins=60)
        result = cf.apply([sample_candidate], filters)
        assert len(result) == 1

    def test_language_filter(
        self,
        sample_candidate: RetrievedCandidate,
        sample_candidate_2: RetrievedCandidate,
    ) -> None:
        """Language filter removes candidates without required language."""
        cf = CandidateFilter()
        filters = MetadataFilters(languages=["French"])
        result = cf.apply([sample_candidate, sample_candidate_2], filters)
        # sample_candidate has French, sample_candidate_2 does not
        assert len(result) == 1
        assert result[0].name == "Verify G+"

    def test_empty_filters_returns_all(
        self,
        sample_candidate: RetrievedCandidate,
        sample_candidate_2: RetrievedCandidate,
    ) -> None:
        """Empty filters pass all candidates through."""
        cf = CandidateFilter()
        result = cf.apply([sample_candidate, sample_candidate_2], MetadataFilters())
        assert len(result) == 2

    def test_soft_filter_penalizes_not_removes(
        self,
        sample_candidate: RetrievedCandidate,
    ) -> None:
        """Soft filter penalizes non-matching candidates instead of removing."""
        cf = CandidateFilter()
        original_score = 0.9
        candidate = sample_candidate.model_copy(update={"metadata_score": original_score})
        filters = MetadataFilters(max_duration_mins=20)  # candidate duration=36
        result = cf.apply_soft([candidate], filters)
        assert len(result) == 1
        assert result[0].metadata_score < original_score


# ---------------------------------------------------------------------------
# Reranker tests
# ---------------------------------------------------------------------------


class TestReranker:
    """Tests for deterministic priority reranker."""

    def test_higher_metadata_score_ranks_first(
        self,
        sample_candidate: RetrievedCandidate,
        sample_candidate_2: RetrievedCandidate,
    ) -> None:
        """Candidate with higher metadata score is ranked first when filters are active.

        When MetadataFilters are empty, the reranker correctly gives all candidates
        meta_s=1.0 (everyone matches). To test metadata priority, we must pass active
        filters — this exercises the branch that reads candidate.metadata_score.
        """
        reranker = Reranker()
        # high: metadata strongly matches, semantic is weaker
        high = sample_candidate.model_copy(update={"metadata_score": 1.0, "semantic_score": 0.5})
        # low: metadata barely matches, semantic is stronger
        low = sample_candidate_2.model_copy(update={"metadata_score": 0.2, "semantic_score": 0.9})
        # Pass active filters so meta_s reads from candidate.metadata_score
        active_filters = MetadataFilters(job_family=["Technology"])
        result = reranker.rerank([low, high], filters=active_filters)
        assert result[0].assessment_id == high.assessment_id

    def test_ranks_assigned_sequentially(
        self,
        sample_candidate: RetrievedCandidate,
        sample_candidate_2: RetrievedCandidate,
    ) -> None:
        """Reranker assigns sequential rank positions starting at 1."""
        reranker = Reranker()
        result = reranker.rerank([sample_candidate, sample_candidate_2])
        ranks = [c.rank for c in result]
        assert ranks == list(range(1, len(result) + 1))

    def test_empty_input_returns_empty(self) -> None:
        """Empty candidate list returns empty result."""
        reranker = Reranker()
        assert reranker.rerank([]) == []

    def test_composite_scores_attached(self, sample_candidate: RetrievedCandidate) -> None:
        """Reranker attaches non-zero composite scores to all candidates."""
        reranker = Reranker()
        result = reranker.rerank([sample_candidate])
        assert result[0].composite_score > 0.0


# ---------------------------------------------------------------------------
# CandidateRanker tests
# ---------------------------------------------------------------------------


class TestCandidateRanker:
    """Tests for top-K selection and deduplication."""

    def test_top_k_enforced(self, sample_candidate: RetrievedCandidate) -> None:
        """Top-K never exceeds the hard ceiling of 10."""
        ranker = CandidateRanker()
        candidates = [
            sample_candidate.model_copy(update={"assessment_id": f"id-{i}", "rank": i})
            for i in range(20)
        ]
        result = ranker.top_k(candidates, k=20)
        assert len(result) <= 10

    def test_deduplication_keeps_highest_score(
        self,
        sample_candidate: RetrievedCandidate,
    ) -> None:
        """Duplicate assessment_id entries are merged keeping highest composite score."""
        ranker = CandidateRanker()
        duplicate_low = sample_candidate.model_copy(update={"composite_score": 0.3})
        duplicate_high = sample_candidate.model_copy(update={"composite_score": 0.9})
        result = ranker.top_k([duplicate_low, duplicate_high], k=10)
        assert len(result) == 1
        assert result[0].composite_score == 0.9

    def test_merge_lists_deduplicates(
        self,
        sample_candidate: RetrievedCandidate,
        sample_candidate_2: RetrievedCandidate,
    ) -> None:
        """Merging two lists with overlapping IDs deduplicates correctly."""
        ranker = CandidateRanker()
        list1 = [sample_candidate]
        list2 = [sample_candidate, sample_candidate_2]
        merged = ranker.merge_candidate_lists(list1, list2)
        ids = [c.assessment_id for c in merged]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# ContextBuilder tests
# ---------------------------------------------------------------------------


class TestContextBuilder:
    """Tests for LLM context block assembly."""

    def test_build_returns_block_per_candidate(
        self,
        sample_candidate: RetrievedCandidate,
        sample_candidate_2: RetrievedCandidate,
    ) -> None:
        """One context block is generated per candidate."""
        builder = ContextBuilder()
        blocks, _ = builder.build([sample_candidate, sample_candidate_2])
        assert len(blocks) == 2

    def test_block_contains_required_fields(self, sample_candidate: RetrievedCandidate) -> None:
        """Context blocks include name, type, duration, URL, skills, levels."""
        builder = ContextBuilder()
        blocks, _ = builder.build([sample_candidate])
        block = blocks[0]
        assert "Verify G+" in block
        assert "Cognitive" in block
        assert "36 minutes" in block
        assert "https://www.shl.com/verify-g-plus" in block
        assert "Reasoning" in block
        assert "Graduate" in block

    def test_empty_candidates_returns_empty(self) -> None:
        """No candidates produces empty blocks and context."""
        builder = ContextBuilder()
        blocks, context = builder.build([])
        assert blocks == []
        assert context == ""

    def test_context_text_joins_blocks(self, sample_candidate: RetrievedCandidate) -> None:
        """Context text is a non-empty string joining blocks."""
        builder = ContextBuilder()
        blocks, context = builder.build([sample_candidate])
        assert context
        assert "Verify G+" in context


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------


class TestRetrievalCache:
    """Tests for in-memory LRU retrieval cache."""

    def test_cache_miss_on_empty(self, sample_query: SearchQuery) -> None:
        """Empty cache produces a miss."""
        cache = RetrievalCache()
        assert cache.get(sample_query) is None

    def test_cache_hit_after_set(
        self,
        sample_query: SearchQuery,
        sample_result: RetrievalResult,
    ) -> None:
        """Cache returns stored result on subsequent get."""
        cache = RetrievalCache()
        cache.set(sample_query, sample_result)
        result = cache.get(sample_query)
        assert result is not None
        assert result.total_candidates == 1

    def test_cache_expires_after_ttl(
        self,
        sample_query: SearchQuery,
        sample_result: RetrievalResult,
    ) -> None:
        """Cache entries expire after TTL."""
        cache = RetrievalCache(ttl_seconds=0.01)  # 10ms TTL
        cache.set(sample_query, sample_result)
        time.sleep(0.05)  # Wait for expiry
        assert cache.get(sample_query) is None

    def test_cache_invalidate(
        self,
        sample_query: SearchQuery,
        sample_result: RetrievalResult,
    ) -> None:
        """Invalidate removes a specific entry."""
        cache = RetrievalCache()
        cache.set(sample_query, sample_result)
        removed = cache.invalidate(sample_query)
        assert removed is True
        assert cache.get(sample_query) is None

    def test_cache_clear(
        self,
        sample_query: SearchQuery,
        sample_result: RetrievalResult,
    ) -> None:
        """Clear removes all entries."""
        cache = RetrievalCache()
        cache.set(sample_query, sample_result)
        cache.clear()
        assert cache.get(sample_query) is None

    def test_lru_eviction_at_capacity(
        self,
        sample_result: RetrievalResult,
    ) -> None:
        """Oldest entry is evicted when cache reaches max_size."""
        cache = RetrievalCache(max_size=2)
        queries = [
            SearchQuery(raw_text=f"q{i}", semantic_query=f"query {i}")
            for i in range(3)
        ]
        for q in queries[:2]:
            cache.set(q, sample_result)

        # Access q0 to make q1 the LRU
        cache.get(queries[0])

        # Insert q2 — should evict q1 (least recently used)
        cache.set(queries[2], sample_result)
        assert cache.get(queries[0]) is not None  # still in cache
        assert cache.get(queries[2]) is not None  # new entry

    def test_stats_reflect_hits_and_misses(
        self,
        sample_query: SearchQuery,
        sample_result: RetrievalResult,
    ) -> None:
        """Stats accurately track hits and misses."""
        cache = RetrievalCache()
        cache.get(sample_query)  # miss
        cache.set(sample_query, sample_result)
        cache.get(sample_query)  # hit
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


# ---------------------------------------------------------------------------
# RetrievalEngine end-to-end tests (mocked ChromaDB)
# ---------------------------------------------------------------------------


def _make_mock_vector_store(candidates_meta: list[dict[str, Any]]) -> MagicMock:
    """Creates a MagicMock VectorStoreWrapper returning pre-defined metadata."""
    mock_store = MagicMock()
    mock_store.count.return_value = len(candidates_meta)
    mock_store.health_check.return_value = True
    mock_store.collection_name = "test_collection"

    ids = [m.get("assessment_id", f"id-{i}") for i, m in enumerate(candidates_meta)]
    mock_store.get_all_records.return_value = {
        "ids": ids,
        "metadatas": candidates_meta,
        "documents": ["doc"] * len(candidates_meta),
    }

    # collection.query returns ChromaDB-style result
    mock_store.collection.query.return_value = {
        "ids": [ids],
        "metadatas": [candidates_meta],
        "distances": [[0.1 + i * 0.05 for i in range(len(candidates_meta))]],
    }
    return mock_store


def _make_mock_embedding_provider() -> MagicMock:
    """Creates a MagicMock embedding provider returning deterministic embeddings."""
    mock_provider = MagicMock()
    mock_provider.generate_embeddings.return_value = [[0.1] * 1536]
    mock_provider.get_dimension.return_value = 1536
    return mock_provider


class TestRetrievalEngine:
    """End-to-end tests for RetrievalEngine with mocked ChromaDB."""

    @pytest.fixture
    def meta_records(self) -> list[dict[str, Any]]:
        """Sample metadata records for mock ChromaDB."""
        return [
            {
                "assessment_id": "aaaa-1111",
                "assessment_name": "Verify G+",
                "url": "https://www.shl.com/verify-g-plus",
                "assessment_type": "Cognitive",
                "description": "General cognitive ability test.",
                "job_family": "Technology, Engineering",
                "candidate_level": "Graduate, Professional",
                "duration": 36,
                "languages": "English, French",
                "skills": "Reasoning, Numerical",
                "competencies": "Analytical Thinking",
                "remote_testing": True,
                "adaptive": True,
                "category": "Cognitive",
            },
            {
                "assessment_id": "bbbb-2222",
                "assessment_name": "OPQ32",
                "url": "https://www.shl.com/opq32",
                "assessment_type": "Personality",
                "description": "Personality and behaviour assessment.",
                "job_family": "Sales, Marketing",
                "candidate_level": "Professional",
                "duration": 25,
                "languages": "English",
                "skills": "Communication",
                "competencies": "Influencing Others",
                "remote_testing": True,
                "adaptive": False,
                "category": "Personality",
            },
        ]

    @pytest.fixture
    def engine(self, meta_records: list[dict[str, Any]]) -> RetrievalEngine:
        """Creates a RetrievalEngine with fully mocked dependencies."""
        mock_store = _make_mock_vector_store(meta_records)
        mock_provider = _make_mock_embedding_provider()
        return RetrievalEngine(
            vector_store=mock_store,
            embedding_provider=mock_provider,
        )

    def test_retrieve_returns_result(self, engine: RetrievalEngine) -> None:
        """retrieve() returns a non-empty RetrievalResult."""
        result = engine.retrieve("cognitive test for graduates")
        assert isinstance(result, RetrievalResult)
        assert len(result.candidates) > 0

    def test_retrieve_populates_context(self, engine: RetrievalEngine) -> None:
        """retrieve() produces non-empty context text."""
        result = engine.retrieve("cognitive test")
        assert result.context_text
        assert len(result.context_blocks) > 0

    def test_retrieve_respects_top_k(self, engine: RetrievalEngine) -> None:
        """retrieve() never returns more than top_k candidates."""
        result = engine.retrieve("any test", top_k=1)
        assert len(result.candidates) <= 1

    def test_cache_hit_on_second_retrieve(self, engine: RetrievalEngine) -> None:
        """Second identical retrieve() returns a cache hit."""
        engine.retrieve("cognitive reasoning test")
        result2 = engine.retrieve("cognitive reasoning test")
        assert result2.cache_hit is True

    def test_retrieve_by_name_exact_match(self, engine: RetrievalEngine) -> None:
        """retrieve_by_name() finds assessment by exact name (case-insensitive)."""
        result = engine.retrieve_by_name("Verify G+")
        assert len(result.candidates) == 1
        assert result.candidates[0].name == "Verify G+"

    def test_retrieve_by_name_not_found(self, engine: RetrievalEngine) -> None:
        """retrieve_by_name() returns empty result for unknown assessment."""
        result = engine.retrieve_by_name("NonExistentTest XYZ")
        assert len(result.candidates) == 0

    def test_retrieve_by_url(self, engine: RetrievalEngine) -> None:
        """retrieve_by_url() finds assessment by exact URL."""
        result = engine.retrieve_by_url("https://www.shl.com/opq32")
        assert len(result.candidates) == 1
        assert result.candidates[0].name == "OPQ32"

    def test_retrieve_for_comparison(self, engine: RetrievalEngine) -> None:
        """retrieve_for_comparison() returns all named assessments."""
        result = engine.retrieve_for_comparison(["Verify G+", "OPQ32"])
        assert len(result.candidates) == 2
        names = {c.name for c in result.candidates}
        assert "Verify G+" in names
        assert "OPQ32" in names

    def test_health_check_passes(self, engine: RetrievalEngine) -> None:
        """health_check() returns True for a healthy mock store."""
        assert engine.health_check() is True

    def test_statistics_returns_dict(self, engine: RetrievalEngine) -> None:
        """statistics() returns a dict with 'retrieval' and 'cache' keys."""
        engine.retrieve("test query")
        stats = engine.statistics()
        assert "retrieval" in stats
        assert "cache" in stats

    def test_retrieve_with_filters(self, engine: RetrievalEngine) -> None:
        """retrieve() with filters still returns a valid result."""
        filters = MetadataFilters(
            test_type=["Cognitive"],
            max_duration_mins=60,
        )
        result = engine.retrieve("cognitive test", filters=filters)
        assert isinstance(result, RetrievalResult)

    def test_latency_is_positive(self, engine: RetrievalEngine) -> None:
        """Retrieved result has positive latency measurement."""
        result = engine.retrieve("test")
        assert result.latency_ms >= 0.0
