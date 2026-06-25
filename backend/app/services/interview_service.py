from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.job import JobDescription, JobProfile
from app.models.project import Project, ProjectRewrite
from app.models.resume import ResumeVersion
from app.repositories import interview_repository
from app.schemas.interviews import (
    InterviewDifficulty,
    InterviewQuestionGenerateRequest,
    InterviewQuestionGenerateResponse,
    InterviewQuestionRecord,
    InterviewQuestionType,
)


PREVIEW_CHARS = 180
GENERATION_STRATEGY = "deterministic_interview_questions_v1"


def generate_questions(
    db: Session,
    payload: InterviewQuestionGenerateRequest,
) -> InterviewQuestionGenerateResponse:
    _, job_profile = _get_active_job_with_profile(db, payload.jd_id)
    resume_version = _get_resume_version(db, payload.resume_version_id)
    project = _get_project(db, payload.project_id) if payload.project_id else None
    project_rewrite = (
        _get_project_rewrite(db, payload.project_rewrite_id)
        if payload.project_rewrite_id
        else None
    )
    if project and project_rewrite and project_rewrite.project_id != project.id:
        raise AppError(
            code="project_rewrite_project_mismatch",
            message="Project rewrite does not belong to the requested project.",
            status_code=400,
            details={
                "project_id": project.id,
                "project_rewrite_id": project_rewrite.id,
            },
        )

    requested_types = set(payload.question_types or [])
    warnings: list[str] = []
    need_more_info: list[str] = []
    candidates = _build_question_candidates(
        job_profile=job_profile,
        resume_version=resume_version,
        project=project,
        project_rewrite=project_rewrite,
    )
    if requested_types:
        candidates = [
            candidate
            for candidate in candidates
            if candidate["question_type"] in requested_types
        ]

    if not candidates:
        warnings.append("No strongly grounded interview question could be generated.")
        need_more_info.extend(
            [
                "Add JD required skills or interview focus.",
                "Add structured resume skills or project facts.",
            ]
        )
        candidates = [_fallback_question(job_profile, resume_version)]
        if requested_types:
            candidates = [
                candidate
                for candidate in candidates
                if candidate["question_type"] in requested_types
            ]

    questions = _dedupe_questions(candidates)[: payload.max_questions]
    if not questions:
        return InterviewQuestionGenerateResponse(
            questions=[],
            warnings=warnings,
            need_more_info=need_more_info,
        )
    records = interview_repository.create_questions(
        db,
        jd_id=payload.jd_id.strip(),
        resume_version_id=payload.resume_version_id.strip(),
        project_id=payload.project_id.strip() if payload.project_id else None,
        project_rewrite_id=(
            payload.project_rewrite_id.strip() if payload.project_rewrite_id else None
        ),
        questions=questions,
    )
    return InterviewQuestionGenerateResponse(
        questions=records,
        warnings=warnings,
        need_more_info=need_more_info,
    )


def list_questions(
    db: Session,
    *,
    jd_id: str | None = None,
    resume_version_id: str | None = None,
    project_id: str | None = None,
    question_type: InterviewQuestionType | None = None,
    difficulty: InterviewDifficulty | None = None,
) -> list[InterviewQuestionRecord]:
    return interview_repository.list_questions(
        db,
        jd_id=_normalize_optional_id(jd_id),
        resume_version_id=_normalize_optional_id(resume_version_id),
        project_id=_normalize_optional_id(project_id),
        question_type=question_type,
        difficulty=difficulty,
    )


def _get_active_job_with_profile(
    db: Session,
    jd_id: str,
) -> tuple[JobDescription, JobProfile]:
    normalized = jd_id.strip()
    job = db.get(JobDescription, normalized)
    if not job or job.status != "active":
        raise AppError(
            code="job_not_found",
            message="JD was not found.",
            status_code=404,
            details={"jd_id": normalized},
        )
    profile = (
        db.query(JobProfile)
        .filter(JobProfile.jd_id == normalized)
        .order_by(JobProfile.profile_version.desc(), JobProfile.created_at.desc())
        .first()
    )
    if not profile:
        raise AppError(
            code="job_not_found",
            message="JD profile was not found.",
            status_code=404,
            details={"jd_id": normalized},
        )
    return job, profile


def _get_resume_version(db: Session, resume_version_id: str) -> ResumeVersion:
    normalized = resume_version_id.strip()
    version = db.get(ResumeVersion, normalized)
    if not version:
        raise AppError(
            code="resume_version_not_found",
            message="Resume version was not found.",
            status_code=404,
            details={"resume_version_id": normalized},
        )
    return version


def _get_project(db: Session, project_id: str | None) -> Project:
    normalized = (project_id or "").strip()
    project = db.get(Project, normalized)
    if not project:
        raise AppError(
            code="project_not_found",
            message="Project was not found.",
            status_code=404,
            details={"project_id": normalized},
        )
    return project


def _get_project_rewrite(db: Session, rewrite_id: str | None) -> ProjectRewrite:
    normalized = (rewrite_id or "").strip()
    rewrite = db.get(ProjectRewrite, normalized)
    if not rewrite:
        raise AppError(
            code="project_rewrite_not_found",
            message="Project rewrite was not found.",
            status_code=404,
            details={"project_rewrite_id": normalized},
        )
    return rewrite


def _build_question_candidates(
    *,
    job_profile: JobProfile,
    resume_version: ResumeVersion,
    project: Project | None,
    project_rewrite: ProjectRewrite | None,
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    resume_skills = _flatten_resume_skills(resume_version.structured_resume)
    project_skills = _normalized_set(project.tech_stack if project else [])
    required_skills = [str(skill) for skill in list(job_profile.required_skills or [])]

    for skill in required_skills:
        normalized_skill = _normalize_token(skill)
        skill_refs = [
            _source_ref(
                "job_profile",
                job_profile.id,
                "required_skills",
                "JD required skill",
                skill,
            )
        ]
        if normalized_skill in resume_skills:
            skill_refs.append(
                _source_ref(
                    "resume_version",
                    resume_version.id,
                    "structured_resume.skills",
                    "Resume skill",
                    skill,
                )
            )
        if project and normalized_skill in project_skills:
            skill_refs.append(
                _source_ref(
                    "project",
                    project.id,
                    "tech_stack",
                    "Project tech stack",
                    skill,
                )
            )

        if len(skill_refs) > 1:
            candidates.append(
                _question(
                    question_type="technical_depth",
                    question=(
                        f"请结合已有项目或简历证据，解释你如何使用 {skill} "
                        "解决一个具体技术问题，并说明关键设计取舍。"
                    ),
                    expected_points=[
                        _point("implementation", f"说明 {skill} 的具体实现方式"),
                        _point("tradeoff", "解释设计选择和取舍"),
                        _point("evidence", "只引用已有项目或简历事实"),
                    ],
                    source_refs=skill_refs,
                    difficulty="medium",
                )
            )
        else:
            candidates.append(
                _question(
                    question_type="jd_skill_check",
                    question=(
                        f"JD 要求 {skill}。如果你当前证据不足，"
                        "请诚实说明已有基础、补齐计划和可验证练习。"
                    ),
                    expected_points=[
                        _point("gap", f"明确 {skill} 相关证据缺口"),
                        _point("learning_plan", "说明不编造经历的补齐路径"),
                        _point("validation", "给出可验证的练习或项目计划"),
                    ],
                    source_refs=skill_refs,
                    difficulty="easy",
                )
            )

    if project:
        candidates.extend(_project_questions(project))
    if project_rewrite:
        candidates.extend(_project_rewrite_questions(project_rewrite))
    candidates.extend(_interview_focus_questions(job_profile))
    candidates.append(_resume_challenge_question(resume_version))
    return candidates


def _project_questions(project: Project) -> list[dict[str, object]]:
    refs: list[dict[str, str]] = []
    first_responsibility = _first_text(project.responsibilities)
    first_result = _first_text(project.results)
    if first_responsibility:
        refs.append(
            _source_ref(
                "project",
                project.id,
                "responsibilities",
                "Project responsibility",
                first_responsibility,
            )
        )
    if first_result:
        refs.append(
            _source_ref("project", project.id, "results", "Project result", first_result)
        )
    if not refs:
        return []
    return [
        _question(
            question_type="project_deep_dive",
            question=(
                f"请围绕项目 {project.name} 的一个核心实现，说明设计选择、"
                "边界情况、验证方式和你个人负责的部分。"
            ),
            expected_points=[
                _point("design_choice", "说明核心设计选择"),
                _point("edge_case", "覆盖边界情况或失败路径"),
                _point("evaluation", "说明如何验证结果"),
                _point("ownership", "说明个人负责范围"),
            ],
            source_refs=refs,
            difficulty="hard",
        )
    ]


def _project_rewrite_questions(rewrite: ProjectRewrite) -> list[dict[str, object]]:
    refs: list[dict[str, str]] = []
    refs.extend(
        _refs_from_items(
            items=list(rewrite.risk_flags or []),
            source_id=rewrite.id,
            field="risk_flags",
            label="Project rewrite risk",
        )
    )
    refs.extend(
        _refs_from_items(
            items=list(rewrite.evidence_required or []),
            source_id=rewrite.id,
            field="evidence_required",
            label="Evidence required",
        )
    )
    refs.extend(
        _refs_from_items(
            items=list(rewrite.missing_points or []),
            source_id=rewrite.id,
            field="missing_points",
            label="Missing point",
        )
    )
    if not refs:
        return []
    return [
        _question(
            question_type="risk_or_gap_explanation",
            question=(
                "项目优化记录中存在差距或证据要求。请说明你会如何在面试中"
                "诚实表达该部分，避免夸大上线、收益、用户量或准确率。"
            ),
            expected_points=[
                _point("risk", "明确差距或风险点"),
                _point("honesty", "说明诚实表述方式"),
                _point("next_step", "说明后续补证据或补能力计划"),
            ],
            source_refs=refs[:3],
            difficulty="medium",
        )
    ]


def _interview_focus_questions(job_profile: JobProfile) -> list[dict[str, object]]:
    questions: list[dict[str, object]] = []
    for focus in list(job_profile.interview_focus or [])[:2]:
        focus_text = str(focus).strip()
        if not focus_text:
            continue
        questions.append(
            _question(
                question_type="behavior_or_collaboration",
                question=f"请结合已有经历，回答岗位面试重点：{focus_text}",
                expected_points=[
                    _point("context", "说明相关背景"),
                    _point("action", "说明你的具体行动"),
                    _point("reflection", "说明复盘和改进"),
                ],
                source_refs=[
                    _source_ref(
                        "job_profile",
                        job_profile.id,
                        "interview_focus",
                        "Interview focus",
                        focus_text,
                    )
                ],
                difficulty="medium",
            )
        )
    return questions


def _resume_challenge_question(resume_version: ResumeVersion) -> dict[str, object]:
    skills = sorted(_flatten_resume_skills(resume_version.structured_resume))
    preview = ", ".join(skills[:5]) if skills else "structured resume"
    return _question(
        question_type="resume_challenge",
        question=(
            "请从简历结构化信息中选择一个最有把握的经历，说明其证据、"
            "边界和你不会夸大的部分。"
        ),
        expected_points=[
            _point("evidence", "引用已有结构化简历信息"),
            _point("boundary", "说明经历边界"),
            _point("risk_control", "避免未证实强 claim"),
        ],
        source_refs=[
            _source_ref(
                "resume_version",
                resume_version.id,
                "structured_resume",
                "Structured resume",
                preview,
            )
        ],
        difficulty="easy",
    )


def _fallback_question(
    job_profile: JobProfile,
    resume_version: ResumeVersion,
) -> dict[str, object]:
    return _question(
        question_type="resume_challenge",
        question=(
            "请基于当前 JD 岗位画像和结构化简历，选择一个真实经历说明"
            "岗位相关性；如果证据不足，请明确说明缺口。"
        ),
        expected_points=[
            _point("job_context", "引用岗位画像"),
            _point("resume_context", "引用结构化简历"),
            _point("gap", "说明证据不足处"),
        ],
        source_refs=[
            _source_ref(
                "job_profile",
                job_profile.id,
                "role_category",
                "Job role category",
                job_profile.role_category,
            ),
            _source_ref(
                "resume_version",
                resume_version.id,
                "structured_resume",
                "Structured resume",
                "structured resume available",
            ),
        ],
        difficulty="easy",
    )


def _flatten_resume_skills(structured_resume: dict[str, object]) -> set[str]:
    skills = structured_resume.get("skills")
    if not isinstance(skills, dict):
        return set()
    flattened: set[str] = set()
    for values in skills.values():
        if isinstance(values, list):
            flattened.update(_normalize_token(str(value)) for value in values)
    return flattened


def _normalized_set(values: Iterable[object]) -> set[str]:
    return {_normalize_token(str(value)) for value in values}


def _normalize_token(value: str) -> str:
    return value.strip().lower()


def _first_text(values: Iterable[object]) -> str | None:
    for value in values:
        text = str(value).strip()
        if text:
            return text
    return None


def _refs_from_items(
    *,
    items: list[object],
    source_id: str,
    field: str,
    label: str,
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for item in items[:2]:
        preview = _preview(_item_preview(item))
        if preview:
            refs.append(
                _source_ref(
                    "project_rewrite",
                    source_id,
                    field,
                    label,
                    preview,
                )
            )
    return refs


def _item_preview(item: object) -> str:
    if isinstance(item, dict):
        for key in ("message", "reason", "requirement", "type", "project_text"):
            value = item.get(key)
            if value:
                return str(value)
        return " ".join(str(value) for value in item.values() if value)
    return str(item)


def _question(
    *,
    question_type: InterviewQuestionType,
    question: str,
    expected_points: list[dict[str, object]],
    source_refs: list[dict[str, str]],
    difficulty: InterviewDifficulty,
) -> dict[str, object]:
    return {
        "question_type": question_type,
        "question": question,
        "expected_points": expected_points,
        "source_refs": source_refs,
        "difficulty": difficulty,
    }


def _point(name: str, description: str) -> dict[str, object]:
    return {"name": name, "description": description}


def _source_ref(
    source_type: str,
    source_id: str,
    field: str,
    label: str,
    preview: object,
) -> dict[str, str]:
    return {
        "source_type": source_type,
        "source_id": source_id,
        "field": field,
        "label": label,
        "preview": _preview(str(preview)),
    }


def _preview(value: str) -> str:
    cleaned = " ".join(value.split())
    return cleaned[:PREVIEW_CHARS]


def _dedupe_questions(questions: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, object]] = []
    for question in questions:
        key = (str(question["question_type"]), str(question["question"]))
        if key in seen:
            continue
        seen.add(key)
        if not question.get("source_refs"):
            continue
        deduped.append(question)
    return deduped


def _normalize_optional_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
