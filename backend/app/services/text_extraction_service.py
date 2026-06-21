from dataclasses import dataclass, field
from pathlib import Path

from app.core.errors import AppError


@dataclass(frozen=True)
class TextExtractionResult:
    raw_text: str
    extraction_status: str
    extraction_method: str
    warnings: list[str] = field(default_factory=list)


TEXT_FILE_TYPES = {"markdown", "text"}


def extract_resume_text(
    filename: str, file_type: str, content_type: str | None, content: bytes
) -> TextExtractionResult:
    if file_type in TEXT_FILE_TYPES:
        return _extract_utf8_text(filename, file_type, content)
    if file_type == "pdf":
        return _placeholder_result(
            file_type="pdf",
            method="pdf_parser_placeholder",
            warning="PDF parser is not connected in Phase 1C.",
        )
    if file_type == "docx":
        return _placeholder_result(
            file_type="docx",
            method="docx_parser_placeholder",
            warning="DOCX parser is not connected in Phase 1C.",
        )
    raise AppError(
        code="unsupported_resume_file_type",
        message="Supported resume file types are PDF, DOCX, Markdown, and text.",
        status_code=400,
        details={
            "filename": filename,
            "content_type": content_type,
            "file_type": file_type,
        },
    )


def _extract_utf8_text(
    filename: str, file_type: str, content: bytes
) -> TextExtractionResult:
    try:
        raw_text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AppError(
            code="resume_text_decode_failed",
            message="Resume text file must be valid UTF-8.",
            status_code=400,
            details={"filename": filename, "file_type": file_type},
        ) from exc

    normalized_text = raw_text.strip()
    if not normalized_text:
        raise AppError(
            code="resume_text_empty_after_extraction",
            message="Resume text extraction produced empty text.",
            status_code=400,
            details={"filename": filename, "file_type": file_type},
        )

    suffix = Path(filename).suffix.lower().lstrip(".") or file_type
    return TextExtractionResult(
        raw_text=normalized_text,
        extraction_status="extracted",
        extraction_method=f"utf8_{suffix}_decode",
        warnings=[],
    )


def _placeholder_result(
    file_type: str, method: str, warning: str
) -> TextExtractionResult:
    label = file_type.upper()
    return TextExtractionResult(
        raw_text=(
            f"{label} raw text extraction placeholder. "
            f"{label} parser is not connected in Phase 1C."
        ),
        extraction_status="parser_placeholder",
        extraction_method=method,
        warnings=[warning],
    )
