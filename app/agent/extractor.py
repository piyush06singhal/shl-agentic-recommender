"""Requirement extractor parsing structured parameters from raw user messages."""

import logging
import re

from app.agent.models import ExtractedContext
from app.configs.constants import (
    SUPPORTED_JOB_FAMILIES,
)

logger = logging.getLogger(__name__)

# Compile language patterns
_LANGUAGES = ["english", "french", "german", "spanish", "japanese", "chinese", "italian", "portuguese"]
_LANG_REGEXES = {lang: re.compile(rf"\b{lang}\b", re.IGNORECASE) for lang in _LANGUAGES}

# Compile assessment name identifiers
_ASSESSMENT_IDENTIFIERS = {
    "opq": "SHL OPQ32 Personality Assessment",
    "opq32": "SHL OPQ32 Personality Assessment",
    "verify": "SHL Cognitive Ability Test (Verify)",
    "g+": "Verify G+",
    "verify g+": "Verify G+",
    "java developer": "SHL Java Developer Skills Test",
    "java": "SHL Java Developer Skills Test",
    "english communication": "SHL English Language Communication Test",
    "general ability": "SHL Graduate General Ability Test",
    "graduate general": "SHL Graduate General Ability Test",
}


class ContextExtractor:
    """Extracts structured criteria requirements from single text strings using regex/keywords."""

    def extract_from_text(self, text: str) -> ExtractedContext:
        """Parses a text block and returns an ExtractedContext with found requirements.

        Args:
            text: The message string to analyze.

        Returns:
            An ExtractedContext object representing extracted requirements from this turn.
        """
        lower_text = text.lower()

        job_family = self._extract_job_families(lower_text)
        candidate_level = self._extract_candidate_levels(lower_text)
        assessment_type = self._extract_assessment_types(lower_text)
        languages = self._extract_languages(lower_text)
        max_duration = self._extract_duration(lower_text)
        skills = self._extract_skills(lower_text)
        competencies = self._extract_competencies(lower_text)
        preferred = self._extract_preferred_assessments(lower_text)

        # If we have preferred assessments and intent could be comparison
        comparison = []
        if "compare" in lower_text or "vs" in lower_text or "versus" in lower_text or "difference" in lower_text:
            comparison = list(preferred)

        return ExtractedContext(
            job_family=job_family,
            candidate_level=candidate_level,
            assessment_type=assessment_type,
            skills=skills,
            competencies=competencies,
            languages=languages,
            max_duration_mins=max_duration,
            preferred_assessments=preferred,
            comparison_targets=comparison,
        )

    def _extract_job_families(self, text: str) -> list[str]:
        results: list[str] = []
        # Mapping mapping patterns
        mappings = {
            "technology": [
                "tech", "technology", "developer", "programmer", "software", "it",
                "coder", "engineering", "java", "python", "programming", "coding"
            ],
            "sales": ["sales", "selling", "marketing", "retail", "business development"],
            "management": ["management", "manager", "leader", "leadership", "executive", "director"],
            "finance": ["finance", "banking", "financial", "accounting", "auditing", "analyst", "bookkeeping"],
            "administration": ["administration", "admin", "clerical", "office", "secretariat", "support"],
        }
        for family, keywords in mappings.items():
            for kw in keywords:
                if re.search(rf"\b{kw}\b", text):
                    # Map to canonical name from constants
                    for canonical in SUPPORTED_JOB_FAMILIES:
                        if canonical.lower() == family:
                            results.append(canonical)
                            break
                    break
        return list(set(results))

    def _extract_candidate_levels(self, text: str) -> list[str]:
        results: list[str] = []
        mappings = {
            "Graduate/Entry": ["graduate", "entry", "junior", "intern", "apprentice", "early career"],
            "Professional": ["professional", "mid-level", "experienced", "associate"],
            "Leadership": ["leadership", "manager", "director", "senior", "executive", "lead"],
        }
        for level, keywords in mappings.items():
            for kw in keywords:
                if re.search(rf"\b{kw}\b", text):
                    results.append(level)
                    break
        return list(set(results))

    def _extract_assessment_types(self, text: str) -> list[str]:
        results: list[str] = []
        mappings = {
            "Cognitive": ["cognitive", "reasoning", "verify", "aptitude", "intellectual", "ability"],
            "Personality": ["personality", "opq", "opq32", "behavioral", "behavioural", "style", "fit"],
            "Skills": ["skills", "coding", "programming", "technical", "excel", "typing"],
            "Language": ["language", "english communication", "communication test", "spoken"],
        }
        for atype, keywords in mappings.items():
            for kw in keywords:
                if re.search(rf"\b{kw}\b", text):
                    results.append(atype)
                    break
        return list(set(results))

    def _extract_languages(self, text: str) -> list[str]:
        results: list[str] = []
        for lang, regex in _LANG_REGEXES.items():
            if regex.search(text):
                results.append(lang.capitalize())
        return results

    def _extract_duration(self, text: str) -> int | None:
        # Match "30 min", "30 mins", "30 minutes", "1 hour", "0.5 hours"
        duration_pattern = re.compile(
            r"\b(\d+(?:\.\d+)?)\s*(min|mins|minute|minutes|hour|hours|hr|hrs)\b", re.IGNORECASE
        )
        match = duration_pattern.search(text)
        if match:
            val = float(match.group(1))
            unit = match.group(2).lower()
            if "hour" in unit or "hr" in unit:
                return int(val * 60)
            return int(val)
        return None

    def _extract_skills(self, text: str) -> list[str]:
        results: list[str] = []
        keywords = ["java", "python", "excel", "typing", "coding", "numerical", "verbal", "reasoning", "communication"]
        for kw in keywords:
            if re.search(rf"\b{kw}\b", text):
                results.append(kw.capitalize())
        return results

    def _extract_competencies(self, text: str) -> list[str]:
        results: list[str] = []
        mappings = {
            "Analytical Thinking": ["analytical", "analysis", "analytical thinking"],
            "Problem Solving": ["problem solving", "critical thinking", "solving problems"],
            "Working with People": ["working with people", "teamwork", "collaboration"],
            "Influencing Others": ["influencing", "persuasion", "influencing others"],
        }
        for canonical, keywords in mappings.items():
            for kw in keywords:
                if kw in text:
                    results.append(canonical)
                    break
        return results

    def _extract_preferred_assessments(self, text: str) -> list[str]:
        results: list[str] = []
        for alias, canonical in _ASSESSMENT_IDENTIFIERS.items():
            # Handle word boundaries around alias
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, text):
                results.append(canonical)
        return list(set(results))
