"""Keyword matching module scoring candidates based on token overlap with the query."""

import logging
import re

from app.retriever.models import RetrievedCandidate

logger = logging.getLogger(__name__)

# High-value domain keywords that strongly indicate relevance
_DOMAIN_KEYWORDS: frozenset[str] = frozenset({
    "java", "python", "javascript", "typescript", "sql", "excel", "vba",
    "leadership", "management", "sales", "finance", "accounting", "marketing",
    "coding", "programming", "development", "customer service", "service",
    "engineering", "data", "analytics", "communication", "numerical",
    "verbal", "reasoning", "cognitive", "personality", "behaviour",
    "behavioral", "situational", "judgment", "competency", "aptitude",
    "attention", "detail", "checking", "typing", "clerical", "administrative",
    "agile", "scrum", "devops", "cloud", "aws", "azure", "gcp",
    "operations", "logistics", "supply chain", "healthcare", "legal",
    "compliance", "risk", "project", "strategic", "innovation",
})


class KeywordMatcher:
    """Scores retrieved candidates by keyword relevance against the search query."""

    def score_all(
        self,
        candidates: list[RetrievedCandidate],
        query_text: str,
    ) -> list[RetrievedCandidate]:
        """Computes keyword scores for all candidates and attaches them.

        Args:
            candidates: List of candidates to score.
            query_text: The normalized semantic query text.

        Returns:
            Updated candidates with keyword_score populated.
        """
        query_tokens = self._tokenize(query_text)

        scored: list[RetrievedCandidate] = []
        for candidate in candidates:
            score = self._score(candidate, query_tokens, query_text)
            scored.append(candidate.model_copy(update={"keyword_score": round(score, 4)}))

        return scored

    def _score(
        self,
        candidate: RetrievedCandidate,
        query_tokens: set[str],
        raw_query: str,
    ) -> float:
        """Computes keyword relevance score for a single candidate.

        Scoring signals:
        - Exact name match: +0.5 bonus
        - Token overlap in name: proportional
        - Token overlap in skills: proportional (weighted 0.8x)
        - Token overlap in job family + competencies: proportional (weighted 0.5x)
        - Domain keyword hit: +0.1 bonus per hit (capped)

        Args:
            candidate: The candidate to score.
            query_tokens: Set of tokens from the normalized query.
            raw_query: The original raw query text for exact-name matching.

        Returns:
            A float score clamped to [0.0, 1.0].
        """
        score = 0.0

        # 1. Exact name match (case-insensitive)
        if candidate.name.lower() in raw_query.lower():
            score += 0.5

        # 2. Name token overlap
        name_tokens = self._tokenize(candidate.name)
        if name_tokens and query_tokens:
            overlap = len(name_tokens & query_tokens) / len(name_tokens | query_tokens)
            score += overlap * 0.4

        # 3. Skills token overlap
        skills_text = " ".join(candidate.skills)
        skills_tokens = self._tokenize(skills_text)
        if skills_tokens and query_tokens:
            overlap = len(skills_tokens & query_tokens) / max(len(skills_tokens | query_tokens), 1)
            score += overlap * 0.3

        # 4. Job family + competency overlap
        jf_text = " ".join(candidate.job_family + candidate.competencies)
        jf_tokens = self._tokenize(jf_text)
        if jf_tokens and query_tokens:
            overlap = len(jf_tokens & query_tokens) / max(len(jf_tokens | query_tokens), 1)
            score += overlap * 0.2

        # 5. Domain keyword bonus
        domain_hits = len(query_tokens & _DOMAIN_KEYWORDS & (name_tokens | skills_tokens))
        score += min(domain_hits * 0.1, 0.3)

        return min(score, 1.0)

    def _tokenize(self, text: str) -> set[str]:
        """Tokenizes text into a lowercase set of meaningful words.

        Args:
            text: Input text.

        Returns:
            Set of lowercase tokens (len > 1).
        """
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        return {t for t in text.split() if len(t) > 1}
