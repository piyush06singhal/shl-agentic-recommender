"""Comparison engine generating structured side-by-side metadata comparisons."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ComparisonEngine:
    """Generates structured comparisons between multiple SHL assessments."""

    def compare_assessments(self, assessments: list[Any]) -> str:
        """Constructs a side-by-side markdown comparison block of the provided assessments.

        Args:
            assessments: A list of candidate models or dictionaries.

        Returns:
            A formatted markdown comparison string, or empty string.
        """
        if not assessments:
            return "No assessments provided for comparison."

        if len(assessments) < 2:
            return "At least two assessments are required to perform a comparison."

        # Parse candidate values safely
        records: list[dict[str, Any]] = []
        for c in assessments:
            record = {
                "name": getattr(c, "name", None) or c.get("name", "Unknown Assessment"),
                "type": getattr(c, "test_type", None) or c.get("test_type", "Not Available"),
                "purpose": getattr(c, "description", None) or c.get("description", "Not Available"),
                "job_family": getattr(c, "job_family", None) or c.get("job_family", []),
                "levels": getattr(c, "target_level", None) or c.get("target_level", []),
                "duration": getattr(c, "duration_mins", None) or c.get("duration_mins", 0),
                "skills": getattr(c, "skills", None) or c.get("skills", []),
                "languages": getattr(c, "languages", None) or c.get("languages", []),
                "competencies": getattr(c, "competencies", None) or c.get("competencies", []),
                "adaptive": getattr(c, "adaptive", None) or c.get("adaptive", False),
            }
            records.append(record)

        lines = ["Here is a side-by-side comparison of the requested assessments:\n"]

        # Build comparison grid/sections
        for rec in records:
            name = rec["name"]
            lines.append(f"### {name}")

            # 1. Type
            lines.append(f"- **Assessment Type**: {rec['type']}")

            # 2. Purpose/Description
            lines.append(f"- **Purpose**: {rec['purpose']}")

            # 3. Target Role & Levels
            job_families = ", ".join(rec["job_family"]) if rec["job_family"] else "Not Available"
            levels = ", ".join(rec["levels"]) if rec["levels"] else "Not Available"
            lines.append(f"- **Target Job Sectors**: {job_families}")
            lines.append(f"- **Seniority Level**: {levels}")

            # 4. Duration
            dur_str = f"{rec['duration']} minutes" if rec["duration"] > 0 else "Not Available"
            lines.append(f"- **Test Duration**: {dur_str}")

            # 5. Skills
            skills_str = ", ".join(rec["skills"]) if rec["skills"] else "Not Available"
            lines.append(f"- **Skills Evaluated**: {skills_str}")

            # 6. Competencies
            comp_str = ", ".join(rec["competencies"]) if rec["competencies"] else "Not Available"
            lines.append(f"- **Competencies Audited**: {comp_str}")

            # 7. Languages
            lang_str = ", ".join(rec["languages"]) if rec["languages"] else "Not Available"
            lines.append(f"- **Languages Supported**: {lang_str}")

            # 8. Strengths/Features
            features = []
            if rec["adaptive"]:
                features.append("Adaptive questioning format tailored dynamically to candidate responses.")
            if rec["duration"] > 0 and rec["duration"] <= 20:
                features.append("Short duration optimized for early candidate funnel screening.")
            if len(rec["competencies"]) >= 2:
                features.append("Audits multi-dimensional behavioural competencies for role suitability.")

            features_str = (
                " ".join(features)
                if features
                else "Standard test format administering unified content structures."
            )
            lines.append(f"- **Key Strengths**: {features_str}\n")

        return "\n".join(lines)
