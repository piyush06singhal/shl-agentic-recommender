"""Catalog parser module extracting raw attributes from HTML layouts using BeautifulSoup4."""

import logging
import re

from bs4 import BeautifulSoup, Tag

from app.catalog.models import ScrapedAssessment

logger = logging.getLogger(__name__)


class CatalogParser:
    """Parses HTML content blocks and extracts structured metadata key-value pairs."""

    def parse_page(self, html: str, url: str) -> ScrapedAssessment:
        """Parses a solution web page HTML and returns raw scraped text parameters.

        Args:
            html: Raw HTML content string.
            url: The page URL path.

        Returns:
            A ScrapedAssessment model containing the raw extracted strings.
        """
        soup = BeautifulSoup(html, "html.parser")

        # 1. Parse official name (Look for title headers)
        name = ""
        h1_tag = soup.find("h1")
        if h1_tag:
            name = h1_tag.get_text(strip=True)
        else:
            title_tag = soup.find("title")
            if title_tag:
                name = title_tag.get_text(strip=True)
        # Clean suffix title additions (e.g. " | SHL solutions")
        name = re.sub(r"\s*\|\s*shl.*", "", name, flags=re.IGNORECASE)

        # 2. Parse Description
        description = ""
        desc_meta = soup.find("meta", attrs={"name": "description"})
        if desc_meta and isinstance(desc_meta, Tag) and isinstance(desc_meta.get("content"), str):
            description = str(desc_meta.get("content"))
        else:
            # Fallback: grab first content paragraphs
            body_p = soup.find("p")
            if body_p:
                description = body_p.get_text(strip=True)

        # 3. Extract Metadata Fields via key-value text searches in divs or tables
        test_type = self._find_field_value(soup, ["test type", "assessment type"])
        job_family = self._find_field_value(soup, ["job family", "role family", "target job"])
        target_level = self._find_field_value(soup, ["target level", "seniority", "level"])
        duration = self._find_field_value(soup, ["duration", "time limit", "length"])
        languages = self._find_field_value(soup, ["languages", "supported languages", "translations"])
        skills = self._find_field_value(soup, ["skills", "measured skills", "skills tested"])
        competencies = self._find_field_value(soup, ["competencies", "key competencies"])
        remote_testing = self._find_field_value(soup, ["remote testing", "remote support", "proctoring"])
        adaptive = self._find_field_value(soup, ["adaptive", "adaptive testing"])
        category = self._find_field_value(soup, ["category", "test category"])

        return ScrapedAssessment(
            name=name,
            url=url,
            description=description,
            test_type=test_type,
            job_family=job_family,
            target_level=target_level,
            duration=duration,
            languages=languages,
            skills=skills,
            competencies=competencies,
            remote_testing=remote_testing,
            adaptive=adaptive,
            category=category,
        )

    def _find_field_value(self, soup: BeautifulSoup, keywords: list[str]) -> str | None:
        """Searches BeautifulSoup structures for label match descriptors to extract values.

        Looks for text blocks containing keywords and extracts text immediately following them.
        """
        # 1. Search in table cell elements
        for cell in soup.find_all(["td", "th"]):
            cell_text = cell.get_text(strip=True).lower()
            for kw in keywords:
                if kw in cell_text:
                    # check sibling cells
                    next_sib = cell.find_next_sibling(["td", "div", "span"])
                    if next_sib:
                        return str(next_sib.get_text(strip=True))

        # 2. Search in definition lists (dt/dd)
        for dt in soup.find_all("dt"):
            dt_text = dt.get_text(strip=True).lower()
            for kw in keywords:
                if kw in dt_text:
                    dd = dt.find_next_sibling("dd")
                    if dd:
                        return str(dd.get_text(strip=True))

        # 3. Fallback: scan raw elements matching text prefixes
        for elem in soup.find_all(["p", "div", "li", "span"]):
            # Ignore wrapper elements containing substantial sub-elements
            if len(elem.find_all()) > 2:
                continue
            text = elem.get_text(strip=True)
            for kw in keywords:
                pattern = rf"(?i){re.escape(kw)}[a-zA-Z\s]*[:\-]\s*(.*)"
                match = re.search(pattern, text)
                if match:
                    return match.group(1).strip()

        return None
