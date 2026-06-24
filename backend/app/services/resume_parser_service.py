from __future__ import annotations

import re
from collections.abc import Iterable

from app.schemas.resumes import StructuredResume


PARSER_METHOD = "deterministic_resume_parser_v1"

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
URL_RE = re.compile(r"https?://[^\s,;]+|(?:github|linkedin)\.com/[^\s,;]+", re.IGNORECASE)
DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:19|20)\d{2}(?:[./-]\d{1,2})?)\s*"
    r"(?:-|–|—|to|至|到)\s*"
    r"(?P<end>present|current|now|至今|现在|(?:19|20)\d{2}(?:[./-]\d{1,2})?)",
    re.IGNORECASE,
)

SECTION_HEADINGS = {
    "education": {
        "education",
        "education background",
        "academic background",
        "教育经历",
        "教育背景",
        "学历",
    },
    "projects": {
        "projects",
        "project experience",
        "selected projects",
        "项目经历",
        "项目经验",
        "项目",
    },
    "experience": {
        "experience",
        "work experience",
        "professional experience",
        "internship experience",
        "工作经历",
        "实习经历",
        "经历",
    },
    "skills": {
        "skills",
        "technical skills",
        "core skills",
        "技能",
        "专业技能",
        "技术栈",
    },
    "certificates": {
        "certificates",
        "certifications",
        "licenses",
        "证书",
        "认证",
        "资格证书",
    },
    "awards": {
        "awards",
        "honors",
        "honours",
        "获奖",
        "荣誉",
        "奖项",
    },
}

SKILL_CATALOG: dict[str, list[str]] = {
    "programming": ["Python", "TypeScript", "JavaScript", "Java", "Go", "C++"],
    "backend": [
        "FastAPI",
        "Django",
        "Flask",
        "Node.js",
        "Express",
        "Spring Boot",
        "REST",
        "GraphQL",
    ],
    "frontend": ["React", "Vue", "Angular", "HTML", "CSS", "Tailwind"],
    "ai": [
        "LLM",
        "RAG",
        "LangChain",
        "OpenAI",
        "PyTorch",
        "TensorFlow",
        "scikit-learn",
        "Machine Learning",
        "NLP",
        "Embeddings",
    ],
    "database": ["PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "SQL"],
    "tools": ["Docker", "Kubernetes", "Git", "AWS", "GCP", "Azure", "Linux", "CI/CD", "GitHub Actions"],
}

DEGREE_KEYWORDS = [
    "bachelor",
    "master",
    "phd",
    "doctor",
    "b.s.",
    "m.s.",
    "本科",
    "学士",
    "硕士",
    "博士",
]


def parse_structured_resume(raw_text: str) -> StructuredResume:
    sections = _split_sections(raw_text)
    return StructuredResume(
        basic_info=_parse_basic_info(raw_text, sections.get("summary", [])),
        education=_parse_education(sections.get("education", [])),
        projects=_parse_projects(sections.get("projects", [])),
        experience=_parse_experience(sections.get("experience", [])),
        skills=_parse_skills(raw_text),
        certificates=_parse_named_items(sections.get("certificates", [])),
        awards=_parse_named_items(sections.get("awards", [])),
    )


def _split_sections(raw_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"summary": []}
    current = "summary"
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = _section_key_for_line(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _section_key_for_line(line: str) -> str | None:
    normalized = _normalize_heading(line)
    for key, headings in SECTION_HEADINGS.items():
        if normalized in headings:
            return key
    return None


def _normalize_heading(line: str) -> str:
    cleaned = re.sub(r"^[#>\-\*\d.\s]+", "", line).strip()
    cleaned = cleaned.rstrip(":：").strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _strip_marker(line: str) -> str:
    return re.sub(r"^[#>\-\*\u2022\d.\s]+", "", line).strip()


def _parse_basic_info(raw_text: str, summary_lines: list[str]) -> dict[str, object]:
    email_match = EMAIL_RE.search(raw_text)
    phone_match = PHONE_RE.search(raw_text)
    links = sorted({match.rstrip(").]") for match in URL_RE.findall(raw_text)})
    name = _parse_name(summary_lines)
    location = _parse_labeled_value(
        raw_text.splitlines(), ["location", "city", "地点", "城市", "所在地"]
    )
    return {
        "name": name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0).strip() if phone_match else None,
        "location": location,
        "links": links,
    }


def _parse_name(summary_lines: list[str]) -> str | None:
    for line in summary_lines[:5]:
        candidate = _strip_marker(line)
        lowered = candidate.lower()
        if not candidate or any(token in lowered for token in ["resume", "cv", "@", "http"]):
            continue
        if PHONE_RE.search(candidate):
            continue
        if 1 <= len(candidate.split()) <= 5 and len(candidate) <= 80:
            return candidate
    return None


def _parse_labeled_value(lines: Iterable[str], labels: list[str]) -> str | None:
    for line in lines:
        value = _line_value_for_labels(line, labels)
        if value:
            return value
    return None


def _line_value_for_labels(line: str, labels: list[str]) -> str | None:
    clean = _strip_marker(line)
    lower = clean.lower()
    for label in labels:
        label_lower = label.lower()
        for separator in (":", "："):
            prefix = f"{label_lower}{separator}"
            if lower.startswith(prefix):
                return clean[len(prefix) :].strip() or None
    return None


def _parse_skills(raw_text: str) -> dict[str, list[str]]:
    skills: dict[str, list[str]] = {}
    for category, candidates in SKILL_CATALOG.items():
        found = [skill for skill in candidates if _contains_skill(raw_text, skill)]
        skills[category] = found
    return skills


def _contains_skill(raw_text: str, skill: str) -> bool:
    lowered = raw_text.lower()
    skill_lower = skill.lower()
    if skill_lower in {"c++", "node.js", "ci/cd", "github actions", "scikit-learn"}:
        return skill_lower in lowered
    return re.search(rf"\b{re.escape(skill_lower)}\b", lowered) is not None


def _parse_education(lines: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line in _meaningful_lines(lines):
        start_date, end_date = _parse_period(line)
        clean = _strip_marker(line)
        segments = _split_segments(clean)
        degree = _first_segment_matching(segments, DEGREE_KEYWORDS)
        courses = _parse_list_value(clean, ["courses", "coursework", "核心课程", "课程"])
        major = _parse_labeled_value([clean], ["major", "专业"])
        school = _first_school_segment(segments, degree, major, courses)
        if not any([school, degree, major, start_date, end_date, courses]):
            continue
        records.append(
            {
                "school": school,
                "degree": degree,
                "major": major,
                "start_date": start_date,
                "end_date": end_date,
                "courses": courses,
                "raw_text": clean,
            }
        )
    return records


def _first_school_segment(
    segments: list[str],
    degree: str | None,
    major: str | None,
    courses: list[str],
) -> str | None:
    course_set = {course.lower() for course in courses}
    for segment in segments:
        lowered = segment.lower()
        if segment == degree or segment == major:
            continue
        if lowered in course_set or "course" in lowered or "课程" in segment:
            continue
        if DATE_RANGE_RE.search(segment):
            continue
        return segment
    return None


def _parse_projects(lines: list[str]) -> list[dict[str, object]]:
    return [_parse_project_block(block) for block in _split_blocks(lines) if block]


def _parse_project_block(block: list[str]) -> dict[str, object]:
    first_line = _strip_marker(block[0]) if block else ""
    name = _parse_labeled_value(block, ["name", "project", "项目名称"]) or first_line or None
    role = _parse_labeled_value(block, ["role", "角色"])
    period = _parse_labeled_value(block, ["period", "date", "time", "时间", "周期"])
    start_date, end_date = _parse_period(period or "\n".join(block))
    tech_stack = _parse_list_value("\n".join(block), ["tech", "tech stack", "技术栈", "技术"])
    responsibilities = _parse_list_value(
        "\n".join(block), ["responsibilities", "duties", "负责", "职责"]
    )
    results = _parse_list_value("\n".join(block), ["results", "impact", "outcome", "成果", "结果"])
    evidence = _parse_list_value("\n".join(block), ["evidence", "proof", "证据", "佐证"])
    background = _parse_labeled_value(block, ["background", "context", "背景"])
    return {
        "name": name,
        "role": role,
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "background": background,
        "tech_stack": tech_stack,
        "responsibilities": responsibilities,
        "results": results,
        "evidence": evidence,
        "risk_flags": [],
        "raw_text": "\n".join(_strip_marker(line) for line in block),
    }


def _parse_experience(lines: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for block in _split_blocks(lines):
        first_line = _strip_marker(block[0]) if block else ""
        company = _parse_labeled_value(block, ["company", "公司"])
        role = _parse_labeled_value(block, ["role", "title", "岗位", "职位"])
        period = _parse_labeled_value(block, ["period", "date", "time", "时间", "周期"])
        start_date, end_date = _parse_period(period or "\n".join(block))
        responsibilities = _parse_list_value(
            "\n".join(block), ["responsibilities", "duties", "负责", "职责"]
        )
        results = _parse_list_value("\n".join(block), ["results", "impact", "成果", "结果"])
        if any([company, role, start_date, end_date, responsibilities, results]):
            records.append(
                {
                    "company": company or first_line or None,
                    "role": role,
                    "period": period,
                    "start_date": start_date,
                    "end_date": end_date,
                    "responsibilities": responsibilities,
                    "results": results,
                    "raw_text": "\n".join(_strip_marker(line) for line in block),
                }
            )
    return records


def _parse_named_items(lines: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line in _meaningful_lines(lines):
        clean = _strip_marker(line)
        start_date, end_date = _parse_period(clean)
        records.append(
            {
                "name": clean,
                "start_date": start_date,
                "end_date": end_date,
                "raw_text": clean,
            }
        )
    return records


def _split_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in _meaningful_lines(lines):
        if current and _looks_like_block_title(line):
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _looks_like_block_title(line: str) -> bool:
    clean = _strip_marker(line)
    if line.lstrip().startswith("#"):
        return True
    if _line_value_for_labels(clean, ["name", "project", "项目名称"]):
        return True
    if ":" in clean or "：" in clean:
        return False
    return 1 <= len(clean.split()) <= 8 and len(clean) <= 100


def _meaningful_lines(lines: list[str]) -> list[str]:
    return [line for line in (item.strip() for item in lines) if line]


def _parse_period(text: str | None) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    match = DATE_RANGE_RE.search(text)
    if not match:
        return None, None
    return _normalize_date(match.group("start")), _normalize_date(match.group("end"))


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.strip().lower()
    if lowered in {"present", "current", "now", "至今", "现在"}:
        return "present"
    return lowered.replace("/", "-").replace(".", "-")


def _parse_list_value(text: str, labels: list[str]) -> list[str]:
    for line in text.splitlines():
        value = _line_value_for_labels(line, labels)
        if value:
            return _split_list(value)
    return []


def _split_list(value: str) -> list[str]:
    items = re.split(r"[,;/，；、]|\s+\|\s+", value)
    return [item.strip(" .") for item in items if item.strip(" .")]


def _split_segments(value: str) -> list[str]:
    segments = re.split(r"\s+\|\s+|[,，；;]", value)
    return [segment.strip() for segment in segments if segment.strip()]


def _first_segment_matching(segments: list[str], keywords: list[str]) -> str | None:
    for segment in segments:
        lowered = segment.lower()
        if any(keyword in lowered for keyword in keywords):
            return segment
    return None
