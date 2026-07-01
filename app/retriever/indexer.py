"""Catalog indexer orchestrating incremental indexing of assessments into ChromaDB."""

import hashlib
import logging
import time
from typing import Any

from app.catalog.models import CatalogAssessment
from app.retriever.chunker import AssessmentChunker
from app.retriever.embeddings import BaseEmbeddingProvider
from app.retriever.metadata import MetadataBuilder
from app.retriever.models import IndexingResult
from app.retriever.vector_store import VectorStoreWrapper

logger = logging.getLogger(__name__)


class CatalogIndexer:
    """Orchestrator managing incremental vector updates and deletions inside ChromaDB."""

    def __init__(
        self,
        vector_store: VectorStoreWrapper,
        embedding_provider: BaseEmbeddingProvider,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.chunker = AssessmentChunker()
        self.metadata_builder = MetadataBuilder()

    def run_indexing(self, assessments: list[CatalogAssessment], batch_size: int = 20) -> IndexingResult:
        """Executes full incremental indexing.

        Detects new, modified, and deleted entries, updating ChromaDB.

        Args:
            assessments: The current active list of CatalogAssessment items.
            batch_size: Configured batch size for embedding generation calls.

        Returns:
            An IndexingResult summary object detailing run metrics.
        """
        start_time = time.time()
        result = IndexingResult(collection_name=self.vector_store.collection_name)
        result.total_processed = len(assessments)

        try:
            logger.info("Indexer: Starting incremental indexing suite...")

            # 1. Fetch current index records inside ChromaDB
            existing_records = self.vector_store.get_all_records()
            existing_ids = existing_records.get("ids", [])
            existing_metadatas = existing_records.get("metadatas", []) or []

            # Map IDs to their current stored document hashes
            id_to_hash: dict[str, str] = {}
            for idx, rid in enumerate(existing_ids):
                meta = existing_metadatas[idx] if idx < len(existing_metadatas) else {}
                if meta and "document_hash" in meta:
                    id_to_hash[rid] = str(meta["document_hash"])

            catalog_ids: set[str] = {str(a.id) for a in assessments}

            # Lists to queue for ChromaDB operations
            to_add_ids: list[str] = []
            to_add_docs: list[str] = []
            to_add_metadatas: list[dict[str, Any]] = []

            to_update_ids: list[str] = []
            to_update_docs: list[str] = []
            to_update_metadatas: list[dict[str, Any]] = []

            # 2. Iterate catalog assessments, computing hashes and comparing
            for assessment in assessments:
                aid_str = str(assessment.id)
                doc_text = self.chunker.build_search_document(assessment)
                doc_hash = hashlib.sha256(doc_text.encode("utf-8")).hexdigest()
                metadata = self.metadata_builder.build_metadata(assessment, doc_hash)

                if aid_str not in id_to_hash:
                    # New assessment
                    to_add_ids.append(aid_str)
                    to_add_docs.append(doc_text)
                    to_add_metadatas.append(metadata)
                elif id_to_hash[aid_str] != doc_hash:
                    # Modified assessment
                    to_update_ids.append(aid_str)
                    to_update_docs.append(doc_text)
                    to_update_metadatas.append(metadata)
                else:
                    # Unmodified assessment
                    result.skipped += 1

            # 3. Process new insertions in batches
            if to_add_ids:
                logger.info("Indexer: Inserting %d new records...", len(to_add_ids))
                self._process_batch_ops(
                    ids=to_add_ids,
                    docs=to_add_docs,
                    metadatas=to_add_metadatas,
                    batch_size=batch_size,
                    operation="add",
                    result=result,
                )

            # 4. Process updates in batches
            if to_update_ids:
                logger.info("Indexer: Updating %d modified records...", len(to_update_ids))
                self._process_batch_ops(
                    ids=to_update_ids,
                    docs=to_update_docs,
                    metadatas=to_update_metadatas,
                    batch_size=batch_size,
                    operation="update",
                    result=result,
                )

            # 5. Prune deleted records (orphan IDs in DB not in active catalog)
            obsolete_ids = [rid for rid in existing_ids if rid not in catalog_ids]
            if obsolete_ids:
                logger.info("Indexer: Pruning %d obsolete vector records...", len(obsolete_ids))
                self.vector_store.delete(ids=obsolete_ids)
                result.deleted = len(obsolete_ids)

        except Exception as e:
            logger.error("Indexer: Ingest failed with critical error: %s", e)
            result.errors.append(str(e))
            result.failed = len(assessments) - result.added - result.updated - result.skipped

        result.execution_duration_sec = time.time() - start_time
        logger.info(
            "Indexer: run finished. Added: %d, Updated: %d, Deleted: %d, Skipped: %d",
            result.added,
            result.updated,
            result.deleted,
            result.skipped,
        )
        return result

    def _process_batch_ops(
        self,
        ids: list[str],
        docs: list[str],
        metadatas: list[dict[str, Any]],
        batch_size: int,
        operation: str,
        result: IndexingResult,
    ) -> None:
        """Processes database updates/inserts sequentially in batched chunks.

        Args:
            ids: List of database ID keys.
            docs: Structured document text list.
            metadatas: Flat metadata dictionaries.
            batch_size: Sub-chunk batch size limits.
            operation: Either "add" or "update".
            result: Reference to mutable run IndexingResult.
        """
        total = len(ids)
        for start_idx in range(0, total, batch_size):
            end_idx = min(start_idx + batch_size, total)

            batch_ids = ids[start_idx:end_idx]
            batch_docs = docs[start_idx:end_idx]
            batch_metadatas = metadatas[start_idx:end_idx]

            try:
                # Generate embeddings for current batch
                embeddings = self.embedding_provider.generate_embeddings(batch_docs)

                if operation == "add":
                    self.vector_store.add(
                        ids=batch_ids,
                        documents=batch_docs,
                        metadatas=batch_metadatas,
                        embeddings=embeddings,
                    )
                    result.added += len(batch_ids)
                else:
                    self.vector_store.update(
                        ids=batch_ids,
                        documents=batch_docs,
                        metadatas=batch_metadatas,
                        embeddings=embeddings,
                    )
                    result.updated += len(batch_ids)
            except Exception as e:
                logger.error(
                    "Indexer: Batch %d-%d operation '%s' failed: %s",
                    start_idx,
                    end_idx,
                    operation,
                    e,
                )
                result.errors.append(f"Batch {start_idx}-{end_idx} failed: {e}")
                result.failed += len(batch_ids)


if __name__ == "__main__":
    import argparse

    from app.configs.logging import setup_logging
    from app.configs.settings import get_settings
    from app.retriever.manager import VectorStoreManager

    setup_logging()
    parser = argparse.ArgumentParser(description="SHL Vector Indexing CLI.")
    parser.add_argument(
        "--mode",
        choices=["online", "mock"],
        default="online",
        help="Run embeddings generation in live 'online' or 'mock' offline mode.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Wipe and rebuild ChromaDB collection index structures.",
    )
    args = parser.parse_args()

    if args.mode == "mock":
        # Override model_name config parameter to trigger mock provider selection
        get_settings().model_name = "mock"

    manager = VectorStoreManager()
    try:
        idx_res, val_res = manager.sync_index(rebuild=args.rebuild)
        print(f"Indexing run completed. Added: {idx_res.added}, Skipped: {idx_res.skipped}, Failed: {idx_res.failed}")
    except Exception as exc:
        print(f"Indexing failed: {exc}")
