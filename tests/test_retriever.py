"""Unit tests validating retriever chunker, embeddings, vector store, indexer, and manager modules."""

import os
import shutil
import tempfile
from collections.abc import Generator
from uuid import UUID

import pytest

from app.catalog.models import CatalogAssessment
from app.retriever.chunker import AssessmentChunker
from app.retriever.embeddings import MockEmbeddingProvider
from app.retriever.indexer import CatalogIndexer
from app.retriever.manager import VectorStoreManager
from app.retriever.metadata import MetadataBuilder
from app.retriever.vector_store import VectorStoreWrapper

# --- Fixtures ---

@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Creates a temporary folder path for isolating local persistent ChromaDB instances."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def mock_embedding_provider() -> MockEmbeddingProvider:
    """Provides a MockEmbeddingProvider with dimension 1536."""
    return MockEmbeddingProvider(dimension=1536)


@pytest.fixture
def sample_catalog_record() -> CatalogAssessment:
    """Provides a normalized CatalogAssessment record fixture."""
    return CatalogAssessment(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        name="Java Skill Ingestion Test",
        url="https://www.shl.com/java",
        test_type="Cognitive",
        description="Audits core object oriented skills in java.",
        job_family=["Technology"],
        target_level=["Professional"],
        duration_mins=45,
        languages=["English", "German"],
        skills=["Java OOP", "Multithreading"],
        competencies=["Applying Expertise"],
        remote_testing=True,
        adaptive=False,
        category="Technical Skills",
    )


# --- Test Cases ---

def test_chunker_builds_correct_document(sample_catalog_record: CatalogAssessment) -> None:
    """Verifies AssessmentChunker builds readable, normalized structural document representations."""
    chunker = AssessmentChunker()
    doc = chunker.build_search_document(sample_catalog_record)

    assert "Assessment: Java Skill Ingestion Test" in doc
    assert "Type: Cognitive" in doc
    assert "Job Families: Technology" in doc
    assert "Levels: Professional" in doc
    assert "Duration: 45 minutes" in doc
    assert "Languages: English, German" in doc
    assert "Skills: Java OOP, Multithreading" in doc
    assert "Competencies: Applying Expertise" in doc
    assert "Description: Audits core object oriented skills in java." in doc


def test_metadata_builder_flattens_fields(sample_catalog_record: CatalogAssessment) -> None:
    """Verifies MetadataBuilder flattens structured array lists into primitive values for ChromaDB."""
    builder = MetadataBuilder()
    metadata = builder.build_metadata(sample_catalog_record, "dummy-hash-123")

    assert metadata["assessment_id"] == "22222222-2222-2222-2222-222222222222"
    assert metadata["assessment_name"] == "Java Skill Ingestion Test"
    assert metadata["url"] == "https://www.shl.com/java"
    assert metadata["assessment_type"] == "Cognitive"
    assert metadata["job_family"] == "Technology"
    assert metadata["candidate_level"] == "Professional"
    assert metadata["duration"] == 45
    assert metadata["languages"] == "English, German"
    assert metadata["skills"] == "Java OOP, Multithreading"
    assert metadata["competencies"] == "Applying Expertise"
    assert metadata["remote_testing"] is True
    assert metadata["adaptive"] is False
    assert metadata["category"] == "Technical Skills"
    assert metadata["document_hash"] == "dummy-hash-123"


def test_mock_embeddings_generation(mock_embedding_provider: MockEmbeddingProvider) -> None:
    """Verifies MockEmbeddingProvider returns correct dimensions and coordinates lists."""
    texts = ["Doc 1", "Doc 2"]
    embeddings = mock_embedding_provider.generate_embeddings(texts)

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 1536
    assert len(embeddings[1]) == 1536
    assert mock_embedding_provider.get_dimension() == 1536


def test_vector_store_operations(temp_dir: str, mock_embedding_provider: MockEmbeddingProvider) -> None:
    """Verifies VectorStoreWrapper database pings, additions, count queries, and deletes."""
    vstore = VectorStoreWrapper(persist_directory=temp_dir, collection_name="test_collection")

    assert vstore.count() == 0
    assert vstore.health_check() is True

    # Insert items
    embeddings = mock_embedding_provider.generate_embeddings(["Java Document Chunk"])
    vstore.add(
        ids=["id-1"],
        documents=["Java Document Chunk"],
        metadatas=[{"assessment_name": "Java Test", "document_hash": "hash1"}],
        embeddings=embeddings,
    )

    assert vstore.count() == 1

    # Query check
    record = vstore.get_by_ids(["id-1"])
    assert len(record.get("ids", [])) == 1
    assert record["documents"][0] == "Java Document Chunk"

    # Delete check
    vstore.delete(["id-1"])
    assert vstore.count() == 0

    vstore.close()


def test_indexer_incremental_updates(temp_dir: str, mock_embedding_provider: MockEmbeddingProvider) -> None:
    """Verifies indexer incremental sync: skips unchanged records, updates modifications, deletes prunes."""
    vstore = VectorStoreWrapper(persist_directory=temp_dir, collection_name="test_collection")
    indexer = CatalogIndexer(vstore, mock_embedding_provider)

    assessment1 = CatalogAssessment(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="Cognitive Test A",
        url="https://www.shl.com/cognitive-a",
        test_type="Cognitive",
        description="Old description details.",
        duration_mins=20,
    )
    assessment2 = CatalogAssessment(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        name="Cognitive Test B",
        url="https://www.shl.com/cognitive-b",
        test_type="Cognitive",
        description="Record B description details.",
        duration_mins=30,
    )

    # 1. First Run: Index both records
    res1 = indexer.run_indexing([assessment1, assessment2])
    assert res1.added == 2
    assert res1.skipped == 0
    assert vstore.count() == 2

    # 2. Second Run: Run unchanged catalog list (should skip both)
    res2 = indexer.run_indexing([assessment1, assessment2])
    assert res2.added == 0
    assert res2.skipped == 2
    assert res2.updated == 0

    # 3. Third Run: Modify assessment1 description, delete assessment2
    modified_assessment1 = assessment1.model_copy(update={"description": "New description details."})
    res3 = indexer.run_indexing([modified_assessment1])
    assert res3.added == 0
    assert res3.updated == 1  # assessment1 updated
    assert res3.deleted == 1  # assessment2 deleted (not in list)
    assert res3.skipped == 0
    assert vstore.count() == 1

    vstore.close()


def test_manager_pipeline_lifecycle(temp_dir: str, mock_embedding_provider: MockEmbeddingProvider) -> None:
    """Verifies VectorStoreManager orchestrates loading, indexing, stats generating, and validation reports."""
    # Create temporary catalog path
    temp_catalog_file = os.path.join(temp_dir, "catalog.json")

    import json
    # Save a dummy catalog list
    assessments_data = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Cognitive test",
            "url": "https://www.shl.com/cognitive",
            "test_type": "Cognitive",
            "description": "Verifies reasoning ability.",
            "job_family": ["Technology"],
            "target_level": ["Professional"],
            "duration_mins": 30,
            "languages": ["English"],
            "skills": ["Reasoning"],
            "competencies": ["Analyzing"],
            "remote_testing": True,
            "adaptive": True,
            "category": "Cognitive",
        }
    ]
    with open(temp_catalog_file, "w", encoding="utf-8") as f:
        json.dump(assessments_data, f)

    vstore = VectorStoreWrapper(persist_directory=temp_dir, collection_name="test_collection")
    manager = VectorStoreManager(vector_store=vstore, embedding_provider=mock_embedding_provider)

    # Inject temporary file path
    manager.loader.catalog_path = temp_catalog_file
    manager.settings.catalog_path = temp_catalog_file

    # Run full sync
    idx_res, val_res = manager.sync_index(rebuild=True)

    assert idx_res.added == 1
    assert val_res.is_valid is True
    assert val_res.total_catalog_records == 1
    assert val_res.total_vector_records == 1
    assert len(val_res.validation_errors) == 0

    vstore.close()
