"""Vector store wrapper class managing interactions with persistent ChromaDB indices."""

import logging
import os
from typing import Any, cast

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.configs.settings import get_settings

logger = logging.getLogger(__name__)


class VectorStoreWrapper:
    """Wrapper encapsulating persistent ChromaDB operations."""

    def __init__(
        self,
        persist_directory: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        settings = get_settings()
        self.persist_directory = persist_directory or settings.vector_db_path
        self.collection_name = collection_name or settings.vector_collection_name

        # Ensure persist directory folder exists
        os.makedirs(self.persist_directory, exist_ok=True)

        logger.info(
            "Initializing persistent ChromaDB Client (Path: %s, Collection: %s)...",
            self.persist_directory,
            self.collection_name,
        )

        # Instantiate persistent Client API
        self.client: ClientAPI = chromadb.PersistentClient(path=self.persist_directory)
        self.collection: Collection = self.client.get_or_create_collection(
            name=self.collection_name
        )

    def count(self) -> int:
        """Returns the total number of items stored in the collection."""
        try:
            return int(self.collection.count())
        except Exception as e:
            logger.error("Error fetching collection count from ChromaDB: %s", e)
            return 0

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, str | int | float | bool]],
        embeddings: list[list[float]],
    ) -> None:
        """Inserts records into the vector database.

        Args:
            ids: Unique ID string mappings list.
            documents: Text representation documents chunks.
            metadatas: Flat properties dictionaries list.
            embeddings: Generated coordinate float matrices.
        """
        try:
            logger.info("ChromaDB: Inserting %d vector records...", len(ids))
            # ChromaDB add checks types strictly
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,  # type: ignore
                embeddings=embeddings,  # type: ignore
            )
        except Exception as e:
            logger.error("ChromaDB: Failed inserting vector records: %s", e)
            raise

    def update(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, str | int | float | bool]],
        embeddings: list[list[float]],
    ) -> None:
        """Updates records in the vector database.

        Args:
            ids: Unique ID mappings.
            documents: Text document string chunks.
            metadatas: Properties dictionaries.
            embeddings: Coordinates matrices.
        """
        try:
            logger.info("ChromaDB: Updating %d vector records...", len(ids))
            self.collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas,  # type: ignore
                embeddings=embeddings,  # type: ignore
            )
        except Exception as e:
            logger.error("ChromaDB: Failed updating vector records: %s", e)
            raise

    def delete(self, ids: list[str]) -> None:
        """Prunes records matching the list of ID keys.

        Args:
            ids: List of database keys to prune.
        """
        try:
            logger.info("ChromaDB: Pruning %d records...", len(ids))
            self.collection.delete(ids=ids)
        except Exception as e:
            logger.error("ChromaDB: Failed deleting vector records: %s", e)
            raise

    def get_by_ids(self, ids: list[str]) -> dict[str, Any]:
        """Queries specific records by ID list.

        Args:
            ids: Unique database keys list.

        Returns:
            ChromaDB query results dictionary containing metadatas, documents, etc.
        """
        try:
            # Explicitly request documents and metadatas, omitting embeddings to save bandwidth/memory
            result = self.collection.get(
                ids=ids,
                include=cast(Any, ["metadatas", "documents"]),
            )
            return cast(dict[str, Any], result)
        except Exception as e:
            logger.error("ChromaDB: Failed fetching records by ID list: %s", e)
            return {"ids": [], "metadatas": [], "documents": []}

    def get_all_records(self) -> dict[str, Any]:
        """Queries the complete list of elements in the collection database."""
        try:
            result = self.collection.get(
                include=cast(Any, ["metadatas", "documents"]),
            )
            return cast(dict[str, Any], result)
        except Exception as e:
            logger.error("ChromaDB: Failed fetching all collection records: %s", e)
            return {"ids": [], "metadatas": [], "documents": []}

    def delete_collection(self) -> None:
        """Deletes the current collection database table."""
        try:
            logger.warning("ChromaDB: Deleting collection '%s'...", self.collection_name)
            self.client.delete_collection(name=self.collection_name)
        except Exception as e:
            logger.error("ChromaDB: Failed deleting collection: %s", e)
            raise

    def rebuild_collection(self) -> None:
        """Wipes and recreates the collection index structures."""
        try:
            self.delete_collection()
        except Exception:
            pass  # If collection did not exist

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )
        logger.info("ChromaDB: Collection '%s' successfully rebuilt.", self.collection_name)

    def health_check(self) -> bool:
        """Pings the local database client to verify connectivity health.

        Returns:
            True if client heartbeat registers.
        """
        try:
            heartbeat = self.client.heartbeat()
            logger.debug("ChromaDB Heartbeat: %s", heartbeat)
            return isinstance(heartbeat, int)
        except Exception as e:
            logger.error("ChromaDB: Client health check failed: %s", e)
            return False

    def close(self) -> None:
        """Teardown handler releasing any locked resources."""
        # ChromaDB clients automatically manage resources.
        logger.info("ChromaDB persistent client connection shut down successfully.")
