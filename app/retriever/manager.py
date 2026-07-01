"""VectorStoreManager service orchestrating embedding generation and index sync pipelines."""

import logging
import os
from typing import Any

from app.configs.settings import get_settings
from app.retriever.embeddings import BaseEmbeddingProvider, get_embedding_provider
from app.retriever.indexer import CatalogIndexer
from app.retriever.loader import CatalogLoader
from app.retriever.models import IndexingResult, IndexValidationResult
from app.retriever.statistics import IndexStatisticsGenerator
from app.retriever.validator import CatalogIndexValidator
from app.retriever.vector_store import VectorStoreWrapper

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Main lifecycle orchestrator of the vector index generation and integrity verification pipelines."""

    def __init__(
        self,
        vector_store: VectorStoreWrapper | None = None,
        embedding_provider: BaseEmbeddingProvider | None = None,
    ) -> None:
        self.settings = get_settings()
        self.vector_store = vector_store or VectorStoreWrapper()
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.loader = CatalogLoader()
        self.indexer = CatalogIndexer(self.vector_store, self.embedding_provider)
        self.validator = CatalogIndexValidator()
        self.stats_generator = IndexStatisticsGenerator()

    def sync_index(self, rebuild: bool = False, batch_size: int = 20) -> tuple[IndexingResult, IndexValidationResult]:
        """Loads catalog assessments and synchronizes ChromaDB vector index database.

        Args:
            rebuild: Wipes and rebuilds the collection database before indexing if True.
            batch_size: Bulk batch size parameters for OpenAI embedding calls.

        Returns:
            A tuple of (IndexingResult, IndexValidationResult).
        """
        logger.info("Manager: Initiating index synchronization (Rebuild: %s)...", rebuild)

        if rebuild:
            self.vector_store.rebuild_collection()

        try:
            # 1. Load catalog assessments
            assessments = self.loader.load_assessments()
        except Exception as e:
            logger.error("Manager: Aborting sync. Ingestion catalog load failed: %s", e)
            # Return empty failed result
            err_result = IndexingResult(collection_name=self.vector_store.collection_name, failed=1)
            err_result.errors.append(str(e))
            empty_validation = IndexValidationResult(
                is_valid=False,
                total_catalog_records=0,
                total_vector_records=self.vector_store.count(),
                validation_errors=[str(e)],
            )
            return err_result, empty_validation

        # 2. Run indexer
        indexing_result = self.indexer.run_indexing(assessments, batch_size=batch_size)

        # 3. Validate index alignment
        expected_dim = self.embedding_provider.get_dimension()
        validation_result = self.validator.validate_index(
            assessments=assessments,
            vector_store=self.vector_store,
            expected_dimension=expected_dim,
        )

        # 4. Compile statistics and write reports
        try:
            stats = self.stats_generator.compile_statistics(
                vector_store=self.vector_store,
                embedding_model=self.settings.embedding_model,
                embedding_dimension=expected_dim,
                indexing_result=indexing_result,
            )

            # Save files under catalog/data/ folder
            data_dir = os.path.dirname(self.settings.catalog_path)
            stats_path = os.path.join(data_dir, "vector_statistics.json")

            import json
            logger.info("Manager: Saving vector statistics to %s...", stats_path)
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(stats.model_dump(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Manager: Compiling database statistics failed: %s", e)

        return indexing_result, validation_result

    def query_placeholder(self, query: str) -> list[dict[str, Any]]:
        """Stub placeholder query interface for search (real search logic implemented in Phase 4)."""
        logger.info("Manager: Query placeholder invoked for: '%s'", query)
        return []

    def shutdown(self) -> None:
        """Teardown handler releasing database clients connections."""
        self.vector_store.close()
