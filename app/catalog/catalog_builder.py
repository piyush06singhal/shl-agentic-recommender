"""Catalog builder script orchestrating stages 1 through 9 of the ingestion pipeline."""

import argparse
import json
import logging
import os
import sys

from app.catalog.cleaner import CatalogCleaner
from app.catalog.deduplicator import CatalogDeduplicator
from app.catalog.models import CatalogAssessment, ScrapedAssessment
from app.catalog.normalizer import CatalogNormalizer
from app.catalog.parser import CatalogParser
from app.catalog.scraper import CatalogScraper
from app.catalog.statistics import CatalogStatisticsGenerator
from app.catalog.validator import CatalogValidator
from app.configs.logging import setup_logging
from app.configs.settings import get_settings

logger = logging.getLogger(__name__)


def run_pipeline(mode: str, index_url: str) -> None:
    """Orchestrates the catalog building pipeline.

    Args:
        mode: Ingestion execution mode, either "online" or "mock".
        index_url: Web url path to crawl in online mode.
    """
    logger.info("Initializing SHL Catalog Generation Pipeline (Mode: %s)...", mode)
    setup_logging()

    # 1. Initialize Pipeline components
    scraper = CatalogScraper()
    parser = CatalogParser()
    cleaner = CatalogCleaner()
    normalizer = CatalogNormalizer()
    validator = CatalogValidator()
    deduplicator = CatalogDeduplicator()
    stats_gen = CatalogStatisticsGenerator()

    raw_assessments: list[ScrapedAssessment] = []

    # 2. Stage 1-3: Download pages and follow links
    if mode.lower() == "online":
        logger.info("Online mode active: Starting crawler targeting %s...", index_url)
        try:
            detail_links = scraper.scrape_catalog_index(index_url)
            if not detail_links:
                logger.warning("No assessment detail page links scraped. Falling back to mock data.")
                raw_data = scraper.get_mock_assessments()
            else:
                raw_data = []
                for idx, link in enumerate(detail_links, 1):
                    try:
                        logger.info("Crawling detail link %d/%d: %s", idx, len(detail_links), link)
                        html = scraper.fetch_url(link)
                        # Stage 4: Extract metadata
                        scraped = parser.parse_page(html, link)
                        raw_data.append(scraped.model_dump())
                    except Exception as err:
                        logger.error("Failed scraping detail page %s: %s. Continuing...", link, err)
        except Exception as e:
            logger.error("Scraper encountered failure in index crawl: %s. Falling back to mock data.", e)
            raw_data = scraper.get_mock_assessments()
    else:
        logger.info("Mock mode active: Loading mock assessment fixtures...")
        raw_data = scraper.get_mock_assessments()

    # Convert raw dictionary entries to ScrapedAssessment models
    for item in raw_data:
        try:
            raw_assessments.append(ScrapedAssessment(**item))
        except Exception as e:
            logger.error("Parsing raw scraped input model failed for item: %s. Error: %s", item, e)

    # Resolve target directory paths
    settings = get_settings()
    data_dir = os.path.dirname(settings.catalog_path)
    os.makedirs(data_dir, exist_ok=True)

    # Save Stage 4 output: raw_catalog.json
    raw_catalog_path = os.path.join(data_dir, "raw_catalog.json")
    logger.info("Saving raw catalog dump to %s...", raw_catalog_path)
    with open(raw_catalog_path, "w", encoding="utf-8") as f:
        json.dump([item.model_dump() for item in raw_assessments], f, indent=2, ensure_ascii=False)

    # 3. Stage 5: Clean & Normalize
    normalized_assessments: list[CatalogAssessment] = []
    missing_fields_count = 0

    for scraped in raw_assessments:
        try:
            # Audit missing optional fields in raw data
            # Check description, type, job family, target level, duration, languages
            opt_fields = ["description", "test_type", "job_family", "target_level", "duration", "languages"]
            for field in opt_fields:
                if not getattr(scraped, field):
                    missing_fields_count += 1

            # Cleaner step
            cleaned = cleaner.clean_metadata(scraped)
            # Normalizer step
            normalized = normalizer.normalize_assessment(cleaned)
            normalized_assessments.append(normalized)
        except Exception as e:
            logger.error("Failed to clean or normalize item '%s': %s", scraped.name, e)

    # 4. Stage 6: Validate
    is_valid, validation_report = validator.validate_catalog(normalized_assessments)
    validation_report_path = os.path.join(data_dir, "validation_report.json")
    logger.info("Saving validation report to %s...", validation_report_path)
    with open(validation_report_path, "w", encoding="utf-8") as f:
        json.dump(validation_report, f, indent=2, ensure_ascii=False)

    # Count validation issues
    validation_failures_count = sum(len(errs) for errs in validation_report.values())

    # 5. Stage 7: Deduplicate
    initial_count = len(normalized_assessments)
    deduplicated_assessments = deduplicator.deduplicate(normalized_assessments)
    duplicate_count = initial_count - len(deduplicated_assessments)

    # 6. Stage 8: Generate catalog.json
    logger.info("Saving final normalized catalog database to %s...", settings.catalog_path)
    with open(settings.catalog_path, "w", encoding="utf-8") as f:
        # Save as json list of serialized CatalogAssessment dicts
        json.dump(
            [item.model_dump(mode="json") for item in deduplicated_assessments],
            f,
            indent=2,
            ensure_ascii=False,
        )

    # 7. Stage 9: Generate statistics report
    stats = stats_gen.generate_report(
        assessments=deduplicated_assessments,
        duplicate_count=duplicate_count,
        validation_failures_count=validation_failures_count,
        missing_metadata_stubs=missing_fields_count,
    )
    stats_path = os.path.join(data_dir, "catalog_statistics.json")
    logger.info("Saving catalog statistics report to %s...", stats_path)
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    # 8. Log and print summary report
    logger.info("==================================================")
    logger.info("SHL CATALOG PIPELINE PROCESSING COMPLETED SUCCESSFULLY")
    logger.info("==================================================")
    logger.info("Total Assessments Processed: %d", len(deduplicated_assessments))
    logger.info("Duplicates Removed: %d", duplicate_count)
    logger.info("Validation Issues Logged: %d", validation_failures_count)
    logger.info("Missing Metadata Attributes: %d", missing_fields_count)
    logger.info("Catalog Path: %s", settings.catalog_path)
    logger.info("Statistics Path: %s", stats_path)
    logger.info("==================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SHL Solutions Catalog Ingestion Pipeline CLI.")
    parser.add_argument(
        "--mode",
        choices=["online", "mock"],
        default="mock",
        help="Run scraper in live crawl 'online' mode or 'mock' data fallback mode.",
    )
    parser.add_argument(
        "--url",
        default="https://www.shl.com/en/assessments/",
        help="Main solutions list URL to crawl when running online.",
    )
    args = parser.parse_args()

    try:
        run_pipeline(args.mode, args.url)
    except Exception as exc:
        logger.critical("Ingestion pipeline crashed with uncaught failure: %s", exc, exc_info=True)
        sys.exit(1)
