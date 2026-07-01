"""Recommendation engine formatting and validating retrieved assessment results."""

import logging
from typing import Any
from urllib.parse import urlparse

from app.agent.models import RecommendedAssessment
from app.agent.state import ConversationState
from app.configs.constants import WHITELISTED_DOMAINS

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Formats, validates, and adds reasoning to retrieved SHL assessment candidates."""

    def generate_recommendations(
        self,
        state: ConversationState,
        retrieved_candidates: list[Any],
    ) -> list[RecommendedAssessment]:
        """Validates retrieved candidates, filters duplicates/domain issues, and generates reasoning.

        Args:
            state: Reconstructed ConversationState containing active context filters.
            retrieved_candidates: Retrieved candidates list from RetrievalEngine.

        Returns:
            A list of validated and scored RecommendedAssessment objects (max 10).
        """
        recommendations: list[RecommendedAssessment] = []
        seen_ids: set[str] = set()

        for idx, candidate in enumerate(retrieved_candidates):
            # Enforce maximum 10 recommendations
            if len(recommendations) >= 10:
                break

            # 1. Extract candidate attributes safely (handles both RetrievedCandidate model and dict)
            assessment_id = getattr(candidate, "assessment_id", None) or candidate.get("assessment_id")
            name = getattr(candidate, "name", None) or candidate.get("name")
            url = getattr(candidate, "url", None) or candidate.get("url")
            test_type = getattr(candidate, "test_type", None) or candidate.get("test_type", "Standard")
            duration = getattr(candidate, "duration_mins", None) or candidate.get("duration_mins", 0)
            skills = getattr(candidate, "skills", None) or candidate.get("skills", [])
            competencies = getattr(candidate, "competencies", None) or candidate.get("competencies", [])
            levels = getattr(candidate, "target_level", None) or candidate.get("target_level", [])

            if not name or not url or not assessment_id:
                logger.warning("RecommendationEngine: Missing critical fields for candidate at index %d.", idx)
                continue

            # 2. Check duplicates
            if assessment_id in seen_ids:
                continue
            seen_ids.add(assessment_id)

            # 3. Ensure official URL and whitelisted domains
            if not self._is_official_url(url):
                logger.warning("RecommendationEngine: Candidate '%s' has non-whitelisted URL: %s", name, url)
                continue

            # 4. Generate recommendation reasoning justification
            reasoning = self._generate_reasoning(state, name, test_type, skills, levels)

            rec = RecommendedAssessment(
                name=name,
                test_type=test_type,
                duration_mins=int(duration),
                url=url,
                skills=list(skills),
                competencies=list(competencies),
                seniority_levels=list(levels),
                reasoning=reasoning,
            )
            recommendations.append(rec)

        logger.info("RecommendationEngine: Formatted %d recommendations successfully.", len(recommendations))
        return recommendations

    def _is_official_url(self, url: str) -> bool:
        """Verifies if URL belongs to whitelisted domains.

        Args:
            url: The link to verify.

        Returns:
            True if URL belongs to shl.com or subdomains.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # strip port if present
            if ":" in domain:
                domain = domain.split(":")[0]
            return any(domain == wd or domain.endswith("." + wd) for wd in WHITELISTED_DOMAINS)
        except Exception:
            return False

    def _generate_reasoning(
        self,
        state: ConversationState,
        name: str,
        test_type: str,
        skills: list[str],
        levels: list[str],
    ) -> str:
        """Constructs a statement justifying the recommendation of this assessment.

        Args:
            state: Dialogue context.
            name: Assessment name.
            test_type: Type category.
            skills: Assessed skills.
            levels: seniority levels.

        Returns:
            Reasoning statement string.
        """
        ctx = state.active_context
        reasons = []

        # Match skills
        matching_skills = [s for s in skills if any(s.lower() == cs.lower() for cs in ctx.skills)]
        if matching_skills:
            reasons.append(f"evaluates matching skills in {', '.join(matching_skills)}")

        # Match levels
        matching_levels = [lvl for lvl in levels if any(lvl.lower() == cl.lower() for cl in ctx.candidate_level)]
        if matching_levels:
            reasons.append(f"is designed for {', '.join(matching_levels)} candidates")

        # Match job family
        if ctx.job_family:
            reasons.append(f"aligns with your focus in {', '.join(ctx.job_family)}")

        if reasons:
            reasons_joined = " and ".join(reasons)
            return f"The {name} ({test_type}) is recommended because it {reasons_joined}."

        return (
            f"The {name} is a high-quality {test_type} assessment "
            f"suitable for evaluating candidates on key job competencies."
        )
