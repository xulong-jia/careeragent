from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.base import Base
from app.models.rag import RagChunk, RagDocument


RAG_TABLES = {"rag_documents", "rag_chunks"}


def test_orm_metadata_contains_rag_tables():
    assert RAG_TABLES.issubset(set(Base.metadata.tables))


def test_alembic_migration_creates_rag_tables(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'careeragent_rag_test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("backend/alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert RAG_TABLES.issubset(set(inspector.get_table_names()))
    assert {"source_type", "index_status"}.issubset(
        {column["name"] for column in inspector.get_columns("rag_documents")}
    )
    assert {"document_id", "chunk_index", "embedding_id"}.issubset(
        {column["name"] for column in inspector.get_columns("rag_chunks")}
    )
    assert "ix_rag_documents_source_type" in {
        index["name"] for index in inspector.get_indexes("rag_documents")
    }
    assert "ix_rag_documents_index_status" in {
        index["name"] for index in inspector.get_indexes("rag_documents")
    }
    assert "ix_rag_chunks_document_id" in {
        index["name"] for index in inspector.get_indexes("rag_chunks")
    }
    assert "uq_rag_chunks_document_id_chunk_index" in {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("rag_chunks")
    }

    get_settings.cache_clear()


def test_rag_document_and_chunk_insert_with_json_metadata(db_session):
    document = RagDocument(
        id="rag_doc_0001",
        title="Synthetic Backend Notes",
        source_type="learning",
        source_uri=None,
        raw_text="Synthetic text about FastAPI testing and database migrations.",
        metadata_json={"tags": ["backend", "synthetic"], "topic": "testing"},
    )
    chunk = RagChunk(
        id="rag_chunk_0001",
        chunk_index=0,
        section="Testing",
        text="Synthetic chunk about pytest and Alembic.",
        token_count=6,
        metadata_json={"section_hint": "Testing"},
    )
    document.chunks.append(chunk)

    db_session.add(document)
    db_session.commit()

    persisted = db_session.get(RagDocument, "rag_doc_0001")
    assert persisted is not None
    assert persisted.user_id == "default"
    assert persisted.index_status == "pending"
    assert persisted.chunk_count == 0
    assert persisted.metadata_json["tags"] == ["backend", "synthetic"]
    assert persisted.chunks[0].metadata_json["section_hint"] == "Testing"
    assert persisted.chunks[0].document_id == "rag_doc_0001"


def test_rag_chunk_document_index_unique_constraint(db_session):
    document = RagDocument(
        id="rag_doc_unique",
        title="Synthetic Unique Notes",
        source_type="manual",
        raw_text="Synthetic text for unique constraint testing.",
        metadata_json={},
    )
    document.chunks.extend(
        [
            RagChunk(
                id="rag_chunk_unique_1",
                chunk_index=0,
                section=None,
                text="First synthetic chunk.",
                metadata_json={},
            ),
            RagChunk(
                id="rag_chunk_unique_2",
                chunk_index=0,
                section=None,
                text="Duplicate synthetic chunk.",
                metadata_json={},
            ),
        ]
    )

    db_session.add(document)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_rag_document_delete_orphan_removes_chunks(db_session):
    document = RagDocument(
        id="rag_doc_delete",
        title="Synthetic Delete Notes",
        source_type="manual",
        raw_text="Synthetic text for delete-orphan testing.",
        metadata_json={},
    )
    document.chunks.append(
        RagChunk(
            id="rag_chunk_delete",
            chunk_index=0,
            section="Delete",
            text="Synthetic chunk for delete-orphan testing.",
            metadata_json={},
        )
    )
    db_session.add(document)
    db_session.commit()

    db_session.delete(document)
    db_session.commit()

    assert db_session.get(RagDocument, "rag_doc_delete") is None
    assert db_session.get(RagChunk, "rag_chunk_delete") is None
