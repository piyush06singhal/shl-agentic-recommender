"""Context builder assembling LLM-ready text blocks from ranked candidates."""

import logging

from app.retriever.models import RetrievedCandidate

logger = logging.getLogger(__name__)

# Block separator used between assessments in the joined context string
_BLOCK_SEPARATOR = "\n" + "—" * 60 + "\n"


class ContextBuilder:
    """Formats ranked RetrievedCandidate objects into structured LLM context blocks."""

    def build(self, candidates: list[RetrievedCandidate]) -> tuple[list[str], str]:
        """Assembles context blocks and a single joined context string.

        Each block contains exactly:
            Official Name, Description, Assessment Type, Skills,
            Competencies, Duration, Candidate Level, Languages, Official URL.

        Args:
            candidates: Ordered list of top-K candidates.

        Returns:
            A tuple of (list of individual block strings, joined context string).
        """
        if not candidates:
            logger.warning("ContextBuilder: No candidates provided — returning empty context.")
            return [], ""

        blocks: list[str] = []
        for candidate in candidates:
            block = self._format_block(candidate)
            blocks.append(block)

        context_text = _BLOCK_SEPARATOR.join(blocks)

        logger.debug(
            "ContextBuilder: Built %d context blocks (%d chars total).",
            len(blocks),
            len(context_text),
        )
        return blocks, context_text

    def _format_block(self, candidate: RetrievedCandidate) -> str:
        """Formats a single candidate into a structured text block.

        Args:
            candidate: A single retrieved and ranked assessment.

        Returns:
            A formatted multi-line string block.
        """
        rank_label = f"[{candidate.rank}]" if candidate.rank > 0 else "[-]"

        skills_text = ", ".join(candidate.skills) if candidate.skills else "Not specified"
        competencies_text = ", ".join(candidate.competencies) if candidate.competencies else "Not specified"
        levels_text = ", ".join(candidate.target_level) if candidate.target_level else "Not specified"
        languages_text = ", ".join(candidate.languages) if candidate.languages else "Not specified"
        job_family_text = ", ".join(candidate.job_family) if candidate.job_family else "Not specified"

        remote_label = "Yes" if candidate.remote_testing else "No"
        adaptive_label = "Yes" if candidate.adaptive else "No"

        lines = [
            f"{rank_label} {candidate.name}",
            f"Type: {candidate.test_type}",
            f"Job Families: {job_family_text}",
            f"Description: {candidate.description}",
            f"Skills: {skills_text}",
            f"Competencies: {competencies_text}",
            f"Duration: {candidate.duration_mins} minutes",
            f"Candidate Level: {levels_text}",
            f"Languages: {languages_text}",
            f"Remote Testing: {remote_label}",
            f"Adaptive: {adaptive_label}",
            f"URL: {candidate.url}",
        ]

        return "\n".join(lines)

    def build_comparison_block(self, candidates: list[RetrievedCandidate]) -> str:
        """Formats candidates side-by-side in a comparison-friendly layout.

        Args:
            candidates: List of candidates to compare.

        Returns:
            A formatted comparison string for the LLM.
        """
        if not candidates:
            return ""

        sections = ["=== ASSESSMENT COMPARISON ===\n"]
        for candidate in candidates:
            sections.append(self._format_block(candidate))

        return _BLOCK_SEPARATOR.join(sections)
