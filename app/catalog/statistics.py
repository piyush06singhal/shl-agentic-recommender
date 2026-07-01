"""Catalog statistics module compiling database characteristics reports."""

import logging
from datetime import UTC, datetime
from typing import Any

from app.catalog.models import CatalogAssessment
from app.configs.constants import API_VERSION

logger = logging.getLogger(__name__)


class CatalogStatisticsGenerator:
    """Aggregates catalog profile metrics, calculating average times,

    language distributions, and schema validations failures.
    """

    def generate_report(
        self,
        assessments: list[CatalogAssessment],
        duplicate_count: int,
        validation_failures_count: int,
        missing_metadata_stubs: int,
    ) -> dict[str, Any]:
        """Compiles catalog status stats.

        Args:
            assessments: The current active list of CatalogAssessment records.
            duplicate_count: Number of duplicates removed.
            validation_failures_count: Number of validation issues.
            missing_metadata_stubs: Count of missing optional metadata values.

        Returns:
            A structured dictionary report containing catalog analytics metrics.
        """
        logger.info("Compiling catalog index statistics report...")

        # Calculate durations averages
        durations = [r.duration_mins for r in assessments]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Calculate type distributions
        type_dist: dict[str, int] = {}
        for r in assessments:
            type_dist[r.test_type] = type_dist.get(r.test_type, 0) + 1

        # Calculate language distributions
        lang_dist: dict[str, int] = {}
        for r in assessments:
            for lang in r.languages:
                lang_dist[lang] = lang_dist.get(lang, 0) + 1

        # Calculate job family distributions
        family_dist: dict[str, int] = {}
        for r in assessments:
            for fam in r.job_family:
                family_dist[fam] = family_dist.get(fam, 0) + 1

        # Compile JSON payload structure
        report: dict[str, Any] = {
            "catalog_version": API_VERSION,
            "generation_timestamp": datetime.now(UTC).isoformat(),
            "total_assessments": len(assessments),
            "average_duration_mins": round(avg_duration, 2),
            "distribution_by_test_type": type_dist,
            "distribution_by_job_family": family_dist,
            "unique_languages_count": len(lang_dist),
            "distribution_by_language": lang_dist,
            "pipeline_metrics": {
                "duplicates_removed_count": duplicate_count,
                "validation_failures_count": validation_failures_count,
                "missing_optional_fields_count": missing_metadata_stubs,
            },
        }

        logger.info("Catalog statistics report generated successfully.")
        return report
