from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.base import Base
from app.models.rag import RagAnswerRun, RagChunk, RagDocument


RAG_TABLES = {"rag_documents", "rag_chunks", "rag_answer_runs"}


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
    assert {
        "question",
        "filters_json",
        "answer",
        "citations_json",
        "source_refs_json",
        "retrieval_debug_json",
    }.issubset(
        {column["name"] for column in inspector.get_columns("rag_answer_runs")}
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
    assert "ix_rag_answer_runs_user_id" in {
        index["name"] for index in inspector.get_indexes("rag_answer_runs")
    }
    assert "ix_rag_answer_runs_grounded" in {
        index["name"] for index in inspector.get_indexes("rag_answer_runs")
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


def test_rag_answer_run_insert_with_grounded_contract(db_session):
    answer_run = RagAnswerRun(
        id="rag_answer_run_0001",
        question="How should I prepare for FastAPI interviews?",
        filters_json={"source_type": "manual"},
        top_k=3,
        retrieval_mode="deterministic_lexical",
        answer="Based on retrieved evidence, use source-backed examples.",
        answer_type="deterministic_summary",
        grounded=True,
        uncertainty="grounded",
        evidence_summary=["Synthetic Notes: use source-backed examples."],
        citations_json=[
            {
                "source_type": "manual",
                "document_id": "rag_doc_0001",
                "chunk_id": "rag_doc_0001_chunk_0001",
                "title": "Synthetic Notes",
                "section": None,
                "label": "Synthetic Notes",
                "snippet": "use source-backed examples",
                "score": 0.5,
                "metadata_preview": {"topic": "interview"},
            }
        ],
        source_refs_json=[
            {
                "source_type": "rag_chunk",
                "source_id": "rag_doc_0001_chunk_0001",
                "document_id": "rag_doc_0001",
                "chunk_id": "rag_doc_0001_chunk_0001",
                "field": "snippet",
                "label": "Synthetic Notes",
                "preview": "use source-backed examples",
                "score": 0.5,
            }
        ],
        retrieval_debug_json={
            "retrieval_mode": "deterministic_lexical",
            "query_tokens": ["fastapi"],
            "candidate_count": 1,
            "selected_chunk_ids": ["rag_doc_0001_chunk_0001"],
            "scores": [0.5],
            "top_k": 3,
            "filters": {"source_type": "manual"},
            "insufficient_reason": None,
        },
    )

    db_session.add(answer_run)
    db_session.commit()

    persisted = db_session.get(RagAnswerRun, "rag_answer_run_0001")
    assert persisted is not None
    assert persisted.user_id == "default"
    assert persisted.grounded is True
    assert persisted.uncertainty == "grounded"
    assert persisted.citations_json[0]["snippet"] == "use source-backed examples"


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
