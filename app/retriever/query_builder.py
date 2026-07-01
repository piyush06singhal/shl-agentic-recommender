"""Query builder converting raw conversation context into normalized semantic queries."""

import logging
import re

from app.configs.settings import get_settings
from app.retriever.models import MetadataFilters, SearchQuery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Abbreviation expansion table
# ---------------------------------------------------------------------------
_ABBREVIATIONS: dict[str, str] = {
    "sr": "senior",
    "sr.": "senior",
    "jr": "junior",
    "jr.": "junior",
    "dev": "developer",
    "eng": "engineer",
    "mgr": "manager",
    "pm": "project manager",
    "qa": "quality assurance",
    "hr": "human resources",
    "it": "information technology",
    "ux": "user experience",
    "ui": "user interface",
    "swe": "software engineer",
    "be": "backend",
    "fe": "frontend",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "ba": "business analyst",
    "csr": "customer service representative",
    "rep": "representative",
    "ops": "operations",
    "fin": "finance",
    "acct": "accounting",
    "mktg": "marketing",
    "bd": "business development",
}

# Common skill synonym normalizations
_SKILL_SYNONYMS: dict[str, str] = {
    "coding": "programming",
    "scripting": "programming",
    "python3": "python",
    "javascript": "programming",
    "js": "javascript",
    "ts": "typescript",
    "sql": "database",
    "nosql": "database",
    "rest": "api development",
    "restful": "api development",
    "oop": "object oriented programming",
    "leadership": "people management",
    "mgmt": "management",
    "comm": "communication",
    "analytical": "analytical thinking",
    "analysis": "analytical thinking",
    "problem solving": "critical thinking",
}

# Stop words to strip from queries
_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "for", "with", "to", "of", "in",
    "on", "at", "by", "that", "this", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "need", "needs", "looking", "want", "wants", "seeking", "find",
    "help", "please", "can", "could", "would", "should", "we", "our",
    "i", "me", "my", "hire", "hiring", "recruit", "recruiting",
    "assessment", "test", "evaluate", "evaluation",
})


class QueryBuilder:
    """Normalizes and expands raw conversation context into optimized semantic search queries."""

    def build(
        self,
        raw_text: str,
        filters: MetadataFilters | None = None,
        top_k: int | None = None,
    ) -> SearchQuery:
        """Converts raw text + metadata filters into a structured SearchQuery.

        Args:
            raw_text: Raw conversation context or user query.
            filters: Optional structured metadata filters.
            top_k: Maximum candidates to retrieve (defaults to settings value).

        Returns:
            A fully normalized SearchQuery ready for retrieval.
        """
        settings = get_settings()
        filters = filters or MetadataFilters()
        resolved_top_k = min(top_k or settings.top_k, 10)  # Hard cap at 10

        semantic_query = self._build_semantic_query(raw_text, filters)

        logger.debug(
            "QueryBuilder: Raw='%s' → Semantic='%s' | Filters=%s",
            raw_text[:80],
            semantic_query[:120],
            filters.model_dump(exclude_none=True),
        )

        return SearchQuery(
            raw_text=raw_text,
            semantic_query=semantic_query,
            filters=filters,
            top_k=resolved_top_k,
            similarity_threshold=settings.similarity_threshold,
        )

    def _build_semantic_query(self, raw_text: str, filters: MetadataFilters) -> str:
        """Generates optimized semantic query by merging raw text and filter signals.

        Args:
            raw_text: User-provided query text.
            filters: Structured filter constraints.

        Returns:
            A normalized semantic query string.
        """
        # Collect tokens from all signal sources
        tokens: list[str] = []

        # 1. Add level hints from filters first (highest signal)
        tokens.extend(filters.target_level)
        tokens.extend(filters.job_family)
        tokens.extend(filters.test_type)
        tokens.extend(filters.skills[:5])     # limit to prevent bloat
        tokens.extend(filters.competencies[:3])

        # 2. Parse raw text tokens
        raw_tokens = self._tokenize(raw_text)
        tokens.extend(raw_tokens)

        # 3. Expand abbreviations
        expanded = [self._expand_abbreviation(t) for t in tokens]

        # 4. Apply skill synonyms
        normalized = [self._normalize_skill(t) for t in expanded]

        # 5. Remove duplicates while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for token in normalized:
            if token not in seen:
                seen.add(token)
                unique.append(token)

        # 6. Build final human-readable query
        query = " ".join(unique)

        # 7. Append domain anchor to help semantic matching
        if "shl" not in query.lower():
            query = f"{query} assessment"

        return query.strip()

    def _tokenize(self, text: str) -> list[str]:
        """Tokenizes and cleans raw text, removing stop words and short tokens.

        Args:
            text: Input raw text.

        Returns:
            List of meaningful tokens.
        """
        # Lowercase, strip punctuation
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        tokens = text.split()

        # Remove stop words and very short tokens
        return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]

    def _expand_abbreviation(self, token: str) -> str:
        """Replaces known abbreviations with full phrases.

        Args:
            token: Input token.

        Returns:
            Expanded string or the original token.
        """
        return _ABBREVIATIONS.get(token.lower(), token)

    def _normalize_skill(self, token: str) -> str:
        """Replaces known skill synonyms with canonical forms.

        Args:
            token: Input skill/competency token.

        Returns:
            Normalized canonical skill string.
        """
        return _SKILL_SYNONYMS.get(token.lower(), token)
