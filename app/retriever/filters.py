"""Post-retrieval filter module applying constraints that ChromaDB cannot pre-filter."""

import logging

from app.retriever.models import MetadataFilters, RetrievedCandidate

logger = logging.getLogger(__name__)


class CandidateFilter:
    """Applies metadata constraints against a list of already-retrieved candidates.

    Used as a fallback for filter fields that cannot be expressed as ChromaDB
    where-clauses (e.g., multi-value list membership checks).
    """

    def apply(
        self,
        candidates: list[RetrievedCandidate],
        filters: MetadataFilters,
    ) -> list[RetrievedCandidate]:
        """Filters candidate list against active MetadataFilters.

        Args:
            candidates: List of retrieved and scored candidates.
            filters: Active metadata filter constraints.

        Returns:
            Filtered candidate list. Returns original list if no filters active.
        """
        if filters.is_empty():
            return candidates

        original_count = len(candidates)
        filtered = [c for c in candidates if self._passes(c, filters)]

        logger.debug(
            "CandidateFilter: Retained %d/%d candidates after post-filtering.",
            len(filtered),
            original_count,
        )
        return filtered

    def _passes(self, candidate: RetrievedCandidate, filters: MetadataFilters) -> bool:
        """Returns True if the candidate satisfies all active filter constraints.

        Args:
            candidate: A single retrieved candidate.
            filters: Filter constraints to apply.

        Returns:
            True if all filters pass, False otherwise.
        """
        # Duration constraint
        if filters.max_duration_mins is not None:
            if candidate.duration_mins > filters.max_duration_mins:
                return False

        # Job family constraint (any match)
        if filters.job_family:
            candidate_jf_lower = [jf.lower() for jf in candidate.job_family]
            if not any(f.lower() in candidate_jf_lower for f in filters.job_family):
                return False

        # Target level constraint (any match)
        if filters.target_level:
            candidate_levels_lower = [lv.lower() for lv in candidate.target_level]
            if not any(lv.lower() in candidate_levels_lower for lv in filters.target_level):
                return False

        # Language constraint (any match)
        if filters.languages:
            candidate_langs_lower = [lang.lower() for lang in candidate.languages]
            if not any(lang.lower() in candidate_langs_lower for lang in filters.languages):
                return False

        # Skills constraint (any match)
        if filters.skills:
            candidate_skills_lower = [sk.lower() for sk in candidate.skills]
            if not any(sk.lower() in candidate_skills_lower for sk in filters.skills):
                return False

        # Competencies constraint (any match)
        if filters.competencies:
            candidate_comp_lower = [cp.lower() for cp in candidate.competencies]
            if not any(cp.lower() in candidate_comp_lower for cp in filters.competencies):
                return False

        # Remote testing constraint
        if filters.remote_testing is not None:
            if candidate.remote_testing != filters.remote_testing:
                return False

        return True

    def apply_soft(
        self,
        candidates: list[RetrievedCandidate],
        filters: MetadataFilters,
    ) -> list[RetrievedCandidate]:
        """Applies soft filtering — marks non-matching candidates with reduced score
        instead of removing them entirely.

        Useful when strict filtering would result in an empty result set.

        Args:
            candidates: Retrieved candidates list.
            filters: Active filter constraints.

        Returns:
            All candidates, with penalized scores for non-matching entries.
        """
        if filters.is_empty():
            return candidates

        result: list[RetrievedCandidate] = []
        for candidate in candidates:
            if not self._passes(candidate, filters):
                # Apply score penalty for non-matching but don't remove
                penalized = candidate.model_copy(
                    update={"metadata_score": candidate.metadata_score * 0.3}
                )
                result.append(penalized)
            else:
                result.append(candidate)
        return result
