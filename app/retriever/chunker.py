"""Document chunker module constructing search strings from assessment profiles."""

import logging

from app.catalog.models import CatalogAssessment

logger = logging.getLogger(__name__)


class AssessmentChunker:
    """Formats normalized CatalogAssessment records into unified human-readable search blocks."""

    def build_search_document(self, record: CatalogAssessment) -> str:
        """Serializes CatalogAssessment properties into a structured document text chunk.

        Args:
            record: The database CatalogAssessment record.

        Returns:
            A formatted multi-line string block optimized for vector database searching.
        """
        # Format list properties
        job_families = ", ".join(record.job_family) if record.job_family else "Not Specified"
        levels = ", ".join(record.target_level) if record.target_level else "Not Specified"
        languages = ", ".join(record.languages) if record.languages else "Not Specified"
        skills = ", ".join(record.skills) if record.skills else "Not Specified"
        competencies = ", ".join(record.competencies) if record.competencies else "Not Specified"

        # Build text string block
        lines = [
            f"Assessment: {record.name}",
            f"Type: {record.test_type}",
            f"Job Families: {job_families}",
            f"Levels: {levels}",
            f"Duration: {record.duration_mins} minutes",
            f"Languages: {languages}",
            f"Skills: {skills}",
            f"Competencies: {competencies}",
            f"Description: {record.description}",
        ]

        document = "\n".join(lines)
        return self._normalize_spacing(document)

    def _normalize_spacing(self, text: str) -> str:
        """Strips double spaces, trailing line breaks, and cleans tabs."""
        if not text:
            return ""
        # Clean double blank spaces
        cleaned = " ".join(part for part in text.split(" ") if part)
        # Normalize double lines spacing
        lines = [line.strip() for line in cleaned.split("\n")]
        return "\n".join(line for line in lines if line)
