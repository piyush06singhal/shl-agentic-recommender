"""Clarification engine generating questions for missing hiring context attributes."""

import logging

logger = logging.getLogger(__name__)


class ClarificationEngine:
    """Formulates precise and friendly clarifying questions targeting missing context fields."""

    def generate_clarification_question(self, missing_fields: list[str]) -> str:
        """Inspects missing fields and builds a low-overhead, precise prompt question.

        Args:
            missing_fields: List of missing field keys (e.g. ["skills", "candidate_level"]).

        Returns:
            A recruiter-facing dialogue reply clarifying the missing requirements.
        """
        if not missing_fields:
            return "Could you provide more details on the hiring requirements you would like to evaluate?"

        # De-duplicate
        fields = list(set(missing_fields))

        # Check combinations
        has_family = "job_family" in fields
        has_level = "candidate_level" in fields
        has_skills = "skills" in fields

        # 1. Ask for everything if all critical fields are empty
        if has_family and has_skills and has_level:
            return (
                "To recommend the right SHL assessments, could you specify which job family "
                "you are hiring for (e.g., Technology, Sales, Finance), the seniority level of the candidates "
                "(e.g., Graduate/Entry, Professional, Leadership), and any specific skills you need to measure?"
            )

        # 2. Ask for combination of family and level
        if has_family and has_level:
            return (
                "Could you clarify the job family (e.g. Technology, Sales, Finance) and the seniority level "
                "(e.g. Graduate/Entry, Professional, Leadership) of the candidates you want to evaluate?"
            )

        # 3. Ask for combination of skills and level
        if has_skills and has_level:
            return (
                "Could you specify the seniority level (e.g. Graduate/Entry, Professional, Leadership) "
                "and any specific technical skills (like Java, Python, Excel, or Typing) required for the role?"
            )

        # Ask for combination of family and skills
        if has_family and has_skills:
            return (
                "Could you clarify which job family (e.g. Technology, Sales, Finance) "
                "and any specific technical skills (such as Java, Python, or Excel) "
                "you would like to evaluate?"
            )

        # 4. Individual field queries
        if has_family:
            return (
                "Which job family or role type is this assessment for? "
                "We support Technology, Sales, Management, Finance, and Administration."
            )

        if has_level:
            return (
                "What seniority level are you targeting for this role? "
                "Options include Graduate/Entry, Professional, and Leadership."
            )

        if has_skills:
            return (
                "Are there any specific technical skills (such as coding languages, Excel, or Typing) "
                "or core competencies you want to evaluate?"
            )

        # Fallback question
        return "Could you provide more details about the candidate profile or skills focus you need to screen?"
