"""Catalog deduplicator module removing duplicate assessment profiles."""

import logging

from app.catalog.models import CatalogAssessment

logger = logging.getLogger(__name__)


class CatalogDeduplicator:
    """Identifies and resolves duplicate assessments based on name or URL."""

    def deduplicate(self, assessments: list[CatalogAssessment]) -> list[CatalogAssessment]:
        """Deduplicates list of assessments, logging removals.

        Keeps the first occurrence of each unique name and URL.

        Args:
            assessments: List of normalized assessments.

        Returns:
            A cleaned list of assessments without duplicate names or URLs.
        """
        unique_assessments: list[CatalogAssessment] = []
        seen_names: set[str] = set()
        seen_urls: set[str] = set()

        duplicate_count = 0

        for assessment in assessments:
            name_key = assessment.name.lower().strip()
            url_key = assessment.url.lower().strip()

            is_duplicate = False

            if name_key in seen_names:
                logger.info(
                    "Deduplication: Removing duplicate name record '%s' (ID: %s)",
                    assessment.name,
                    assessment.id,
                )
                is_duplicate = True
            elif url_key in seen_urls:
                logger.info(
                    "Deduplication: Removing duplicate URL record '%s' (ID: %s)",
                    assessment.url,
                    assessment.id,
                )
                is_duplicate = True

            if not is_duplicate:
                seen_names.add(name_key)
                seen_urls.add(url_key)
                unique_assessments.append(assessment)
            else:
                duplicate_count += 1

        logger.info("Deduplication completed. Removed %d duplicate records.", duplicate_count)
        return unique_assessments
