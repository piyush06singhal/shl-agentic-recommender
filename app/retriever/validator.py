"""Catalog index validator module auditing database alignment health."""

import logging
from typing import Any, cast

from app.catalog.models import CatalogAssessment
from app.retriever.models import IndexValidationResult
from app.retriever.vector_store import VectorStoreWrapper

logger = logging.getLogger(__name__)


class CatalogIndexValidator:
    """Audits index entries, checking coordinate dimensions, orphan profiles, and schema validation consistency."""

    def validate_index(
        self,
        assessments: list[CatalogAssessment],
        vector_store: VectorStoreWrapper,
        expected_dimension: int,
    ) -> IndexValidationResult:
        """Audits database records alignment.

        Args:
            assessments: The current active list of CatalogAssessment records.
            vector_store: The active VectorStoreWrapper wrapper.
            expected_dimension: The expected size of float coordinate dimensions arrays.

        Returns:
            An IndexValidationResult detailing discrepancies.
        """
        logger.info("Validator: Auditing alignment between catalog database and vector index...")

        catalog_ids = {str(a.id) for a in assessments}

        # Query ChromaDB collection
        db_records = vector_store.get_all_records()
        db_ids = db_records.get("ids", []) or []

        # ChromaDB API 'get()' by default doesn't return coordinates embeddings unless explicitly requested
        # We need a separate query, or we check database health via ping and get metadata.
        # But we can query collection collection.get(include=["embeddings"]) to test dimension integrity.
        # To save memory, we can fetch just one record with embeddings to verify dimension matching.
        dimension_valid = True
        actual_dimension = 0

        if db_ids:
            try:
                sample_id = db_ids[0]
                sample = cast(
                    dict[str, Any],
                    vector_store.collection.get(
                        ids=[sample_id],
                        include=cast(Any, ["embeddings"]),
                    ),
                )
                embeddings = sample.get("embeddings", [])
                if embeddings is not None and len(embeddings) > 0:
                    actual_dimension = len(embeddings[0])
                    if actual_dimension != expected_dimension:
                        dimension_valid = False
            except Exception as e:
                logger.error("Validator: Checking vector dimension failed: %s", e)

        # Audit mismatches
        missing_ids = [cid for cid in catalog_ids if cid not in db_ids]
        orphan_ids = [db_id for db_id in db_ids if db_id not in catalog_ids]

        validation_errors: list[str] = []

        if len(catalog_ids) != len(db_ids):
            validation_errors.append(
                f"Record count mismatch: Catalog contains {len(catalog_ids)} items, "
                f"but Vector database contains {len(db_ids)} entries."
            )

        if missing_ids:
            validation_errors.append(f"Missing records: {len(missing_ids)} catalog items are not indexed.")
        if orphan_ids:
            validation_errors.append(f"Orphan records: {len(orphan_ids)} vector entries do not exist in catalog.")
        if not dimension_valid:
            validation_errors.append(
                f"Embedding dimensions mismatch: Expected size {expected_dimension}, "
                f"but indexed record contains size {actual_dimension}."
            )

        # Check duplicate vector IDs
        seen_ids: set[str] = set()
        duplicate_ids: list[str] = []
        for rid in db_ids:
            if rid in seen_ids:
                duplicate_ids.append(rid)
            seen_ids.add(rid)

        if duplicate_ids:
            validation_errors.append(f"Duplicate records found in index for IDs: {duplicate_ids}")

        is_valid = len(validation_errors) == 0

        logger.info(
            "Validator: Audit completed. Index is %s. Discrepancies logged: %d",
            "VALID" if is_valid else "INVALID",
            len(validation_errors),
        )

        return IndexValidationResult(
            is_valid=is_valid,
            total_catalog_records=len(catalog_ids),
            total_vector_records=len(db_ids),
            missing_ids=missing_ids,
            orphan_ids=orphan_ids,
            validation_errors=validation_errors,
        )
