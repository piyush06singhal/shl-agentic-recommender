"""Loader module reading and parsing the unified catalog JSON file."""

import logging
import os

from app.catalog.models import CatalogAssessment
from app.configs.settings import get_settings
from app.services.utils import safe_json_load

logger = logging.getLogger(__name__)


class CatalogLoader:
    """Ingests catalog.json and converts serialized records into typed CatalogAssessment instances."""

    def __init__(self, catalog_path: str | None = None) -> None:
        settings = get_settings()
        self.catalog_path = catalog_path or settings.catalog_path

    def load_assessments(self) -> list[CatalogAssessment]:
        """Loads and parses the catalog JSON database from file path.

        Returns:
            A list of CatalogAssessment Pydantic models.
        """
        if not os.path.exists(self.catalog_path):
            logger.error("Catalog Loader: Database file does not exist at %s", self.catalog_path)
            raise FileNotFoundError(f"Catalog file not found at {self.catalog_path}")

        try:
            logger.info("Catalog Loader: Ingesting database entries from %s...", self.catalog_path)
            raw_data = safe_json_load(self.catalog_path)

            if not isinstance(raw_data, list):
                raise ValueError("Catalog JSON root node must be a list of records.")

            assessments: list[CatalogAssessment] = []
            for idx, item in enumerate(raw_data):
                try:
                    assessment = CatalogAssessment(**item)
                    assessments.append(assessment)
                except Exception as e:
                    logger.error(
                        "Catalog Loader: Parsing failed for item index %d: %s. Skipping...",
                        idx,
                        e,
                    )

            logger.info("Catalog Loader: Successfully loaded %d assessments.", len(assessments))
            return assessments
        except Exception as e:
            logger.error("Catalog Loader: Fatal crash loading database: %s", e)
            raise
