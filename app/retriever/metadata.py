"""Metadata builder converting CatalogAssessment data into flat primitives for ChromaDB."""

import logging

from app.catalog.models import CatalogAssessment

logger = logging.getLogger(__name__)


class MetadataBuilder:
    """Formats assessment schemas into flat key-value pairs meeting ChromaDB primitives constraints."""

    def build_metadata(self, record: CatalogAssessment, document_hash: str) -> dict[str, str | int | float | bool]:
        """Converts structured assessment lists and fields into flat string/primitive types.

        Args:
            record: The active CatalogAssessment record database entries.
            document_hash: A SHA-256 string hash representing the compiled search document.

        Returns:
            A dictionary containing only primitive metadata values.
        """
        # Convert lists to comma-separated strings to conform to ChromaDB constraints
        job_family_str = ", ".join(record.job_family)
        target_level_str = ", ".join(record.target_level)
        languages_str = ", ".join(record.languages)
        skills_str = ", ".join(record.skills)
        competencies_str = ", ".join(record.competencies)

        return {
            "assessment_id": str(record.id),
            "assessment_name": record.name,
            "url": record.url,
            "assessment_type": record.test_type,
            "job_family": job_family_str,
            "candidate_level": target_level_str,
            "duration": record.duration_mins,
            "languages": languages_str,
            "skills": skills_str,
            "competencies": competencies_str,
            "remote_testing": record.remote_testing,
            "adaptive": record.adaptive,
            "category": record.category,
            "document_hash": document_hash,
        }
