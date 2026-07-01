"""Unit tests validating parser, cleaner, normalizer, validator, deduplicator, and manager blocks."""

from uuid import UUID

import pytest

from app.catalog.cleaner import CatalogCleaner
from app.catalog.deduplicator import CatalogDeduplicator
from app.catalog.manager import CatalogManager
from app.catalog.models import CatalogAssessment, ScrapedAssessment
from app.catalog.normalizer import CatalogNormalizer
from app.catalog.parser import CatalogParser
from app.catalog.validator import CatalogValidator
from app.schemas.response import Assessment

# --- Fixtures ---

@pytest.fixture
def sample_html_detail() -> str:
    """Provides a sample HTML string mimicking an SHL product detail page layout."""
    return """
    <html>
        <head>
            <title>SHL Inductive Reasoning Test | SHL solutions</title>
            <meta name="description"
                  content="An interactive logical ability test auditing inductive and critical thinking.">
        </head>
        <body>
            <h1>SHL Inductive Reasoning Test</h1>
            <table>
                <tr>
                    <td>Assessment Type:</td>
                    <td>Cognitive</td>
                </tr>
                <tr>
                    <td>Job Family:</td>
                    <td>Technology, Finance, Administration</td>
                </tr>
                <tr>
                    <td>Target Level:</td>
                    <td>Graduate/Entry, Professional</td>
                </tr>
            </table>
            <div>
                <p>Duration - 18 minutes</p>
                <p>Languages: English, French, German</p>
                <p>Skills tested - Logical processing, Inductive leap, Concept mappings</p>
                <p>Competencies - Analyzing, Formulating Concepts</p>
                <p>Remote testing support: Yes</p>
                <p>Adaptive testing - Yes</p>
                <p>Category: Cognitive Test</p>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_scraped_records() -> list[ScrapedAssessment]:
    """Provides a list of cleaned ScrapedAssessment records."""
    return [
        ScrapedAssessment(
            name="SHL Personality Profile",
            url="https://www.shl.com/en/assessments/personality/",
            description="Measures critical personality behaviors in workplace.",
            test_type="Personality",
            job_family="Sales, Management",
            target_level="Professional, Leadership",
            duration="25 minutes",
            languages="English, French",
            skills="Work styles, behavioral fit",
            competencies="Leading, Working with people",
            remote_testing="Yes",
            adaptive="No",
            category="Personality",
        ),
        # Duplicate of above (same name, different URL)
        ScrapedAssessment(
            name="SHL Personality Profile",
            url="https://www.shl.com/en/assessments/personality-alt/",
            description="Measures critical personality behaviors in workplace.",
            test_type="Personality",
            job_family="Sales, Management",
            target_level="Professional, Leadership",
            duration="25 minutes",
            languages="English, French",
            skills="Work styles, behavioral fit",
            competencies="Leading, Working with people",
            remote_testing="Yes",
            adaptive="No",
            category="Personality",
        ),
        # Duplicate of first (different name, same URL)
        ScrapedAssessment(
            name="SHL OPQ Personality",
            url="https://www.shl.com/en/assessments/personality/",
            description="Measures critical personality behaviors in workplace.",
            test_type="Personality",
            job_family="Sales, Management",
            target_level="Professional, Leadership",
            duration="25 minutes",
            languages="English, French",
            skills="Work styles, behavioral fit",
            competencies="Leading, Working with people",
            remote_testing="Yes",
            adaptive="No",
            category="Personality",
        ),
    ]


# --- Test Cases ---

def test_parser_extracts_all_metadata(sample_html_detail: str) -> None:
    """Verifies CatalogParser successfully extracts metadata attributes from HTML templates."""
    parser = CatalogParser()
    scraped = parser.parse_page(sample_html_detail, "https://www.shl.com/en/assessments/cognitive/inductive/")

    assert scraped.name == "SHL Inductive Reasoning Test"
    assert scraped.url == "https://www.shl.com/en/assessments/cognitive/inductive/"
    assert scraped.description == "An interactive logical ability test auditing inductive and critical thinking."
    assert scraped.test_type == "Cognitive"
    assert scraped.job_family == "Technology, Finance, Administration"
    assert scraped.target_level == "Graduate/Entry, Professional"
    assert scraped.duration == "18 minutes"
    assert scraped.languages == "English, French, German"
    assert scraped.skills == "Logical processing, Inductive leap, Concept mappings"
    assert scraped.competencies == "Analyzing, Formulating Concepts"
    assert scraped.remote_testing == "Yes"
    assert scraped.adaptive == "Yes"
    assert scraped.category == "Cognitive Test"


def test_cleaner_normalizes_text() -> None:
    """Verifies CatalogCleaner cleans text layout whitespace and smart quotes."""
    cleaner = CatalogCleaner()

    assert cleaner.clean_text("Hello    World  ") == "Hello World"
    assert cleaner.clean_text("<p>Hello &ldquo;World&rdquo;</p>") == 'Hello "World"'

    raw = ScrapedAssessment(
        name="  SHL   Test  ",
        url="https://www.shl.com/test",
        description="Paragraph with   smart   quotes.",
    )
    cleaned = cleaner.clean_metadata(raw)
    assert cleaned.name == "SHL Test"
    assert cleaned.description == "Paragraph with smart quotes."


def test_normalizer_standardizes_types() -> None:
    """Verifies CatalogNormalizer maps and parses raw values into clean catalog schemas."""
    normalizer = CatalogNormalizer()

    scraped = ScrapedAssessment(
        name="SHL Inductive reasoning",
        url="https://www.shl.com/inductive",
        description="A cognitive logic reasoning assessment.",
        test_type="Cognitive Aptitude",
        job_family="Software / Tech, finance industry",
        target_level="experienced professionals, executives",
        duration="0.5 hr",
        languages="English / German, Spanish",
        skills="data analysis • logical inference",
        competencies="Analyzing, Formulating Concepts",
        remote_testing="Yes",
        adaptive="y",
        category="Logic",
    )

    normalized = normalizer.normalize_assessment(scraped)

    assert isinstance(normalized.id, UUID)
    assert normalized.test_type == "Cognitive"
    assert normalized.duration_mins == 30
    assert "Technology" in normalized.job_family
    assert "Finance" in normalized.job_family
    assert "Professional" in normalized.target_level
    assert "Leadership" in normalized.target_level
    assert "English" in normalized.languages
    assert "German" in normalized.languages
    assert "Spanish" in normalized.languages
    assert "Data analysis" in normalized.skills
    assert normalized.remote_testing is True
    assert normalized.adaptive is True


def test_validator_detects_invalid_values() -> None:
    """Verifies CatalogValidator flags required fields, bad durations, and non-whitelisted domains."""
    validator = CatalogValidator()

    # Clean valid record
    valid = CatalogAssessment(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        name="SHL Java test",
        url="https://www.shl.com/java",
        test_type="Cognitive",
        description="A programming skills test.",
        duration_mins=45,
    )
    assert len(validator.validate_assessment(valid)) == 0

    # Non-whitelisted domain URL
    invalid_url = valid.model_copy(update={"url": "https://www.hackersite.com/java"})
    assert any("not whitelisted" in err for err in validator.validate_assessment(invalid_url))

    # Negative duration
    invalid_duration = valid.model_copy(update={"duration_mins": -5})
    assert any("duration" in err for err in validator.validate_assessment(invalid_duration))

    # Missing description
    invalid_desc = valid.model_copy(update={"description": "  "})
    assert any("description" in err for err in validator.validate_assessment(invalid_desc))


def test_deduplicator_removes_duplicates(mock_scraped_records: list[ScrapedAssessment]) -> None:
    """Verifies CatalogDeduplicator preserves uniqueness of names and URLs."""
    normalizer = CatalogNormalizer()
    deduplicator = CatalogDeduplicator()

    normalized = [normalizer.normalize_assessment(r) for r in mock_scraped_records]

    assert len(normalized) == 3

    # Run deduplication
    deduped = deduplicator.deduplicate(normalized)

    # Expected: The duplicate name profile and duplicate URL profile get removed.
    # Returns only 1 record (the first unique personality profile)
    assert len(deduped) == 1
    assert deduped[0].name == "SHL Personality Profile"


def test_catalog_manager_searches() -> None:
    """Verifies CatalogManager parses catalog list and serves lookups."""
    # We will initialize manager with a custom test catalog list by stubbing data cache
    manager = CatalogManager()

    # Pre-populate cache for testing
    item = Assessment(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="Java Skill Screening",
        url="https://www.shl.com/en/assessments/skills/java/",
        test_type="Cognitive",
        description="Verifies algorithmic capability in Java programming.",
        job_family=["Technology"],
        target_level=["Professional"],
        duration_mins=45,
        languages=["English"],
    )

    manager._catalog_list = [item]
    manager._catalog_cache[item.name.lower().strip()] = item
    manager._catalog_cache[item.url.lower().strip()] = item

    assert manager.get_assessment_by_name("Java Skill Screening") == item
    assert manager.get_assessment_by_name("java skill screening ") == item
    assert manager.get_assessment_by_url("https://www.shl.com/en/assessments/skills/java/") == item

    # Search checks
    assert item in manager.search_assessments("Java")
    assert item in manager.search_assessments("algorithmic")
    assert len(manager.search_assessments("Python")) == 0
