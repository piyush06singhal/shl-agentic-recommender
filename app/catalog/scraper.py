"""Catalog scraper module implementing robust page downloaders with retry patterns."""

import logging
import time

import requests
from bs4 import BeautifulSoup

from app.configs.settings import get_settings

logger = logging.getLogger(__name__)


class CatalogScraper:
    """Robust web crawler designed to scrape SHL solution pages with backoffs and timeouts."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
        self.timeout = self.settings.api_timeout

    def fetch_url(self, url: str, max_retries: int = 3, backoff_factor: float = 2.0) -> str:
        """Fetches the HTML content of a URL with connection retries and exponential backoffs.

        Args:
            url: The page web URL path to query.
            max_retries: The max number of retries before failure.
            backoff_factor: Multiplier for backoff delay.

        Returns:
            The raw HTML content string of the page.
        """
        delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                logger.info("Fetching URL (attempt %d/%d): %s", attempt, max_retries, url)
                response = requests.get(url, headers=self.headers, timeout=self.timeout)

                # Check status codes
                if response.status_code == 429:
                    logger.warning("Received HTTP 429 Rate Limit. Backing off...")
                else:
                    response.raise_for_status()

                return response.text
            except requests.RequestException as e:
                if attempt == max_retries:
                    logger.error("Failed to download page %s after %d retries: %s", url, max_retries, e)
                    raise
                logger.warning(
                    "Attempt %d failed for %s: %s. Retrying in %.2fs...",
                    attempt,
                    url,
                    e,
                    delay,
                )
                time.sleep(delay)
                delay *= backoff_factor

        raise requests.RequestException(f"Failed to fetch {url}")

    def scrape_catalog_index(self, index_url: str) -> list[str]:
        """Queries catalog listings index pages and extracts individual assessment links.

        Args:
            index_url: Main index url of SHL solutions.

        Returns:
            List of absolute URLs to detailed assessment pages.
        """
        try:
            html = self.fetch_url(index_url)
            soup = BeautifulSoup(html, "html.parser")
            links: list[str] = []

            # Scrape solution anchors matching typical SHL catalog paths
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"]
                if "/assessments/" in href or "/solutions/" in href:
                    # Construct absolute paths
                    if href.startswith("/"):
                        href = f"https://www.shl.com{href}"
                    if href.startswith("https://www.shl.com") and href not in links:
                        links.append(href)

            logger.info("Scraped %d assessment links from index.", len(links))
            return links
        except Exception as e:
            logger.error("Error scraping catalog index %s: %s", index_url, e)
            return []

    def get_mock_assessments(self) -> list[dict[str, str]]:
        """Provides static mock solutions metadata profiles to support offline mode runs."""
        logger.info("Offline mode active: Generating default mock catalog data profiles...")
        return [
            {
                "name": "SHL OPQ32 Personality Assessment",
                "url": "https://www.shl.com/en/assessments/personality/opq/",
                "description": (
                    "The Occupational Personality Questionnaire (OPQ32) is a premier assessment "
                    "measuring 32 key personality characteristics that influence job performance. "
                    "Highly predictive of workplace behavior and fit."
                ),
                "test_type": "Personality",
                "job_family": "Technology, Sales, Management, Finance",
                "target_level": "Professional, Leadership",
                "duration": "25 mins",
                "languages": "English, French, German, Spanish, Japanese",
                "skills": "Behavioral Fit, Workplace Styles, Leadership Potential",
                "competencies": "Working with People, Leading and Deciding, Adapting and Coping",
                "remote_testing": "Yes",
                "adaptive": "No",
                "category": "Personality Profile",
            },
            {
                "name": "SHL Cognitive Ability Test (Verify)",
                "url": "https://www.shl.com/en/assessments/cognitive-ability/verify/",
                "description": (
                    "A suite of cognitive capability audits testing critical numerical, verbal, "
                    "and inductive reasoning competencies. Essential for predicting task performance "
                    "across complex role profiles."
                ),
                "test_type": "Cognitive",
                "job_family": "Technology, Finance, Administration",
                "target_level": "Graduate/Entry, Professional",
                "duration": "18 minutes",
                "languages": "English, German, Spanish, Chinese",
                "skills": "Numerical Analysis, Logical Thinking, Inductive Reasoning, Verbal Reasoning",
                "competencies": "Analyzing, Formulating Concepts, Problem Solving",
                "remote_testing": "Yes",
                "adaptive": "Yes",
                "category": "Cognitive Test",
            },
            {
                "name": "SHL Java Developer Skills Test",
                "url": "https://www.shl.com/en/assessments/skills/java-developer/",
                "description": (
                    "An interactive coding assessment specifically designed for screening software "
                    "engineers on Java core fundamentals, multi-threading, database mappings, and memory "
                    "management efficiency."
                ),
                "test_type": "Skills",
                "job_family": "Technology",
                "target_level": "Professional",
                "duration": "0.5 hours",
                "languages": "English",
                "skills": "Java Code Design, OOP Principles, Algorithmic Analysis, Debugging",
                "competencies": "Writing and Reporting, Applying Expertise and Technology",
                "remote_testing": "Yes",
                "adaptive": "No",
                "category": "Technical Skills",
            },
            {
                "name": "SHL English Language Communication Test",
                "url": "https://www.shl.com/en/assessments/language/english-communication/",
                "description": (
                    "Audits professional spoken, written, and reading English communication capacities. "
                    "Identifies capability fit for customer support, service delivery, "
                    "or international coordination roles."
                ),
                "test_type": "Language",
                "job_family": "Administration, Sales",
                "target_level": "Graduate/Entry, Professional",
                "duration": "15 mins",
                "languages": "English",
                "skills": "Vocabulary, Spoken Intonation, Grammar Accuracy, Listening Comprehension",
                "competencies": "Presenting and Communicating Information, Relating and Networking",
                "remote_testing": "Yes",
                "adaptive": "Yes",
                "category": "Language Proficiency",
            },
            {
                "name": "SHL Graduate General Ability Test",
                "url": "https://www.shl.com/en/assessments/cognitive/general-ability/",
                "description": (
                    "Audits general reasoning, critical logical inference, and numerical processing for entry level "
                    "graduates. Excellent for screening general talent in early career pipelines."
                ),
                "test_type": "Cognitive",
                "job_family": "Technology, Sales, Administration, Finance, Management",
                "target_level": "Graduate/Entry",
                "duration": "30 mins",
                "languages": "English, French, German",
                "skills": "Logical Aptitude, Data Inferences, Problem Solving",
                "competencies": "Analyzing, Formulating Concepts, Learning Capacity",
                "remote_testing": "Yes",
                "adaptive": "Yes",
                "category": "Cognitive Test",
            },
        ]
