#!/usr/bin/env python3
"""Generate an anonymized blank human review sample pack."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import random
import re
import zipfile
from typing import Any
from xml.sax.saxutils import escape


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_DIR = REPO_ROOT / "evals" / "datasets" / "anonymized_benchmark"
DEFAULT_CSV_OUTPUT = "evidence/private_outputs/human_review_sample_pack.{timestamp}.csv"
DEFAULT_XLSX_OUTPUT = "evidence/private_outputs/human_review_fillable_simple_{timestamp}.xlsx"
DEFAULT_SAMPLE_SIZE = 30
DEFAULT_SEED = 35
TASK_MODULES = {
    "jd_parse": "jd_parser_benchmark.jsonl",
    "resume_parse": "resume_parser_benchmark.jsonl",
    "match_score": "match_benchmark.jsonl",
    "rag_answer": "rag_answer_benchmark.jsonl",
    "project_rewrite": "project_rewrite_benchmark.jsonl",
    "agent_workflow": "agent_workflow_benchmark.jsonl",
}
TASK_TYPE_LABELS = {
    "jd_parse": "JD 解析审核",
    "resume_parse": "简历解析审核",
    "match_score": "匹配分数审核",
    "rag_answer": "RAG 回答审核",
    "project_rewrite": "项目改写审核",
    "agent_workflow": "Agent 流程审核",
}
REVIEW_INSTRUCTIONS = {
    "jd_parse": "检查 JD 解析结果是否正确抽取岗位类别、技能、风险和隐藏要求。",
    "resume_parse": "检查简历解析结果是否正确抽取章节、技能、项目和风险信号。",
    "match_score": "检查匹配分数、证据、差距和风险扣分是否合理。",
    "rag_answer": "检查回答是否基于证据、引用正确且没有 unsupported claim。",
    "project_rewrite": "检查项目改写是否贴合 JD 且没有编造事实。",
    "agent_workflow": "检查 Agent 流程状态、下一步和 Bad Case 处理是否合理。",
}
MACHINE_FIELDS = [
    "review_batch_id",
    "dataset_name",
    "sampling_method",
    "reviewer_role",
    "privacy_sanitized",
    "item_id",
    "task_type",
    "anonymized_input_ref",
    "model_output_ref",
]
REVIEW_CONTEXT_FIELDS = [
    "task_type_label",
    "input_summary",
    "model_output_summary",
    "review_instruction",
]
REVIEWER_FIELDS = [
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
]
CSV_FIELDS = [
    *MACHINE_FIELDS,
    *REVIEW_CONTEXT_FIELDS,
    *REVIEWER_FIELDS,
]
SCORE_FIELDS = ["correctness_score", "groundedness_score", "safety_score", "usefulness_score"]
BOOLEAN_FIELDS = [
    "privacy_risk_flag",
    "hallucination_flag",
    "fabrication_flag",
    "requires_adjudication",
]
DECISION_FIELDS = ["decision", "adjudication_decision"]
FILL_SHEET_NAME = "填写表"
IMPORT_SHEET_NAME = "导入字段_不要改"
INSTRUCTIONS_SHEET_NAME = "填写说明"
OPTIONS_SHEET_NAME = "选项"
FILL_HEADER_ROW = 6
FILL_DATA_START_ROW = FILL_HEADER_ROW + 1
FILL_COLUMNS = [
    ("sequence", "序号"),
    ("task_type_label", "审核类型"),
    ("input_summary", "输入摘要（匿名）"),
    ("model_output_summary", "模型输出摘要"),
    ("review_instruction", "审核说明"),
    ("correctness_score", "正确性\n0-1"),
    ("groundedness_score", "有依据\n0-1"),
    ("safety_score", "安全性\n0-1"),
    ("usefulness_score", "有用性\n0-1"),
    ("privacy_risk_flag", "隐私风险"),
    ("hallucination_flag", "幻觉"),
    ("fabrication_flag", "编造"),
    ("decision", "结论"),
    ("requires_adjudication", "需复审"),
    ("reviewer_comment", "备注"),
    ("adjudication_decision", "复审结论"),
    ("bad_case_ref", "Bad Case编号"),
    ("item_id", "item_id"),
]
FILL_FORMULA_COLUMNS = {
    "correctness_score": "F",
    "groundedness_score": "G",
    "safety_score": "H",
    "usefulness_score": "I",
    "privacy_risk_flag": "J",
    "hallucination_flag": "K",
    "fabrication_flag": "L",
    "decision": "M",
    "requires_adjudication": "N",
    "reviewer_comment": "O",
    "adjudication_decision": "P",
    "bad_case_ref": "Q",
}
FILL_REVIEWER_FIELDS = set(SCORE_FIELDS + BOOLEAN_FIELDS + DECISION_FIELDS + ["reviewer_comment", "bad_case_ref"])
PII_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{8,}\d)(?!\d)"),
]


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _output_path(path: str) -> Path:
    return Path(path.format(timestamp=_timestamp()))


def default_output_for_format(output_format: str) -> str:
    if output_format == "xlsx":
        return DEFAULT_XLSX_OUTPUT
    return DEFAULT_CSV_OUTPUT


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _assert_public_safe(value: str) -> None:
    for pattern in PII_PATTERNS:
        if pattern.search(value):
            raise ValueError("sample pack contains obvious PII")
    lowered = value.lower()
    forbidden = ["raw_text", "raw_resume", "resume_text", "jd_text", "chunk_text", "interview_answer"]
    if any(token in lowered for token in forbidden):
        raise ValueError("sample pack contains raw private field markers")


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _case_input_summary(case: dict[str, Any]) -> str:
    return (
        f"{case.get('summary', '')}; input_ref={_safe_json(case.get('input', {}))}; "
        f"difficulty={case.get('difficulty', '')}"
    )


def _case_output_summary(case: dict[str, Any]) -> str:
    return (
        f"signals={_safe_json(case.get('signals', {}))}; "
        f"expected_output_ref={_safe_json(case.get('expected_output', case.get('expected', {})))}"
    )


def _load_cases(dataset_dir: Path) -> dict[str, list[dict[str, Any]]]:
    cases_by_task: dict[str, list[dict[str, Any]]] = {}
    for task_type, filename in TASK_MODULES.items():
        path = dataset_dir / filename
        if not path.exists():
            raise FileNotFoundError(path)
        rows = []
        for case in _load_jsonl(path):
            if case.get("privacy_check_passed") is not True:
                continue
            note = str(case.get("anonymization_note", "")).lower()
            if not note or "synthetic only" in note:
                continue
            rows.append(case)
        if not rows:
            raise ValueError(f"no public-safe cases found for {task_type}")
        cases_by_task[task_type] = rows
    return cases_by_task


def _sample_counts(sample_size: int) -> dict[str, int]:
    task_types = list(TASK_MODULES)
    if sample_size < len(task_types):
        raise ValueError(f"sample_size must be at least {len(task_types)} to cover every task_type")
    base = sample_size // len(task_types)
    remainder = sample_size % len(task_types)
    return {
        task_type: base + (1 if index < remainder else 0)
        for index, task_type in enumerate(task_types)
    }


def build_sample_pack_rows(
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    review_batch_id: str = "human-review-sample-pack-v35b",
) -> list[dict[str, str]]:
    rng = random.Random(seed)
    cases_by_task = _load_cases(dataset_dir)
    counts = _sample_counts(sample_size)
    rows: list[dict[str, str]] = []
    for task_type, count in counts.items():
        cases = list(cases_by_task[task_type])
        rng.shuffle(cases)
        if len(cases) < count:
            raise ValueError(f"not enough cases for {task_type}: need {count}, found {len(cases)}")
        for case in cases[:count]:
            case_id = str(case.get("case_id", "")).strip()
            if not case_id:
                raise ValueError(f"{task_type} case missing case_id")
            row = {
                "review_batch_id": review_batch_id,
                "dataset_name": "anonymized_benchmark",
                "sampling_method": f"seeded_balanced_by_task_type_seed_{seed}",
                "reviewer_role": "external_reviewer",
                "privacy_sanitized": "true",
                "item_id": f"hr_{task_type}_{case_id}",
                "task_type": task_type,
                "anonymized_input_ref": f"anonymized_benchmark:{task_type}:{case_id}:input",
                "model_output_ref": f"anonymized_benchmark:{task_type}:{case_id}:model_output",
                "task_type_label": TASK_TYPE_LABELS[task_type],
                "input_summary": _case_input_summary(case),
                "model_output_summary": _case_output_summary(case),
                "review_instruction": REVIEW_INSTRUCTIONS[task_type],
                "reviewer_id_hash": "",
                "correctness_score": "",
                "groundedness_score": "",
                "safety_score": "",
                "usefulness_score": "",
                "privacy_risk_flag": "",
                "hallucination_flag": "",
                "fabrication_flag": "",
                "reviewer_comment": "",
                "decision": "",
                "requires_adjudication": "",
                "adjudication_decision": "",
                "bad_case_ref": "",
            }
            for value in row.values():
                _assert_public_safe(value)
            rows.append(row)
    rows.sort(key=lambda item: (item["task_type"], item["item_id"]))
    return rows


def render_csv(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _column_letter(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _cell_xml(row_index: int, column_index: int, value: str, style_index: int) -> str:
    ref = f"{_column_letter(column_index)}{row_index}"
    text = str(value)
    if text == "":
        return f'<c r="{ref}" s="{style_index}"/>'
    if text.startswith("="):
        return f'<c r="{ref}" s="{style_index}"><f>{escape(text[1:])}</f></c>'
    return (
        f'<c r="{ref}" s="{style_index}" t="inlineStr">'
        f"<is><t>{escape(text)}</t></is></c>"
    )


def _worksheet_xml(
    *,
    cols_xml: str,
    rows_xml: str,
    freeze_xml: str = "",
    auto_filter_ref: str = "",
    validations_xml: str = "",
) -> str:
    auto_filter_xml = f'<autoFilter ref="{auto_filter_ref}"/>' if auto_filter_ref else ""
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
{freeze_xml}
<cols>{cols_xml}</cols>
<sheetData>{rows_xml}</sheetData>
{auto_filter_xml}
{validations_xml}
</worksheet>'''


def _cols_xml(widths: list[int]) -> str:
    return "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )


def _freeze_xml(split_row: int, top_left_cell: str) -> str:
    return (
        '<sheetViews><sheetView workbookViewId="0">'
        f'<pane ySplit="{split_row}" topLeftCell="{top_left_cell}" '
        'activePane="bottomLeft" state="frozen"/>'
        "</sheetView></sheetViews>"
    )


def _data_validations_xml(validations: list[str]) -> str:
    if not validations:
        return ""
    return f'<dataValidations count="{len(validations)}">{"".join(validations)}</dataValidations>'


def _fill_validations(last_row: int) -> str:
    validations: list[str] = []
    for column in ["J", "K", "L", "N"]:
        validations.append(
            f'<dataValidation type="list" allowBlank="1" showInputMessage="1" '
            f'promptTitle="Reviewer input" prompt="Choose true or false." '
            f'sqref="{column}{FILL_DATA_START_ROW}:{column}{last_row}">'
            '<formula1>"true,false"</formula1></dataValidation>'
        )
    for column in ["M", "P"]:
        validations.append(
            f'<dataValidation type="list" allowBlank="1" showInputMessage="1" '
            f'promptTitle="Reviewer input" prompt="Choose pass, minor_issue, major_issue, or fail." '
            f'sqref="{column}{FILL_DATA_START_ROW}:{column}{last_row}">'
            '<formula1>"pass,minor_issue,major_issue,fail"</formula1></dataValidation>'
        )
    for column in ["F", "G", "H", "I"]:
        validations.append(
            f'<dataValidation type="decimal" operator="between" allowBlank="1" '
            f'showInputMessage="1" promptTitle="Reviewer score" '
            f'prompt="Use 1.0 good, 0.8 minor issue, 0.5 major issue, 0.0 fail." '
            f'sqref="{column}{FILL_DATA_START_ROW}:{column}{last_row}">'
            "<formula1>0</formula1><formula2>1</formula2></dataValidation>"
        )
    return _data_validations_xml(validations)


def _first_reviewer_id(rows: list[dict[str, str]]) -> str:
    for row in rows:
        value = row.get("reviewer_id_hash", "").strip()
        if value:
            return value
    return ""


def _fill_sheet_xml(rows: list[dict[str, str]]) -> str:
    last_row = FILL_DATA_START_ROW + len(rows) - 1
    last_column = _column_letter(len(FILL_COLUMNS))
    widths = [8, 18, 46, 46, 34, 12, 12, 12, 12, 12, 12, 12, 15, 12, 32, 15, 18, 34]
    row_xml: list[str] = []
    row_xml.append(
        '<row r="1" ht="24" customHeight="1">'
        + _cell_xml(1, 1, "CareerAgent 人工审核表（简洁版）", 1)
        + "</row>"
    )
    row_xml.append('<row r="2"/>')
    row_xml.append(
        '<row r="3">'
        + _cell_xml(3, 1, "Reviewer ID Hash（填一次即可）", 1)
        + _cell_xml(3, 2, _first_reviewer_id(rows), 3)
        + _cell_xml(3, 3, f"说明：请从第 {FILL_DATA_START_ROW} 行开始逐行审核。不要修改 item_id。", 2)
        + "</row>"
    )
    row_xml.append('<row r="4"/>')
    row_xml.append('<row r="5"/>')
    header_cells = [
        _cell_xml(FILL_HEADER_ROW, index, label, 1)
        for index, (_field, label) in enumerate(FILL_COLUMNS, start=1)
    ]
    row_xml.append(
        f'<row r="{FILL_HEADER_ROW}" ht="38" customHeight="1">'
        + "".join(header_cells)
        + "</row>"
    )
    for offset, row in enumerate(rows, start=0):
        row_index = FILL_DATA_START_ROW + offset
        cells = []
        for column_index, (field, _label) in enumerate(FILL_COLUMNS, start=1):
            value = str(offset + 1) if field == "sequence" else row.get(field, "")
            style = 3 if field in FILL_REVIEWER_FIELDS else 2
            cells.append(_cell_xml(row_index, column_index, value, style))
        row_xml.append(f'<row r="{row_index}" ht="72" customHeight="1">{"".join(cells)}</row>')
    return _worksheet_xml(
        cols_xml=_cols_xml(widths),
        rows_xml="".join(row_xml),
        freeze_xml=_freeze_xml(FILL_HEADER_ROW, f"A{FILL_DATA_START_ROW}"),
        auto_filter_ref=f"A{FILL_HEADER_ROW}:{last_column}{last_row}",
        validations_xml=_fill_validations(last_row),
    )


def _import_formula(field: str, fill_row_index: int) -> str:
    if field == "reviewer_id_hash":
        return f"='{FILL_SHEET_NAME}'!$B$3"
    column = FILL_FORMULA_COLUMNS.get(field)
    if column:
        return f"='{FILL_SHEET_NAME}'!{column}{fill_row_index}"
    return ""


def _import_sheet_xml(rows: list[dict[str, str]]) -> str:
    last_row = len(rows) + 1
    last_column = _column_letter(len(CSV_FIELDS))
    widths = [24, 24, 34, 22, 18, 36, 18, 48, 48, 18, 44, 44, 34, 22, 14, 14, 14, 14, 14, 14, 14, 32, 18, 14, 18, 20]
    row_xml: list[str] = []
    row_xml.append(
        '<row r="1" ht="32" customHeight="1">'
        + "".join(_cell_xml(1, index, field, 1) for index, field in enumerate(CSV_FIELDS, start=1))
        + "</row>"
    )
    for offset, row in enumerate(rows, start=0):
        row_index = offset + 2
        fill_row_index = FILL_DATA_START_ROW + offset
        cells = []
        for column_index, field in enumerate(CSV_FIELDS, start=1):
            value = _import_formula(field, fill_row_index) if field in REVIEWER_FIELDS else row.get(field, "")
            style = 3 if field in REVIEWER_FIELDS else 2
            cells.append(_cell_xml(row_index, column_index, value, style))
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return _worksheet_xml(
        cols_xml=_cols_xml(widths),
        rows_xml="".join(row_xml),
        freeze_xml=_freeze_xml(1, "A2"),
        auto_filter_ref=f"A1:{last_column}{last_row}",
    )


def _simple_table_sheet_xml(rows: list[list[str]], widths: list[int]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        style = 1 if row_index == 1 else 2
        cells = [
            _cell_xml(row_index, column_index, value, style)
            for column_index, value in enumerate(row, start=1)
        ]
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return _worksheet_xml(
        cols_xml=_cols_xml(widths),
        rows_xml="".join(row_xml),
        freeze_xml=_freeze_xml(1, "A2"),
    )


def _instructions_sheet_xml() -> str:
    rows = [
        ["CareerAgent 人工审核填写说明"],
        [""],
        ["1. 只填写“填写表”。不要修改 item_id，也不要修改“导入字段_不要改”。"],
        ["2. 每一行看：审核类型、输入摘要（匿名）、模型输出摘要、审核说明。"],
        ["3. 分数：1.0=good，0.8=minor issue，0.5=major issue，0.0=fail。"],
        ["4. 隐私风险、幻觉、编造、需复审必须显式选择 true 或 false。"],
        ["5. 结论/复审结论只能使用 pass、minor_issue、major_issue、fail。"],
        ["6. 不要写入真实姓名、邮箱、电话、API key、真实简历/JD 原文或私有证据。"],
    ]
    return _simple_table_sheet_xml(rows, [110])


def _options_sheet_xml() -> str:
    rows = [
        ["decision", "bool"],
        ["pass", "true"],
        ["minor_issue", "false"],
        ["major_issue", ""],
        ["fail", ""],
    ]
    return _simple_table_sheet_xml(rows, [22, 18])


def render_xlsx(rows: list[dict[str, str]], output_path: Path) -> None:
    sheet_names = [FILL_SHEET_NAME, IMPORT_SHEET_NAME, INSTRUCTIONS_SHEET_NAME, OPTIONS_SHEET_NAME]
    sheet_overrides = "\n".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, len(sheet_names) + 1)
    )
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheet_overrides}
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''.format(sheet_overrides=sheet_overrides)
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''
    workbook_sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheet_names, start=1)
    )
    workbook = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>{workbook_sheets}</sheets>
</workbook>'''
    workbook_sheet_rels = "\n".join(
        f'<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, len(sheet_names) + 1)
    )
    workbook_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{workbook_sheet_rels}
<Relationship Id="rId{len(sheet_names) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFD9EAF7"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="2"><border/><border><left style="thin"/><right style="thin"/><top style="thin"/><bottom style="thin"/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf><xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:creator>CareerAgent</dc:creator><cp:lastModifiedBy>CareerAgent</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{datetime.now(timezone.utc).isoformat()}</dcterms:created></cp:coreProperties>'''
    app = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>CareerAgent</Application></Properties>'''
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", _fill_sheet_xml(rows))
        archive.writestr("xl/worksheets/sheet2.xml", _import_sheet_xml(rows))
        archive.writestr("xl/worksheets/sheet3.xml", _instructions_sheet_xml())
        archive.writestr("xl/worksheets/sheet4.xml", _options_sheet_xml())
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("docProps/core.xml", core)
        archive.writestr("docProps/app.xml", app)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    parser.add_argument("--format", choices=["csv", "xlsx"], default="csv")
    parser.add_argument("--xlsx", action="store_true", help="Shortcut for --format xlsx.")
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    output_format = "xlsx" if args.xlsx else args.format
    rows = build_sample_pack_rows(sample_size=args.sample_size, seed=args.seed)
    payload = render_csv(rows)
    _assert_public_safe(payload)
    if args.dry_run:
        print(payload, end="")
        return 0
    output = _output_path(args.output or default_output_for_format(output_format))
    output.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "xlsx":
        render_xlsx(rows, output)
    else:
        output.write_text(payload, encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
