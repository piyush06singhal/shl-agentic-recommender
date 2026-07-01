"""Deterministic priority reranker for retrieved assessment candidates."""

import logging

from app.retriever.models import MetadataFilters, RetrievedCandidate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Priority constants (lower = higher priority)
# ---------------------------------------------------------------------------
_P1_METADATA = 1
_P2_SEMANTIC = 2
_P3_KEYWORD = 3
_P4_COMPLETENESS = 4
_P5_CONFIDENCE = 5


def _catalog_completeness(candidate: RetrievedCandidate) -> float:
    """Fraction of optional metadata fields that are populated.

    Args:
        candidate: Retrieved candidate.

    Returns:
        A completeness ratio between 0.0 and 1.0.
    """
    optional_checks = [
        bool(candidate.job_family),
        bool(candidate.target_level),
        bool(candidate.languages),
        bool(candidate.skills),
        bool(candidate.competencies),
        bool(candidate.description),
        bool(candidate.category),
    ]
    return sum(1 for c in optional_checks if c) / len(optional_checks)


def _assessment_confidence(candidate: RetrievedCandidate) -> float:
    """Proxy confidence score based on information richness of the record.

    Considers whether URL is set, duration is non-zero, and field counts.

    Args:
        candidate: Retrieved candidate.

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    score = 0.0
    if candidate.url:
        score += 0.4
    if candidate.duration_mins > 0:
        score += 0.2
    if len(candidate.skills) >= 2:
        score += 0.2
    if len(candidate.competencies) >= 1:
        score += 0.1
    if len(candidate.description) >= 30:
        score += 0.1
    return min(score, 1.0)


class Reranker:
    """Deterministic priority-based reranker.

    Priority order (strict lexicographic — no blending):
        1. Metadata match score   (highest priority)
        2. Semantic similarity
        3. Keyword relevance
        4. Catalog completeness
        5. Assessment confidence  (tiebreaker)
    """

    def rerank(
        self,
        candidates: list[RetrievedCandidate],
        filters: MetadataFilters | None = None,
    ) -> list[RetrievedCandidate]:
        """Reranks candidates using strict priority ordering and attaches composite scores.

        Args:
            candidates: Scored candidate list from hybrid merge.
            filters: Active filters (used to compute metadata score if missing).

        Returns:
            Deterministically sorted and ranked candidate list.
        """
        if not candidates:
            return []

        active_filters = filters or MetadataFilters()

        # Attach composite scores and completeness signals
        enriched: list[tuple[RetrievedCandidate, float, float, float, float, float]] = []
        for c in candidates:
            meta_s = c.metadata_score if not active_filters.is_empty() else 1.0
            sem_s = c.semantic_score
            kw_s = c.keyword_score
            completeness = _catalog_completeness(c)
            confidence = _assessment_confidence(c)

            # Composite score: weighted blend for reporting/display only
            # (actual sort order is lexicographic priority, not this blend)
            composite = (
                meta_s * 0.35
                + sem_s * 0.35
                + kw_s * 0.15
                + completeness * 0.10
                + confidence * 0.05
            )
            enriched.append((c, meta_s, sem_s, kw_s, completeness, composite))

        # Sort by priority tuple (descending — highest score first)
        enriched.sort(
            key=lambda x: (x[1], x[2], x[3], x[4], x[5]),
            reverse=True,
        )

        # Assign ranks and attach composite scores
        result: list[RetrievedCandidate] = []
        for rank_idx, (candidate, _, _, _, _, composite) in enumerate(enriched, start=1):
            result.append(
                candidate.model_copy(
                    update={
                        "rank": rank_idx,
                        "composite_score": round(composite, 4),
                    }
                )
            )

        logger.debug(
            "Reranker: Reranked %d candidates. Top: %s (composite=%.3f)",
            len(result),
            result[0].name if result else "N/A",
            result[0].composite_score if result else 0.0,
        )
        return result
