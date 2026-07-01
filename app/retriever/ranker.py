"""Candidate ranker responsible for deduplication and top-K selection."""

import logging

from app.retriever.models import RetrievedCandidate

logger = logging.getLogger(__name__)

_MAX_TOP_K = 10  # Hard ceiling — never return more than 10 assessments


class CandidateRanker:
    """Deduplicates and enforces the top-K ceiling on ranked candidate lists."""

    def top_k(
        self,
        candidates: list[RetrievedCandidate],
        k: int = 10,
    ) -> list[RetrievedCandidate]:
        """Deduplicates by assessment ID and returns the top-K highest scoring candidates.

        If a duplicate assessment_id appears, the entry with the highest composite_score
        is preserved and the lower-scoring duplicate is dropped.

        Args:
            candidates: Fully scored and reranked candidate list.
            k: Desired maximum candidate count (hard-capped at 10).

        Returns:
            Deduplicated and truncated candidate list.
        """
        effective_k = min(k, _MAX_TOP_K)

        # Deduplication: keep highest composite_score per assessment_id
        seen: dict[str, RetrievedCandidate] = {}
        for candidate in candidates:
            aid = candidate.assessment_id
            if aid not in seen or candidate.composite_score > seen[aid].composite_score:
                seen[aid] = candidate

        deduplicated = list(seen.values())

        # Re-sort after deduplication (order may shift due to dropped duplicates)
        deduplicated.sort(key=lambda c: c.composite_score, reverse=True)

        # Re-assign ranks after dedup
        final: list[RetrievedCandidate] = []
        for rank_idx, candidate in enumerate(deduplicated[:effective_k], start=1):
            final.append(candidate.model_copy(update={"rank": rank_idx}))

        dropped = len(candidates) - len(final)
        logger.debug(
            "CandidateRanker: Top-K=%d applied. Deduped: %d duplicates removed. Returned: %d.",
            effective_k,
            dropped,
            len(final),
        )
        return final

    def merge_candidate_lists(
        self,
        *candidate_lists: list[RetrievedCandidate],
    ) -> list[RetrievedCandidate]:
        """Merges multiple candidate lists, preserving highest score per assessment_id.

        Used during hybrid merging of semantic + keyword + metadata search results.

        Args:
            *candidate_lists: Variable number of candidate lists to merge.

        Returns:
            Merged deduplicated candidate list (unsorted — call reranker after).
        """
        merged: dict[str, RetrievedCandidate] = {}
        for candidates in candidate_lists:
            for candidate in candidates:
                aid = candidate.assessment_id
                if aid not in merged:
                    merged[aid] = candidate
                else:
                    # Merge: take max of each individual score field
                    existing = merged[aid]
                    merged[aid] = existing.model_copy(
                        update={
                            "semantic_score": max(existing.semantic_score, candidate.semantic_score),
                            "keyword_score": max(existing.keyword_score, candidate.keyword_score),
                            "metadata_score": max(existing.metadata_score, candidate.metadata_score),
                            "composite_score": max(existing.composite_score, candidate.composite_score),
                        }
                    )

        logger.debug(
            "CandidateRanker: Merged %d lists → %d unique candidates.",
            len(candidate_lists),
            len(merged),
        )
        return list(merged.values())
