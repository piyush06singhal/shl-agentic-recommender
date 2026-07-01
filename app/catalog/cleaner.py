"""Catalog cleaner module sanitizing raw string inputs."""

import html
import logging
import re

from app.catalog.models import ScrapedAssessment

logger = logging.getLogger(__name__)


class CatalogCleaner:
    """Sanitizes raw scraped strings, stripping formatting, HTML remnants, and whitespace duplicates."""

    def clean_text(self, text: str | None) -> str:
        """Cleans a raw text string.

        Args:
            text: The raw string to clean.

        Returns:
            The sanitized string.
        """
        if not text:
            return ""

        # Strip html entities and tags (safety check)
        cleaned = re.sub(r"<[^>]+>", "", text)
        cleaned = html.unescape(cleaned)
        # Normalize smart punctuation quotes
        cleaned = (
            cleaned.replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
        )
        # Replace multiple spaces with a single space
        cleaned = re.sub(r"\s+", " ", cleaned)
        # Normalize punctuation spacing
        cleaned = re.sub(r"\s+([.,!?;:])", r"\1", cleaned)

        return cleaned.strip()

    def clean_metadata(self, raw: ScrapedAssessment) -> ScrapedAssessment:
        """Cleans all fields inside a ScrapedAssessment instance.

        Args:
            raw: Raw parsed assessment metadata.

        Returns:
            A new ScrapedAssessment model with sanitized parameters.
        """
        return ScrapedAssessment(
            name=self.clean_text(raw.name),
            url=raw.url.strip(),  # Preserve exact URL routing case/format
            description=self.clean_text(raw.description),
            test_type=self.clean_text(raw.test_type) if raw.test_type else None,
            job_family=self.clean_text(raw.job_family) if raw.job_family else None,
            target_level=self.clean_text(raw.target_level) if raw.target_level else None,
            duration=self.clean_text(raw.duration) if raw.duration else None,
            languages=self.clean_text(raw.languages) if raw.languages else None,
            skills=self.clean_text(raw.skills) if raw.skills else None,
            competencies=self.clean_text(raw.competencies) if raw.competencies else None,
            remote_testing=self.clean_text(raw.remote_testing) if raw.remote_testing else None,
            adaptive=self.clean_text(raw.adaptive) if raw.adaptive else None,
            category=self.clean_text(raw.category) if raw.category else None,
        )
