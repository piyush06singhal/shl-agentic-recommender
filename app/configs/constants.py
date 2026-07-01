"""Application-wide constants configurations database."""

from typing import Final

# API Version parameters
API_VERSION: Final[str] = "1.0.0"
API_PREFIX: Final[str] = "/api/v1"

# Conversational processing limits
DEFAULT_MAX_CONVERSATION_TURNS: Final[int] = 8
DEFAULT_MAX_RECOMMENDATIONS: Final[int] = 10
MAX_MESSAGE_CHARACTER_LENGTH: Final[int] = 2000
CONTEXT_TRUNCATION_LIMIT_CHARS: Final[int] = 15000

# whitelisted domain regex strings
WHITELISTED_DOMAINS: Final[list[str]] = [
    "shl.com",
    "www.shl.com",
]

# Supported system user turn intents
INTENT_GREETING: Final[str] = "Greeting"
INTENT_CLARIFICATION: Final[str] = "Clarification"
INTENT_RECOMMENDATION: Final[str] = "Recommendation"
INTENT_REFINEMENT: Final[str] = "Refinement"
INTENT_COMPARISON: Final[str] = "Comparison"
INTENT_OUT_OF_SCOPE: Final[str] = "Out-of-Scope"
INTENT_PROMPT_INJECTION: Final[str] = "Prompt Injection"
INTENT_CONVERSATION_END: Final[str] = "Conversation End"
INTENT_UNKNOWN: Final[str] = "Unknown"

SUPPORTED_INTENTS: Final[list[str]] = [
    INTENT_GREETING,
    INTENT_CLARIFICATION,
    INTENT_RECOMMENDATION,
    INTENT_REFINEMENT,
    INTENT_COMPARISON,
    INTENT_OUT_OF_SCOPE,
    INTENT_PROMPT_INJECTION,
    INTENT_CONVERSATION_END,
    INTENT_UNKNOWN,
]

# Assessment categories/modalities
ASSESSMENT_TYPE_COGNITIVE: Final[str] = "Cognitive"
ASSESSMENT_TYPE_PERSONALITY: Final[str] = "Personality"
ASSESSMENT_TYPE_SKILLS: Final[str] = "Skills"
ASSESSMENT_TYPE_LANGUAGE: Final[str] = "Language"

SUPPORTED_ASSESSMENT_TYPES: Final[list[str]] = [
    ASSESSMENT_TYPE_COGNITIVE,
    ASSESSMENT_TYPE_PERSONALITY,
    ASSESSMENT_TYPE_SKILLS,
    ASSESSMENT_TYPE_LANGUAGE,
]

# Job family categories
JOB_FAMILY_TECH: Final[str] = "Technology"
JOB_FAMILY_SALES: Final[str] = "Sales"
JOB_FAMILY_MGMT: Final[str] = "Management"
JOB_FAMILY_FINANCE: Final[str] = "Finance"
JOB_FAMILY_ADMIN: Final[str] = "Administration"

SUPPORTED_JOB_FAMILIES: Final[list[str]] = [
    JOB_FAMILY_TECH,
    JOB_FAMILY_SALES,
    JOB_FAMILY_MGMT,
    JOB_FAMILY_FINANCE,
    JOB_FAMILY_ADMIN,
]

# Target Seniority Levels
LEVEL_ENTRY: Final[str] = "Graduate/Entry"
LEVEL_PROFESSIONAL: Final[str] = "Professional"
LEVEL_LEADERSHIP: Final[str] = "Leadership"

SUPPORTED_CANDIDATE_LEVELS: Final[list[str]] = [
    LEVEL_ENTRY,
    LEVEL_PROFESSIONAL,
    LEVEL_LEADERSHIP,
]
