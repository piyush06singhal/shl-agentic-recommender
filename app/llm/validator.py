"""LLM response validator auditing structured outputs for domain and domain linking rules."""

import logging
from urllib.parse import urlparse

from app.configs.constants import WHITELISTED_DOMAINS
from app.llm.models import LLMOutput

logger = logging.getLogger(__name__)


class LLMResponseValidator:
    """Verifies grounding integrity of generated LLM outputs against safety standards."""

    def validate(self, output: LLMOutput, allowed_assessment_names: list[str] | None = None) -> LLMOutput:
        """Audits LLM output, raising ValueError or filtering invalid URLs/names.

        Args:
            output: The parsed LLMOutput.
            allowed_assessment_names: Whitelist of valid assessment names (usually retrieved).

        Returns:
            The validated and sanitized LLMOutput.
        """
        # Ensure max 10 recommendations
        if len(output.recommendations) > 10:
            logger.warning("LLMResponseValidator: Truncating list exceeding 10 recommendations.")
            output.recommendations = output.recommendations[:10]

        cleaned_recs = []
        seen_names = set()

        for rec in output.recommendations:
            if not rec.name or not rec.name.strip():
                continue

            name_lower = rec.name.strip().lower()

            # 1. Deduplicate by name
            if name_lower in seen_names:
                continue
            seen_names.add(name_lower)

            # 2. Check if name is in the retrieved/allowed list (if provided)
            if allowed_assessment_names:
                allowed_lowercased = {n.lower() for n in allowed_assessment_names}
                if name_lower not in allowed_lowercased:
                    logger.warning("LLMResponseValidator: Pruned hallucinated assessment name: %s", rec.name)
                    continue

            # 3. Whitelisted URL domain check
            if not rec.url:
                continue

            parsed = urlparse(rec.url)
            domain = parsed.netloc.lower()
            if ":" in domain:
                domain = domain.split(":")[0]

            is_valid = any(domain == wd or domain.endswith("." + wd) for wd in WHITELISTED_DOMAINS)
            if not is_valid:
                logger.warning("LLMResponseValidator: Pruned non-whitelisted URL domain: %s", rec.url)
                continue

            cleaned_recs.append(rec)

        output.recommendations = cleaned_recs
        return output
