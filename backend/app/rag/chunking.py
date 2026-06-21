from __future__ import annotations

import re


ChunkPayload = dict[str, object]


def _rough_token_count(text: str) -> int:
    words = re.findall(r"\w+", text)
    if words:
        return len(words)
    return max(1, len(text) // 4)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_long_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    safe_overlap = min(overlap_chars, max_chars - 1)
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        segment = cleaned[start:end].strip()
        if segment:
            chunks.append(segment)
        if end >= len(cleaned):
            break
        start = end - safe_overlap
    return chunks


def _paragraphs_for_markdown(raw_text: str) -> list[tuple[str | None, str]]:
    paragraphs: list[tuple[str | None, str]] = []
    current_section: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        text = "\n".join(current_lines).strip()
        if text:
            paragraphs.append((current_section, text))
        current_lines = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush()
            current_section = heading.group(2).strip()
            continue
        if not stripped:
            flush()
            continue
        current_lines.append(stripped)
    flush()
    return paragraphs


def _paragraphs_for_text(raw_text: str) -> list[tuple[str | None, str]]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", raw_text) if block.strip()]
    return [(None, block) for block in blocks]


def _infer_jd_section(text: str) -> str | None:
    lowered = text.lower()
    if "preferred" in lowered or "nice to have" in lowered:
        return "Preferred Skills"
    if "responsibilities" in lowered or "responsibility" in lowered:
        return "Responsibilities"
    if "requirements" in lowered or "qualification" in lowered:
        return "Requirements"
    if "interview" in lowered:
        return "Interview Focus"
    return None


def _paragraphs_for_jd(raw_text: str) -> list[tuple[str | None, str]]:
    paragraphs = _paragraphs_for_text(raw_text)
    return [(_infer_jd_section(text), text) for _, text in paragraphs]


def chunk_document_text(
    raw_text: str,
    *,
    source_type: str,
    metadata: dict[str, object] | None,
    max_chars: int = 1200,
    overlap_chars: int = 0,
) -> list[ChunkPayload]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be lower than max_chars")

    base_metadata = dict(metadata or {})
    normalized_source_type = source_type.strip().lower()
    if normalized_source_type in {"markdown"}:
        paragraphs = _paragraphs_for_markdown(raw_text)
    elif normalized_source_type == "jd":
        paragraphs = _paragraphs_for_jd(raw_text)
    else:
        paragraphs = _paragraphs_for_text(raw_text)

    chunks: list[ChunkPayload] = []
    for section, paragraph in paragraphs:
        for segment in _split_long_text(paragraph, max_chars, overlap_chars):
            chunk_metadata = dict(base_metadata)
            if section:
                chunk_metadata["section_hint"] = section
            chunks.append(
                {
                    "chunk_index": len(chunks),
                    "section": section,
                    "text": segment,
                    "token_count": _rough_token_count(segment),
                    "metadata": chunk_metadata,
                }
            )
    return chunks
