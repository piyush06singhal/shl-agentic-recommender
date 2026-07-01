"""Refinement engine tracking updates and modifications to active constraints."""

import logging

from app.agent.models import ExtractedContext

logger = logging.getLogger(__name__)


class RefinementEngine:
    """Manages updates, replacements, and constraint refinements across dialogue turns."""

    def track_refinement_changes(
        self,
        previous_context: ExtractedContext,
        current_context: ExtractedContext,
    ) -> list[str]:
        """Compares previous and current context constraints to list the refinements made.

        Args:
            previous_context: Context built before the current turn.
            current_context: Newly built context from the current turn.

        Returns:
            A list of modifications logs strings (e.g., "Skills replaced: ['Java'] -> ['Python']").
        """
        changes: list[str] = []

        # Skills replacement check
        if previous_context.skills != current_context.skills:
            changes.append(f"Skills updated: {previous_context.skills} → {current_context.skills}")

        # Job family replacement check
        if previous_context.job_family != current_context.job_family:
            changes.append(f"Job Family updated: {previous_context.job_family} → {current_context.job_family}")

        # Levels check
        if previous_context.candidate_level != current_context.candidate_level:
            changes.append(
                f"Seniority Level updated: {previous_context.candidate_level} "
                f"→ {current_context.candidate_level}"
            )

        # Duration check
        if previous_context.max_duration_mins != current_context.max_duration_mins:
            changes.append(
                f"Duration updated: {previous_context.max_duration_mins} "
                f"→ {current_context.max_duration_mins}"
            )

        # Preferred checks
        if previous_context.preferred_assessments != current_context.preferred_assessments:
            changes.append(
                f"Preferred Assessments updated: {previous_context.preferred_assessments} "
                f"→ {current_context.preferred_assessments}"
            )

        if changes:
            logger.info("RefinementEngine: Detected context modifications: %s", ", ".join(changes))

        return changes
