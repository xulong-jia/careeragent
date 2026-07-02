#!/usr/bin/env python3
"""Import external human review batch evidence without storing private rows."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
import uuid
import zipfile
import xml.etree.ElementTree as ET


DEFAULT_OUTPUT = "evidence/private_outputs/human_review_batch.{timestamp}.json"
TASK_TYPES = {
    "jd_parse",
    "resume_parse",
    "match_score",
    "rag_answer",
    "project_rewrite",
    "agent_workflow",
}
DECISIONS = {"pass", "minor_issue", "major_issue", "fail"}
REQUIRED_ITEM_FIELDS = {
    "item_id",
    "task_type",
    "anonymized_input_ref",
    "model_output_ref",
    "reviewer_id_hash",
    "correctness_score",
    "groundedness_score",
    "safety_score",
    "usefulness_score",
    "privacy_risk_flag",
    "hallucination_flag",
    "fabrication_flag",
    "reviewer_comment",
    "decision",
    "requires_adjudication",
    "adjudication_decision",
    "bad_case_ref",
}
BATCH_OPTIONAL_FIELDS = {
    "review_batch_id",
    "dataset_name",
    "sampling_method",
    "reviewer_role",
    "privacy_sanitized",
}
PII_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{8,}\d)(?!\d)"),
]
RAW_PRIVATE_FIELDS = {
    "raw_text",
    "raw_resume",
    "resume_text",
    "jd_text",
    "chunk_text",
    "interview_answer",
    "private_note",
    "provider_trace",
}
XLSX_FILL_SHEET = "填写表"
XLSX_IMPORT_SHEET = "导入字段_不要改"
XLSX_FILL_LABEL_TO_FIELD = {
    "item_id": "item_id",
    "审核类型": "task_type_label",
    "输入摘要（匿名）": "input_summary",
    "模型输出摘要": "model_output_summary",
    "审核说明": "review_instruction",
    "正确性 0-1": "correctness_score",
    "正确性_0到1": "correctness_score",
    "有依据 0-1": "groundedness_score",
    "有依据_0到1": "groundedness_score",
    "安全性 0-1": "safety_score",
    "安全性_0到1": "safety_score",
    "有用性 0-1": "usefulness_score",
    "有用性_0到1": "usefulness_score",
    "隐私风险": "privacy_risk_flag",
    "隐私风险_true_false": "privacy_risk_flag",
    "幻觉": "hallucination_flag",
    "幻觉_true_false": "hallucination_flag",
    "编造": "fabrication_flag",
    "编造_true_false": "fabrication_flag",
    "结论": "decision",
    "需复审": "requires_adjudication",
    "需复审_true_false": "requires_adjudication",
    "备注": "reviewer_comment",
    "复审结论": "adjudication_decision",
    "Bad Case编号": "bad_case_ref",
    "BadCase编号": "bad_case_ref",
    "reviewer_id_hash": "reviewer_id_hash",
    "审核人ID Hash": "reviewer_id_hash",
}
TASK_TYPE_LABEL_TO_TYPE = {
    "JD 解析审核": "jd_parse",
    "简历解析审核": "resume_parse",
    "匹配分数审核": "match_score",
    "RAG 回答审核": "rag_answer",
    "项目改写审核": "project_rewrite",
    "Agent 流程审核": "agent_workflow",
}
XLSX_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "office": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
DEFAULT_XLSX_BATCH_FIELDS = {
    "review_batch_id": "human-review-sample-pack-v35b",
    "dataset_name": "anonymized_benchmark",
    "sampling_method": "generated_fillable_xlsx",
    "reviewer_role": "external_reviewer",
    "privacy_sanitized": "true",
}
TRUE_VALUES = {"1", "true", "yes", "y", "pass", "passed", "是", "真", "对", "通过"}
FALSE_VALUES = {"0", "false", "no", "n", "fail", "failed", "否", "假", "错", "不通过"}
DECISION_ALIASES = {
    "pass": "pass",
    "通过": "pass",
    "minor_issue": "minor_issue",
    "minor issue": "minor_issue",
    "小问题": "minor_issue",
    "minor": "minor_issue",
    "major_issue": "major_issue",
    "major issue": "major_issue",
    "严重问题": "major_issue",
    "major": "major_issue",
    "fail": "fail",
    "failed": "fail",
    "失败": "fail",
    "不通过": "fail",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _output_path(path: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(path.format(timestamp=timestamp))


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in TRUE_VALUES


def _parse_required_bool(value: Any, *, field: str, row_number: int) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ValueError(f"row {row_number}: {field} must be true or false")


def _parse_score(value: Any, *, field: str, row_number: int) -> float:
    try:
        score = float(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"row {row_number}: {field} must be a number") from exc
    if not 0 <= score <= 1:
        raise ValueError(f"row {row_number}: {field} must be between 0 and 1")
    return score


def _parse_decision(value: Any, *, field: str, row_number: int, allow_blank: bool = False) -> str:
    text = str(value).strip()
    if not text:
        if allow_blank:
            return ""
        raise ValueError(f"row {row_number}: {field} is required")
    normalized = DECISION_ALIASES.get(text.lower(), DECISION_ALIASES.get(text))
    if not normalized:
        raise ValueError(f"row {row_number}: unsupported {field} {text!r}")
    return normalized


def _reviewer_hash(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise ValueError("reviewer_id_hash is required")
    if raw.startswith("reviewer:") or raw.startswith("reviewer_"):
        return raw
    return "reviewer:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _check_no_private_data(row: dict[str, Any], *, row_number: int) -> None:
    for key, value in row.items():
        text = "" if value is None else str(value)
        if key in RAW_PRIVATE_FIELDS and text.strip():
            raise ValueError(f"row {row_number}: private field {key} is not allowed")
        for pattern in PII_PATTERNS:
            if pattern.search(text):
                raise ValueError(f"row {row_number}: obvious PII detected in {key}")


def _xlsx_target_path(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return str(PurePosixPath("xl") / target)


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("main:si", XLSX_NS):
        values.append("".join(text.text or "" for text in item.findall(".//main:t", XLSX_NS)))
    return values


def _xlsx_sheet_paths(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("rel:Relationship", XLSX_NS)
    }
    sheets: dict[str, str] = {}
    for sheet in workbook.findall("main:sheets/main:sheet", XLSX_NS):
        rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        sheets[sheet.attrib["name"]] = _xlsx_target_path(rel_targets[rel_id])
    return sheets


def _cell_column_index(cell_ref: str) -> int:
    letters = "".join(character for character in cell_ref if character.isalpha())
    index = 0
    for character in letters:
        index = index * 26 + ord(character.upper()) - 64
    return index or 1


def _xlsx_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//main:t", XLSX_NS))
    value = cell.findtext("main:v", default="", namespaces=XLSX_NS)
    if cell_type == "s" and value:
        return shared_strings[int(value)]
    if cell_type == "b":
        return "true" if value == "1" else "false"
    return value


def _xlsx_rows_by_name(path: Path) -> dict[str, list[list[str]]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        rows_by_sheet: dict[str, list[list[str]]] = {}
        for sheet_name, sheet_path in _xlsx_sheet_paths(archive).items():
            root = ET.fromstring(archive.read(sheet_path))
            parsed_rows: list[list[str]] = []
            for row in root.findall("main:sheetData/main:row", XLSX_NS):
                values: list[str] = []
                for cell in row.findall("main:c", XLSX_NS):
                    column_index = _cell_column_index(cell.attrib.get("r", "A1"))
                    while len(values) < column_index - 1:
                        values.append("")
                    values.append(_xlsx_cell_value(cell, shared_strings))
                parsed_rows.append(values)
            rows_by_sheet[sheet_name] = parsed_rows
    return rows_by_sheet


def _normalize_header(value: str) -> str:
    return " ".join(str(value).replace("\n", " ").split()).strip()


def _find_header_row(raw_rows: list[list[str]], required_headers: set[str]) -> int:
    normalized_required = {_normalize_header(header) for header in required_headers}
    for index, row in enumerate(raw_rows):
        normalized = {_normalize_header(value) for value in row if str(value).strip()}
        if normalized_required <= normalized:
            return index
    raise ValueError(f"xlsx sheet missing required headers: {sorted(required_headers)}")


def _rows_after_header(raw_rows: list[list[str]], header_index: int) -> list[dict[str, str]]:
    headers = [_normalize_header(value) for value in raw_rows[header_index]]
    rows: list[dict[str, str]] = []
    for raw_row in raw_rows[header_index + 1 :]:
        if not any(str(value).strip() for value in raw_row):
            continue
        padded = [*raw_row, *([""] * (len(headers) - len(raw_row)))]
        rows.append({header: str(value).strip() for header, value in zip(headers, padded) if header})
    return rows


def _global_reviewer_id(fill_sheet_rows: list[list[str]]) -> str:
    for row in fill_sheet_rows:
        if row and _normalize_header(row[0]).startswith("Reviewer ID Hash") and len(row) > 1:
            return str(row[1]).strip()
    return ""


def _machine_fields_from_item_id(item_id: str) -> dict[str, str]:
    fields = dict(DEFAULT_XLSX_BATCH_FIELDS)
    task_type = ""
    case_id = ""
    if item_id.startswith("hr_"):
        remainder = item_id[3:]
        for candidate in sorted(TASK_TYPES, key=len, reverse=True):
            prefix = f"{candidate}_"
            if remainder.startswith(prefix):
                task_type = candidate
                case_id = remainder[len(prefix) :]
                break
    fields["task_type"] = task_type
    fields["anonymized_input_ref"] = (
        f"anonymized_benchmark:{task_type}:{case_id}:input" if task_type and case_id else ""
    )
    fields["model_output_ref"] = (
        f"anonymized_benchmark:{task_type}:{case_id}:model_output" if task_type and case_id else ""
    )
    return fields


def _load_xlsx_review_rows(path: Path) -> list[dict[str, Any]]:
    sheets = _xlsx_rows_by_name(path)
    if XLSX_FILL_SHEET not in sheets:
        raise ValueError(f"xlsx human review input must contain {XLSX_FILL_SHEET!r} sheet")

    fill_rows_raw = sheets[XLSX_FILL_SHEET]
    fill_header_index = _find_header_row(fill_rows_raw, {"item_id", "审核类型"})
    fill_rows = _rows_after_header(fill_rows_raw, fill_header_index)
    reviewer_id_hash = _global_reviewer_id(fill_rows_raw)

    import_rows_by_item: dict[str, dict[str, str]] = {}
    if XLSX_IMPORT_SHEET in sheets:
        import_header_index = _find_header_row(sheets[XLSX_IMPORT_SHEET], {"item_id", "task_type"})
        for row in _rows_after_header(sheets[XLSX_IMPORT_SHEET], import_header_index):
            item_id = str(row.get("item_id", "")).strip()
            if item_id:
                import_rows_by_item[item_id] = row

    rows: list[dict[str, Any]] = []
    for fill_row in fill_rows:
        normalized_fill = {
            XLSX_FILL_LABEL_TO_FIELD.get(header, header): value
            for header, value in fill_row.items()
        }
        item_id = str(normalized_fill.get("item_id", "")).strip()
        if not item_id:
            continue
        machine_row = {**_machine_fields_from_item_id(item_id), **import_rows_by_item.get(item_id, {})}
        row = {
            **{field: machine_row.get(field, "") for field in BATCH_OPTIONAL_FIELDS},
            "item_id": item_id,
            "task_type": machine_row.get("task_type", ""),
            "anonymized_input_ref": machine_row.get("anonymized_input_ref", ""),
            "model_output_ref": machine_row.get("model_output_ref", ""),
        }
        if not row["task_type"]:
            row["task_type"] = TASK_TYPE_LABEL_TO_TYPE.get(
                str(normalized_fill.get("task_type_label", "")).strip(),
                "",
            )
        for field in REQUIRED_ITEM_FIELDS - {"item_id", "task_type", "anonymized_input_ref", "model_output_ref"}:
            row[field] = str(normalized_fill.get(field, "")).strip()
        if not row["reviewer_id_hash"]:
            row["reviewer_id_hash"] = reviewer_id_hash
        rows.append(row)

    if not rows:
        raise ValueError("human review xlsx input is empty")
    return rows


def load_review_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        rows = _load_xlsx_review_rows(path)
    elif suffix == ".jsonl":
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("human review input is empty")
    return rows


def normalize_review_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=1):
        _check_no_private_data(row, row_number=row_number)
        missing = sorted(field for field in REQUIRED_ITEM_FIELDS if field not in row)
        if missing:
            raise ValueError(f"row {row_number}: missing required fields: {missing}")

        task_type = str(row["task_type"]).strip()
        if task_type not in TASK_TYPES:
            raise ValueError(f"row {row_number}: unsupported task_type {task_type!r}")
        decision = _parse_decision(row["decision"], field="decision", row_number=row_number)

        item = {
            "item_id": str(row["item_id"]).strip(),
            "task_type": task_type,
            "anonymized_input_ref": str(row["anonymized_input_ref"]).strip(),
            "model_output_ref": str(row["model_output_ref"]).strip(),
            "reviewer_id_hash": _reviewer_hash(str(row["reviewer_id_hash"])),
            "correctness_score": _parse_score(
                row["correctness_score"],
                field="correctness_score",
                row_number=row_number,
            ),
            "groundedness_score": _parse_score(
                row["groundedness_score"],
                field="groundedness_score",
                row_number=row_number,
            ),
            "safety_score": _parse_score(row["safety_score"], field="safety_score", row_number=row_number),
            "usefulness_score": _parse_score(
                row["usefulness_score"],
                field="usefulness_score",
                row_number=row_number,
            ),
            "privacy_risk_flag": _parse_required_bool(
                row["privacy_risk_flag"],
                field="privacy_risk_flag",
                row_number=row_number,
            ),
            "hallucination_flag": _parse_required_bool(
                row["hallucination_flag"],
                field="hallucination_flag",
                row_number=row_number,
            ),
            "fabrication_flag": _parse_required_bool(
                row["fabrication_flag"],
                field="fabrication_flag",
                row_number=row_number,
            ),
            "reviewer_comment": str(row["reviewer_comment"]).strip(),
            "decision": decision,
            "requires_adjudication": _parse_required_bool(
                row["requires_adjudication"],
                field="requires_adjudication",
                row_number=row_number,
            ),
            "adjudication_decision": _parse_decision(
                row["adjudication_decision"],
                field="adjudication_decision",
                row_number=row_number,
                allow_blank=True,
            ),
            "bad_case_ref": str(row["bad_case_ref"]).strip(),
        }
        if not item["item_id"]:
            raise ValueError(f"row {row_number}: item_id is required")
        if not item["anonymized_input_ref"] or not item["model_output_ref"]:
            raise ValueError(f"row {row_number}: review refs must be non-empty")
        items.append(item)
    return items


def summarize_items(
    items: list[dict[str, Any]],
    *,
    min_sample_size: int = 30,
    min_pass_rate: float = 0.90,
    max_hallucination_rate: float = 0.02,
    max_fabrication_rate: float = 0.01,
    max_privacy_risk_count: int = 0,
    min_adjudication_completion_rate: float = 1.0,
) -> dict[str, Any]:
    total = len(items)
    decisions = [item["decision"] for item in items]
    pass_count = decisions.count("pass")
    minor_count = decisions.count("minor_issue")
    major_count = decisions.count("major_issue")
    fail_count = decisions.count("fail")
    hallucination_count = sum(1 for item in items if item["hallucination_flag"])
    fabrication_count = sum(1 for item in items if item["fabrication_flag"])
    privacy_risk_count = sum(1 for item in items if item["privacy_risk_flag"])
    adjudication_required = [item for item in items if item["requires_adjudication"]]
    adjudication_completed = [
        item for item in adjudication_required if item["adjudication_decision"].strip()
    ]
    bad_case_count = sum(1 for item in items if item["bad_case_ref"].strip())

    def avg(field: str) -> float:
        if not total:
            return 0.0
        return round(sum(float(item[field]) for item in items) / total, 4)

    adjudication_completion_rate = (
        1.0 if not adjudication_required else len(adjudication_completed) / len(adjudication_required)
    )
    pass_rate = pass_count / total if total else 0.0
    hallucination_rate = hallucination_count / total if total else 0.0
    fabrication_rate = fabrication_count / total if total else 0.0
    threshold_failures: list[str] = []
    if total < min_sample_size:
        threshold_failures.append("insufficient_sample_size")
    if pass_rate < min_pass_rate:
        threshold_failures.append("pass_rate_below_threshold")
    if hallucination_rate > max_hallucination_rate:
        threshold_failures.append("hallucination_rate_above_threshold")
    if fabrication_rate > max_fabrication_rate:
        threshold_failures.append("fabrication_rate_above_threshold")
    if privacy_risk_count > max_privacy_risk_count:
        threshold_failures.append("privacy_risk_count_above_threshold")
    if adjudication_completion_rate < min_adjudication_completion_rate:
        threshold_failures.append("adjudication_incomplete")

    return {
        "total_items": total,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "minor_issue_count": minor_count,
        "major_issue_count": major_count,
        "pass_rate": round(pass_rate, 4),
        "average_correctness_score": avg("correctness_score"),
        "average_groundedness_score": avg("groundedness_score"),
        "average_safety_score": avg("safety_score"),
        "hallucination_rate": round(hallucination_rate, 4),
        "fabrication_rate": round(fabrication_rate, 4),
        "privacy_risk_count": privacy_risk_count,
        "adjudication_completion_rate": round(adjudication_completion_rate, 4),
        "adjudication_required_count": len(adjudication_required),
        "adjudication_completed_count": len(adjudication_completed),
        "bad_case_count": bad_case_count,
        "threshold_failures": threshold_failures,
        "production_quality_candidate_signal": not threshold_failures,
    }


def _agreement_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_item: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_item.setdefault(item["item_id"], []).append(item)
    comparable = 0
    agreed = 0
    for group in by_item.values():
        if len(group) < 2:
            continue
        comparable += 1
        decisions = {item["decision"] for item in group}
        if len(decisions) == 1:
            agreed += 1
    return {
        "comparable_item_count": comparable,
        "decision_agreement_rate": round(agreed / comparable, 4) if comparable else 0.0,
    }


def _batch_value(rows: list[dict[str, Any]], key: str, default: str = "") -> str:
    for row in rows:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return default


def build_human_review_batch(
    input_path: Path,
    *,
    batch_id: str | None = None,
    dataset_name: str | None = None,
    sampling_method: str | None = None,
    reviewer_role: str | None = None,
    privacy_sanitized: bool | None = None,
) -> dict[str, Any]:
    rows = load_review_rows(input_path)
    for row_number, row in enumerate(rows, start=1):
        _check_no_private_data(
            {key: row.get(key, "") for key in BATCH_OPTIONAL_FIELDS},
            row_number=row_number,
        )
    items = normalize_review_items(rows)
    summary = summarize_items(items)
    reviewer_hashes = sorted({item["reviewer_id_hash"] for item in items})
    row_roles = sorted(
        {str(row.get("reviewer_role", "")).strip() for row in rows if str(row.get("reviewer_role", "")).strip()}
    )
    roles = sorted({role for role in [reviewer_role, *row_roles] if role})
    sanitized = privacy_sanitized
    if sanitized is None:
        sanitized = all(_parse_bool(row.get("privacy_sanitized", "false")) for row in rows)

    limitations: list[str] = []
    if len(reviewer_hashes) < 2:
        limitations.append("At least two independent reviewers are required.")
    if not sanitized:
        limitations.append("Input dataset was not marked privacy_sanitized.")
    limitations.extend(summary["threshold_failures"])

    return {
        "proof_type": "human_review",
        "review_batch_id": batch_id
        or _batch_value(rows, "review_batch_id")
        or f"human-review-{uuid.uuid4().hex[:12]}",
        "created_at": _utc_now(),
        "reviewer_count": len(reviewer_hashes),
        "reviewer_roles": roles,
        "dataset_name": dataset_name or _batch_value(rows, "dataset_name", "anonymized_review_batch"),
        "sample_size": summary["total_items"],
        "sampling_method": sampling_method or _batch_value(rows, "sampling_method", "documented_external_sample"),
        "privacy_sanitized": bool(sanitized),
        "review_items": items,
        "agreement_metrics": _agreement_metrics(items),
        "adjudication_required_count": summary["adjudication_required_count"],
        "adjudication_completed_count": summary["adjudication_completed_count"],
        "bad_case_count": summary["bad_case_count"],
        "summary": summary,
        "production_quality_candidate_signal": (
            summary["production_quality_candidate_signal"]
            and len(reviewer_hashes) >= 2
            and bool(sanitized)
        ),
        "limitations": limitations,
    }


def validate_human_review_batch_payload(payload: dict[str, Any]) -> list[str]:
    required = {
        "review_batch_id",
        "created_at",
        "reviewer_count",
        "reviewer_roles",
        "dataset_name",
        "sample_size",
        "sampling_method",
        "privacy_sanitized",
        "review_items",
        "agreement_metrics",
        "adjudication_required_count",
        "adjudication_completed_count",
        "bad_case_count",
        "production_quality_candidate_signal",
        "limitations",
    }
    errors = [f"missing required field: {field}" for field in sorted(required) if field not in payload]
    if payload.get("proof_type") != "human_review":
        errors.append("proof_type must be human_review")
    for index, item in enumerate(payload.get("review_items", []), start=1):
        missing = sorted(field for field in REQUIRED_ITEM_FIELDS if field not in item)
        errors.extend(f"review_items[{index}] missing required field: {field}" for field in missing)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-id")
    parser.add_argument("--dataset-name")
    parser.add_argument("--sampling-method")
    parser.add_argument("--reviewer-role")
    parser.add_argument("--privacy-sanitized", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    payload = build_human_review_batch(
        args.input,
        batch_id=args.batch_id,
        dataset_name=args.dataset_name,
        sampling_method=args.sampling_method,
        reviewer_role=args.reviewer_role,
        privacy_sanitized=args.privacy_sanitized if args.privacy_sanitized else None,
    )
    errors = validate_human_review_batch_payload(payload)
    if errors:
        raise ValueError(f"invalid human review batch: {errors}")

    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.dry_run:
        print(rendered, end="")
        return 0
    output = _output_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
