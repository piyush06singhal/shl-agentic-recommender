"""Catalog manager class caching and querying assessment profiles."""

import logging
import os

from app.configs.settings import get_settings
from app.schemas.response import Assessment
from app.services.utils import safe_json_load

logger = logging.getLogger(__name__)


class CatalogManager:
    """Caching service loading catalog.json at startup, exposing fast lookup search methods."""

    def __init__(self, catalog_path: str | None = None) -> None:
        settings = get_settings()
        self.catalog_path = catalog_path or settings.catalog_path
        self._catalog_cache: dict[str, Assessment] = {}
        self._catalog_list: list[Assessment] = []

        # Auto-load on initialization if the catalog file exists
        if os.path.exists(self.catalog_path):
            self.load_catalog_database()
        else:
            logger.warning(
                "Catalog database file not found at %s. Empty cache initialized.",
                self.catalog_path,
            )

    def load_catalog_database(self) -> None:
        """Loads and parses the catalog JSON database file, caching entries in memory."""
        try:
            logger.info("Loading SHL assessment catalog from %s...", self.catalog_path)
            raw_data = safe_json_load(self.catalog_path)

            # Reset cache
            self._catalog_cache.clear()
            self._catalog_list.clear()

            # Expect raw_data to be a list of assessment profiles
            if not isinstance(raw_data, list):
                raise ValueError("Catalog JSON database root must be a list of records.")

            for index, item in enumerate(raw_data):
                try:
                    assessment = Assessment(**item)
                    self._catalog_list.append(assessment)
                    # Cache by unique string representations (lowercase name and URL)
                    self._catalog_cache[assessment.name.lower().strip()] = assessment
                    self._catalog_cache[assessment.url.lower().strip()] = assessment
                except Exception as e:
                    logger.error(
                        "Integrity: Failed parsing catalog item index %d: %s",
                        index,
                        e,
                    )

            logger.info(
                "Successfully loaded %d SHL assessment profiles into memory cache.",
                len(self._catalog_list),
            )
        except Exception as e:
            logger.error("Failed to load catalog database: %s", e)
            raise

    def get_all_assessments(self) -> list[Assessment]:
        """Exposes the raw uncached list of all assessments in the database."""
        return self._catalog_list

    def get_assessment_by_name(self, name: str) -> Assessment | None:
        """Exposes getter looking up assessments by exact name match (case-insensitive)."""
        return self._catalog_cache.get(name.lower().strip())

    def get_assessment_by_url(self, url: str) -> Assessment | None:
        """Exposes getter looking up assessments by URL string (case-insensitive)."""
        return self._catalog_cache.get(url.lower().strip())

    def search_assessments(self, query: str) -> list[Assessment]:
        """Searches assessments by checking match attributes (name, description, skills).

        Args:
            query: The text criteria to search.

        Returns:
            List of matching Assessment profiles.
        """
        if not query or not query.strip():
            return []

        norm_query = query.lower().strip()
        matches: list[Assessment] = []

        for assessment in self._catalog_list:
            # Check name match
            if norm_query in assessment.name.lower():
                matches.append(assessment)
                continue
            # Check description match
            if norm_query in assessment.description.lower():
                matches.append(assessment)
                continue
            # Check skills match
            # Wait, our Assessment schema in schemas/response.py has:
            # id, name, url, test_type, description, job_family, target_level, duration_mins, languages.
            # But the extended metadata can be in description, or we can search skills if available.
            # Since Assessment in schemas/response.py doesn't have an explicit 'skills' list (unless it's extended),
            # let's write a safe check that compiles successfully if skills are dynamically present.
            if hasattr(assessment, "skills"):
                skills_list = getattr(assessment, "skills", [])
                if any(norm_query in skill.lower() for skill in skills_list):
                    matches.append(assessment)
                    continue

        return matches
