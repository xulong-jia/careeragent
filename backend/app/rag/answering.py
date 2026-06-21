from __future__ import annotations

from app.schemas.rag import RagSearchSource


ANSWER_TYPE = "deterministic_summary"


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def build_deterministic_answer(
    question: str,
    sources: list[RagSearchSource],
    *,
    max_chars: int = 1000,
) -> dict[str, object]:
    if not sources:
        return {
            "question": question,
            "answer": "",
            "sources": [],
            "uncertainty": "no_relevant_source",
            "grounded": False,
            "answer_type": ANSWER_TYPE,
        }

    lines = ["基于检索来源，当前可确认的信息如下："]
    for index, source in enumerate(sources, start=1):
        section = f" / {source.section}" if source.section else ""
        lines.append(
            f"{index}. [{source.title}{section}] {source.snippet}"
        )
    answer = _truncate(" ".join(lines), max_chars)
    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "uncertainty": None,
        "grounded": True,
        "answer_type": ANSWER_TYPE,
    }
