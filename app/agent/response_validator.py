"""Response validator auditing outgoing ChatResponses for schema compliance and safety."""

import logging
from urllib.parse import urlparse

from app.agent.models import ChatResponse
from app.configs.constants import WHITELISTED_DOMAINS

logger = logging.getLogger(__name__)


class ResponseValidator:
    """Ensures outgoing ChatResponse schema structures and fields conform to system requirements."""

    def validate_response(self, response: ChatResponse) -> ChatResponse:
        """Audits a compiled ChatResponse, raising ValueError or sanitizing if violations are found.

        Checks:
        - Max 10 recommendations.
        - Non-duplicate recommendations.
        - All URLs belong to shl.com or subdomains.
        - Structure matches ChatResponse.

        Args:
            response: The candidate ChatResponse to validate.

        Returns:
            The validated and potentially sanitized ChatResponse.

        Raises:
            ValueError: If critical constraints are violated.
        """
        # 1. Check max 10 recommendations limit
        if len(response.recommendations) > 10:
            logger.warning("ResponseValidator: Truncating recommendations list exceeding 10 items limit.")
            response.recommendations = response.recommendations[:10]

        # 2. Check duplicates and whitelisted URLs
        cleaned_recs = []
        seen_names = set()

        for idx, rec in enumerate(response.recommendations):
            # Check empty names
            if not rec.name or not rec.name.strip():
                raise ValueError(f"Recommendation at index {idx} has an empty name.")

            # Deduplicate by name
            norm_name = rec.name.strip().lower()
            if norm_name in seen_names:
                logger.warning("ResponseValidator: Found duplicate recommendation name '%s' — pruning.", rec.name)
                continue
            seen_names.add(norm_name)

            # URL validation
            if not rec.url:
                raise ValueError(f"Recommendation '{rec.name}' is missing URL.")

            # Validate domain matches SHL whitelist
            parsed = urlparse(rec.url)
            domain = parsed.netloc.lower()
            if ":" in domain:
                domain = domain.split(":")[0]

            is_valid_domain = any(domain == wd or domain.endswith("." + wd) for wd in WHITELISTED_DOMAINS)
            if not is_valid_domain:
                raise ValueError(f"Recommendation '{rec.name}' has non-whitelisted URL: {rec.url}")

            cleaned_recs.append(rec)

        response.recommendations = cleaned_recs

        # Ensure reply exists
        if not response.reply or not response.reply.strip():
            raise ValueError("Response 'reply' text is empty.")

        return response
