from app.rag.chunking import chunk_document_text


def test_markdown_chunking_tracks_headings_and_metadata():
    chunks = chunk_document_text(
        "# Overview\n\nCareerAgent supports resume workflows.\n\n"
        "## Requirements\n\nPython and FastAPI experience.\n\nReact dashboard work.",
        source_type="markdown",
        metadata={"topic": "career"},
        max_chars=120,
    )

    assert [chunk["chunk_index"] for chunk in chunks] == list(range(len(chunks)))
    assert {chunk["section"] for chunk in chunks} >= {"Overview", "Requirements"}
    assert all(chunk["metadata"]["topic"] == "career" for chunk in chunks)
    assert any(chunk["metadata"]["section_hint"] == "Requirements" for chunk in chunks)


def test_plain_text_chunking_splits_long_paragraphs():
    raw_text = " ".join(["deterministic"] * 80)

    chunks = chunk_document_text(
        raw_text,
        source_type="text",
        metadata={},
        max_chars=120,
    )

    assert len(chunks) > 1
    assert all(len(chunk["text"]) <= 120 for chunk in chunks)
    assert all(chunk["token_count"] > 0 for chunk in chunks)


def test_jd_chunking_adds_section_hints():
    chunks = chunk_document_text(
        "Requirements:\nPython, SQL, and testing.\n\n"
        "Responsibilities:\nBuild APIs and maintain services.\n\n"
        "Preferred Skills:\nReact and analytics.",
        source_type="jd",
        metadata={"source_type": "jd"},
        max_chars=120,
    )

    sections = [chunk["section"] for chunk in chunks]
    assert "Requirements" in sections
    assert "Responsibilities" in sections
    assert "Preferred Skills" in sections
