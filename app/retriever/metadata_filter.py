"""Metadata filter module translating MetadataFilters into ChromaDB where-clause dicts."""

import logging
from typing import Any

from app.retriever.models import MetadataFilters

logger = logging.getLogger(__name__)


class MetadataFilterBuilder:
    """Converts MetadataFilters into ChromaDB-compatible where-clause dictionaries."""

    def build_where_clause(self, filters: MetadataFilters) -> dict[str, Any] | None:
        """Translates structured filters into a ChromaDB-compatible where= dict.

        ChromaDB supports: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $and, $or

        Args:
            filters: The MetadataFilters object with applied constraints.

        Returns:
            A dict suitable for the `where=` parameter of ChromaDB queries,
            or None if no filters are active.
        """
        if filters.is_empty():
            logger.debug("MetadataFilterBuilder: No filters active — bypassing where clause.")
            return None

        conditions: list[dict[str, Any]] = []

        # Test type filter (exact match, single value supported for primary type)
        if filters.test_type and len(filters.test_type) == 1:
            conditions.append({"assessment_type": {"$eq": filters.test_type[0]}})
        elif filters.test_type and len(filters.test_type) > 1:
            # ChromaDB $in for list membership
            conditions.append({"assessment_type": {"$in": filters.test_type}})

        # Duration filter (less than or equal)
        if filters.max_duration_mins is not None:
            conditions.append({"duration": {"$lte": filters.max_duration_mins}})

        # Remote testing filter
        if filters.remote_testing is not None:
            conditions.append({"remote_testing": {"$eq": filters.remote_testing}})

        # Build final where clause
        if not conditions:
            logger.debug("MetadataFilterBuilder: Filters present but no ChromaDB-translatable conditions found.")
            return None

        if len(conditions) == 1:
            where_clause = conditions[0]
        else:
            where_clause = {"$and": conditions}

        logger.debug("MetadataFilterBuilder: Built where clause: %s", where_clause)
        return where_clause

    def compute_metadata_score(
        self,
        filters: MetadataFilters,
        candidate_meta: dict[str, Any],
    ) -> float:
        """Scores how well a candidate metadata matches the applied filters.

        Used post-retrieval to rank metadata alignment even for fields ChromaDB
        cannot pre-filter (e.g., multi-value lists stored as comma-separated strings).

        Args:
            filters: The active metadata filters.
            candidate_meta: The candidate's stored metadata dict.

        Returns:
            A match score between 0.0 and 1.0.
        """
        if filters.is_empty():
            return 1.0

        checks: list[bool] = []

        # Job family match — stored as comma-separated string in ChromaDB
        if filters.job_family:
            stored_jf = str(candidate_meta.get("job_family", "")).lower()
            matched = any(jf.lower() in stored_jf for jf in filters.job_family)
            checks.append(matched)

        # Target level match
        if filters.target_level:
            stored_level = str(candidate_meta.get("candidate_level", "")).lower()
            matched = any(lv.lower() in stored_level for lv in filters.target_level)
            checks.append(matched)

        # Language match
        if filters.languages:
            stored_langs = str(candidate_meta.get("languages", "")).lower()
            matched = any(lang.lower() in stored_langs for lang in filters.languages)
            checks.append(matched)

        # Skills match
        if filters.skills:
            stored_skills = str(candidate_meta.get("skills", "")).lower()
            matched = any(sk.lower() in stored_skills for sk in filters.skills)
            checks.append(matched)

        # Competencies match
        if filters.competencies:
            stored_comp = str(candidate_meta.get("competencies", "")).lower()
            matched = any(cp.lower() in stored_comp for cp in filters.competencies)
            checks.append(matched)

        # Duration check
        if filters.max_duration_mins is not None:
            stored_dur = int(candidate_meta.get("duration", 999))
            checks.append(stored_dur <= filters.max_duration_mins)

        if not checks:
            return 1.0

        return sum(1 for c in checks if c) / len(checks)
