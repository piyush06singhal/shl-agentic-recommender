"""Active context builder reconstructing hiring requirements state across turns."""

import logging

from app.agent.extractor import ContextExtractor
from app.agent.models import AgentIntent, ExtractedContext
from app.schemas.request import Message

logger = logging.getLogger(__name__)


class ActiveContextBuilder:
    """Reconstructs, validates, and refines hiring context state from dialogue histories."""

    def __init__(self, extractor: ContextExtractor | None = None) -> None:
        self.extractor = extractor or ContextExtractor()

    def rebuild_context(
        self,
        messages: list[Message],
        intents: list[AgentIntent],
    ) -> ExtractedContext:
        """Reconstructs the active requirements context chronologically from parsed messages.

        Enforces the "Latest Value Wins" logic for replacements and refinements.

        Args:
            messages: Pre-validated chronological list of dialogue messages.
            intents: Chronological list of user intents matching user turns.

        Returns:
            The final resolved ExtractedContext.
        """
        context = ExtractedContext()

        user_turn_idx = 0
        for msg in messages:
            if msg.role != "user":
                continue

            # Extract requirements from this specific turn
            turn_ctx = self.extractor.extract_from_text(msg.content)
            intent = intents[user_turn_idx] if user_turn_idx < len(intents) else AgentIntent.UNKNOWN
            user_turn_idx += 1

            # Determine whether to replace or merge
            is_refinement = (intent == AgentIntent.REFINEMENT)

            # Update job family
            if turn_ctx.job_family:
                context.job_family = turn_ctx.job_family

            # Update candidate level
            if turn_ctx.candidate_level:
                context.candidate_level = turn_ctx.candidate_level

            # Update assessment type
            if turn_ctx.assessment_type:
                context.assessment_type = turn_ctx.assessment_type

            # Update duration
            if turn_ctx.max_duration_mins is not None:
                context.max_duration_mins = turn_ctx.max_duration_mins

            # Update preferred assessments
            if turn_ctx.preferred_assessments:
                context.preferred_assessments = turn_ctx.preferred_assessments

            # Update comparison targets
            if turn_ctx.comparison_targets:
                context.comparison_targets = turn_ctx.comparison_targets

            # Update skills (Latest Value Wins unless explicitly adding)
            if turn_ctx.skills:
                content_lower = msg.content.lower()
                is_adding = any(w in content_lower for w in ["also", "and", "addition"]) and not is_refinement
                if is_adding and context.skills:
                    # Append unique skills
                    context.skills = list(set(context.skills + turn_ctx.skills))
                else:
                    context.skills = turn_ctx.skills

            # Update competencies
            if turn_ctx.competencies:
                content_lower = msg.content.lower()
                is_adding = any(w in content_lower for w in ["also", "and", "addition"]) and not is_refinement
                if is_adding and context.competencies:
                    context.competencies = list(set(context.competencies + turn_ctx.competencies))
                else:
                    context.competencies = turn_ctx.competencies

            # Update languages
            if turn_ctx.languages:
                content_lower = msg.content.lower()
                is_adding = any(w in content_lower for w in ["also", "and", "addition"]) and not is_refinement
                if is_adding and context.languages:
                    context.languages = list(set(context.languages + turn_ctx.languages))
                else:
                    context.languages = turn_ctx.languages

        logger.debug("ActiveContextBuilder: Rebuilt context details: %s", context.model_dump())
        return context

    def detect_missing_fields(self, context: ExtractedContext) -> list[str]:
        """Identifies what critical information is missing to issue recommendations.

        To perform high-quality retrieval, we need at least a role definition or skills focus.

        Args:
            context: Reconstructed ExtractedContext.

        Returns:
            A list of missing field names (e.g. ["skills", "candidate_level", "job_family"]).
        """
        missing: list[str] = []

        # If job_family, skills, and preferred_assessments are all missing, we have no search target.
        if not context.job_family and not context.skills and not context.preferred_assessments:
            missing.append("job_family")
            missing.append("skills")

        # Candidate level is useful to filter/clarify if not specified.
        if not context.candidate_level:
            missing.append("candidate_level")

        return missing

    def has_sufficient_context(self, context: ExtractedContext) -> bool:
        """Determines if the gathered criteria are enough to proceed with retrieval.

        Args:
            context: Reconstructed ExtractedContext.

        Returns:
            True if search filters/skills target is sufficiently specified.
        """
        # If we have a preferred assessment or specific skills or job family, we can retrieve.
        if context.preferred_assessments:
            return True
        if context.skills or context.job_family:
            return True
        return False
