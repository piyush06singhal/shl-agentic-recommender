"""Catalog validator module auditing data schema constraints."""

import logging
from urllib.parse import urlparse

from app.catalog.models import CatalogAssessment
from app.configs.constants import SUPPORTED_ASSESSMENT_TYPES, WHITELISTED_DOMAINS

logger = logging.getLogger(__name__)


class CatalogValidator:
    """Validates assessment records, checking URLs, checking fields, and auditing duplicate names."""

    def validate_assessment(self, record: CatalogAssessment) -> list[str]:
        """Validates a single CatalogAssessment record for strict schema compliance.

        Args:
            record: The normalized CatalogAssessment record.

        Returns:
            A list of validation error strings. Empty if clean.
        """
        errors = []

        # 1. Check Required fields
        if not record.name or not record.name.strip():
            errors.append("Missing required field: name")
        if not record.url or not record.url.strip():
            errors.append("Missing required field: url")
        if not record.description or not record.description.strip():
            errors.append("Missing required field: description")
        if not record.test_type:
            errors.append("Missing required field: test_type")

        # 2. Check URL Whitelist
        if record.url:
            parsed = urlparse(record.url)
            if not parsed.scheme or not parsed.netloc:
                errors.append(f"Invalid URL structure: {record.url}")
            else:
                domain = parsed.netloc.lower()
                # Check if matches whitelist
                if not any(domain == wd or domain.endswith(f".{wd}") for wd in WHITELISTED_DOMAINS):
                    errors.append(f"URL domain is not whitelisted: {record.url}")

        # 3. Check Durations Limits
        if record.duration_mins <= 0:
            errors.append(f"Invalid test duration: {record.duration_mins} mins. Must be positive.")
        elif record.duration_mins > 180:
            errors.append(f"Suspiciously high test duration: {record.duration_mins} mins. Exceeds 3 hours.")

        # 4. Check Type categories
        if record.test_type not in SUPPORTED_ASSESSMENT_TYPES:
            errors.append(f"Invalid test type classification: {record.test_type}")

        return errors

    def validate_catalog(self, assessments: list[CatalogAssessment]) -> tuple[bool, dict[str, list[str]]]:
        """Audits a list of assessments, checks duplicates, and aggregates validation errors.

        Args:
            assessments: The complete list of CatalogAssessment records.

        Returns:
            A tuple of (is_valid, validation_report_dictionary).
        """
        report: dict[str, list[str]] = {}
        is_valid = True

        seen_names: dict[str, str] = {}
        seen_urls: dict[str, str] = {}

        for record in assessments:
            record_id_str = str(record.id)
            errors = self.validate_assessment(record)

            # Duplicate name check
            norm_name = record.name.lower().strip()
            if norm_name in seen_names:
                errors.append(f"Duplicate assessment name match: '{record.name}' matches ID {seen_names[norm_name]}")
            else:
                seen_names[norm_name] = record_id_str

            # Duplicate URL check
            norm_url = record.url.lower().strip()
            if norm_url in seen_urls:
                errors.append(f"Duplicate URL path match: '{record.url}' matches ID {seen_urls[norm_url]}")
            else:
                seen_urls[norm_url] = record_id_str

            if errors:
                is_valid = False
                report[record_id_str] = errors
                for error in errors:
                    logger.warning("Validation Failure (Record ID: %s): %s", record_id_str, error)

        return is_valid, report
