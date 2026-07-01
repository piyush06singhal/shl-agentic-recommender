"""Catalog normalizer module standardizing and formatting metadata properties."""

import logging
import re
import uuid

from app.catalog.models import CatalogAssessment, ScrapedAssessment
from app.configs.constants import (
    ASSESSMENT_TYPE_COGNITIVE,
    ASSESSMENT_TYPE_PERSONALITY,
    SUPPORTED_ASSESSMENT_TYPES,
    SUPPORTED_JOB_FAMILIES,
)

logger = logging.getLogger(__name__)


class CatalogNormalizer:
    """Standardizes types, maps seniority levels, splits lists, and parses test durations into integer values."""

    def normalize_assessment(self, scraped: ScrapedAssessment) -> CatalogAssessment:
        """Converts raw scraped properties into normalized schema-compliant types.

        Args:
            scraped: The cleaned ScrapedAssessment dataset record.

        Returns:
            A schema-compliant CatalogAssessment database record.
        """
        # Generate persistent UUID namespace key from URL string
        assessment_id = uuid.uuid5(uuid.NAMESPACE_URL, scraped.url)

        # Normalize duration (mins)
        duration_mins = self.parse_duration(scraped.duration)

        # Split and map list items
        job_families = self.normalize_job_families(scraped.job_family)
        target_levels = self.normalize_target_levels(scraped.target_level)
        languages = self.parse_list(scraped.languages)
        skills = self.parse_list(scraped.skills)
        competencies = self.parse_list(scraped.competencies)

        # Standardize test type classification
        test_type = self.normalize_test_type(scraped.test_type)

        # Parse booleans
        remote_testing = self.parse_bool(scraped.remote_testing, default_val=True)
        adaptive = self.parse_bool(scraped.adaptive, default_val=False)

        return CatalogAssessment(
            id=assessment_id,
            name=scraped.name,
            url=scraped.url,
            test_type=test_type,
            description=scraped.description,
            job_family=job_families,
            target_level=target_levels,
            duration_mins=duration_mins,
            languages=languages,
            skills=skills,
            competencies=competencies,
            remote_testing=remote_testing,
            adaptive=adaptive,
            category=scraped.category or "Standard",
        )

    def parse_duration(self, duration_str: str | None) -> int:
        """Extracts and normalizes raw duration text into integer minutes representation.

        E.g. "15 mins" -> 15, "0.5 hours" -> 30, "45 minutes" -> 45. Defaults to 20 mins.
        """
        if not duration_str:
            return 20

        norm = duration_str.lower().strip()
        # Look for digit counts
        match = re.search(r"(\d+(?:\.\d+)?)\s*(min|hour|hr|mins|hours|hrs|minutes)", norm)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            if "hour" in unit or "hr" in unit:
                return int(value * 60)
            return int(value)

        # Fallback raw search for digits
        digits = re.findall(r"\d+", norm)
        if digits:
            return int(digits[0])

        return 20

    def parse_list(self, list_str: str | None) -> list[str]:
        """Splits comma, semicolon, or slash separated text strings into lists.

        Strips spaces and removes empty entries.
        """
        if not list_str:
            return []

        # Split by comma, semicolon, or bullet divider characters
        items = re.split(r"[,;|\n•\/]|\sand\s", list_str)
        cleaned_items = [i.strip() for i in items if i.strip()]

        # Remove empty item stubs and duplicates
        seen = set()
        result = []
        for item in cleaned_items:
            # Capitalize first letter of each item
            cap_item = item[0].upper() + item[1:] if len(item) > 1 else item.upper()
            if cap_item.lower() not in seen:
                seen.add(cap_item.lower())
                result.append(cap_item)

        return result

    def normalize_job_families(self, job_family_str: str | None) -> list[str]:
        """Maps scraped job family strings to the supported whitelist of job family constants."""
        if not job_family_str:
            return []

        raw_list = self.parse_list(job_family_str)
        matched_families = []

        for raw in raw_list:
            norm_raw = raw.lower()
            for supported in SUPPORTED_JOB_FAMILIES:
                if supported.lower() in norm_raw or norm_raw in supported.lower():
                    if supported not in matched_families:
                        matched_families.append(supported)

        # Default fallback to technology if tech/development matches are found
        if not matched_families:
            norm_str = job_family_str.lower()
            if "software" in norm_str or "tech" in norm_str or "it" in norm_str or "developer" in norm_str:
                matched_families.append("Technology")

        return matched_families

    def normalize_target_levels(self, target_level_str: str | None) -> list[str]:
        """Maps seniority descriptions (e.g. entry, lead) to supported level constants."""
        if not target_level_str:
            return ["Professional"]

        norm = target_level_str.lower()
        matched_levels = []

        # Check entry levels mapping
        if any(w in norm for w in ["graduate", "entry", "intern", "junior", "early"]):
            matched_levels.append("Graduate/Entry")
        # Check professional mappings
        if any(w in norm for w in ["professional", "specialist", "mid", "experienced"]):
            matched_levels.append("Professional")
        # Check leadership mappings
        if any(w in norm for w in ["leadership", "management", "leader", "senior", "director", "exec"]):
            matched_levels.append("Leadership")

        if not matched_levels:
            matched_levels.append("Professional")

        return matched_levels

    def normalize_test_type(self, test_type_str: str | None) -> str:
        """Maps and standardizes raw test type categorizations to supported type constants."""
        if not test_type_str:
            return ASSESSMENT_TYPE_PERSONALITY

        norm = test_type_str.lower()
        for supported in SUPPORTED_ASSESSMENT_TYPES:
            if supported.lower() in norm:
                return supported

        # Fallback classification heuristic checks
        if "cognitive" in norm or "ability" in norm or "reasoning" in norm:
            return ASSESSMENT_TYPE_COGNITIVE
        if "personality" in norm or "style" in norm or "behavior" in norm:
            return ASSESSMENT_TYPE_PERSONALITY
        if "skills" in norm or "code" in norm or "technical" in norm:
            return "Skills"
        if "language" in norm or "english" in norm or "communication" in norm:
            return "Language"

        return ASSESSMENT_TYPE_COGNITIVE

    def parse_bool(self, bool_str: str | None, default_val: bool) -> bool:
        """Parses a boolean value from standard true/false string indicators."""
        if not bool_str:
            return default_val

        norm = bool_str.lower().strip()
        if norm in ["yes", "true", "1", "y", "supported", "enabled"]:
            return True
        if norm in ["no", "false", "0", "n", "not supported", "disabled"]:
            return False

        return default_val
