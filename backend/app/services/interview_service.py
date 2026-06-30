from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.tenant import require_owned
from app.models.interview import InterviewQuestion
from app.models.job import JobDescription, JobProfile
from app.models.project import Project, ProjectRewrite
from app.models.resume import Resume, ResumeVersion
from app.repositories import interview_repository, rag_repository
from app.schemas.rag import RagAnswerRunRecord
from app.schemas.interviews import (
    InterviewAnswerCreateRequest,
    InterviewAnswerRecord,
    InterviewAnswerScoreRequest,
    InterviewDifficulty,
    InterviewQuestionGenerateRequest,
    InterviewQuestionGenerateResponse,
    InterviewQuestionRecord,
    InterviewStatsResponse,
    InterviewQuestionType,
)


PREVIEW_CHARS = 180
GENERATION_STRATEGY = "deterministic_interview_questions_v1"
SCORING_STRATEGY = "deterministic_interview_answer_scoring_v1"
SCORE_DIMENSIONS = (
    "structure",
    "technical_depth",
    "business_understanding",
    "evidence",
    "clarity",
    "risk_control",
)
STRUCTURE_TERMS = (
    "background",
    "action",
    "result",
    "first",
    "second",
    "third",
    "1.",
    "2.",
    "3.",
    "背景",
    "行动",
    "结果",
    "首先",
    "其次",
    "最后",
)
TECHNICAL_TERMS = (
    "api",
    "backend",
    "database",
    "schema",
    "validation",
    "pytest",
    "test",
    "docker",
    "sql",
    "fastapi",
    "model",
    "service",
    "repository",
    "migration",
    "cache",
    "pipeline",
    "latency",
    "implementation",
    "tradeoff",
    "实现",
    "接口",
    "数据库",
    "校验",
    "测试",
    "取舍",
)
BUSINESS_TERMS = (
    "workflow",
    "quality",
    "risk",
    "requirement",
    "user",
    "stakeholder",
    "business",
    "scenario",
    "role",
    "customer",
    "需求",
    "用户",
    "业务",
    "场景",
    "岗位",
    "质量",
    "风险",
)
EVIDENCE_TERMS = (
    "evidence",
    "pytest",
    "test",
    "tests",
    "evaluation",
    "log",
    "logs",
    "before/after",
    "source refs",
    "source_refs",
    "validation",
    "verified",
    "reproducible",
    "证据",
    "测试",
    "验证",
    "日志",
    "可复现",
)
RISK_CONTROL_TERMS = (
    "risk control",
    "unsupported",
    "honest",
    "honestly",
    "avoid",
    "boundary",
    "claims",
    "risk",
    "gap",
    "风险控制",
    "诚实",
    "不夸大",
    "边界",
    "缺口",
)
OVERCLAIM_TERMS = (
    "million users",
    "revenue",
    "commercial",
    "accuracy",
    "production",
    "launched",
    "上线",
    "收益",
    "百万用户",
    "商业化",
    "准确率",
)
NEGATED_EVIDENCE_TERMS = (
    "no evidence",
    "without evidence",
    "have no evidence",
    "没有证据",
    "无证据",
)


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
    rag_answer_runs = _get_rag_answer_runs(db, payload.rag_answer_run_ids)
    rag_source_refs = _source_refs_from_grounded_rag_answer_runs(rag_answer_runs)
    for answer_run in rag_answer_runs:
        if not answer_run.grounded:
            warnings.append(
                f"RAG answer run {answer_run.answer_run_id} is {answer_run.uncertainty}; it was not used as a reliable interview source."
            )
    candidates = _build_question_candidates(
        job_profile=job_profile,
        resume_version=resume_version,
        project=project,
        project_rewrite=project_rewrite,
    )
    if rag_source_refs:
        candidates = _attach_rag_source_refs(candidates, rag_source_refs)
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


def submit_answer(
    db: Session,
    payload: InterviewAnswerCreateRequest,
) -> InterviewAnswerRecord:
    question_id = payload.question_id.strip()
    answer_text = payload.answer_text.strip()
    if not answer_text:
        raise AppError(
            code="interview_answer_validation_error",
            message="Interview answer text cannot be empty.",
            status_code=400,
            details={"field": "answer_text"},
        )

    question = interview_repository.get_question_model(db, question_id)
    if not question:
        raise AppError(
            code="interview_question_not_found",
            message="Interview question was not found.",
            status_code=404,
            details={"question_id": question_id},
        )

    return interview_repository.create_answer(
        db,
        question_id=question.id,
        answer_text=answer_text,
        answer_text_preview=_preview(answer_text),
    )


def list_answers(
    db: Session,
    *,
    question_id: str | None = None,
    jd_id: str | None = None,
    resume_version_id: str | None = None,
    project_id: str | None = None,
) -> list[InterviewAnswerRecord]:
    return interview_repository.list_answers(
        db,
        question_id=_normalize_optional_id(question_id),
        jd_id=_normalize_optional_id(jd_id),
        resume_version_id=_normalize_optional_id(resume_version_id),
        project_id=_normalize_optional_id(project_id),
    )


def get_stats(db: Session) -> InterviewStatsResponse:
    return interview_repository.get_stats(db)


def score_answer(
    db: Session,
    answer_id: str,
    payload: InterviewAnswerScoreRequest | None = None,
) -> InterviewAnswerRecord:
    del payload
    normalized_answer_id = answer_id.strip()
    answer = interview_repository.get_answer_model(db, normalized_answer_id)
    if not answer:
        raise AppError(
            code="interview_answer_not_found",
            message="Interview answer was not found.",
            status_code=404,
            details={"answer_id": normalized_answer_id},
        )

    question = interview_repository.get_question_model(db, answer.question_id)
    if not question:
        raise AppError(
            code="interview_question_not_found",
            message="Interview question was not found.",
            status_code=404,
            details={"question_id": answer.question_id},
        )

    scores = _score_answer_text(answer.answer_text, question)
    weakness_tags = _weakness_tags(scores)
    feedback = _feedback_for_scores(scores, weakness_tags)
    return interview_repository.update_answer_score(
        db,
        answer,
        scores=scores,
        feedback=feedback,
        weakness_tags=weakness_tags,
    )


def _score_answer_text(
    answer_text: str,
    question: InterviewQuestion,
) -> dict[str, float]:
    scores = {
        "structure": _score_structure(answer_text),
        "technical_depth": _score_technical_depth(answer_text, question),
        "business_understanding": _score_business_understanding(answer_text, question),
        "evidence": _score_evidence(answer_text),
        "clarity": _score_clarity(answer_text),
        "risk_control": _score_risk_control(answer_text),
    }
    overall = sum(scores[dimension] for dimension in SCORE_DIMENSIONS) / len(
        SCORE_DIMENSIONS
    )
    scores["overall_average"] = round(overall, 2)
    return scores


def _score_structure(answer_text: str) -> float:
    lower = answer_text.lower()
    score = 1.0
    length = len(answer_text)
    if length >= 40:
        score += 1.0
    if length >= 120:
        score += 1.0
    if _contains_any(lower, STRUCTURE_TERMS):
        score += 1.25
    if answer_text.count("\n") >= 2:
        score += 0.5
    return _clamp_score(score)


def _score_technical_depth(
    answer_text: str,
    question: InterviewQuestion,
) -> float:
    lower = answer_text.lower()
    technical_hits = _count_terms(lower, TECHNICAL_TERMS)
    expected_hits = _count_terms(lower, _question_expected_terms(question))
    score = 1.0 + min(2.25, technical_hits * 0.45) + min(1.5, expected_hits * 0.5)
    if len(answer_text) >= 140 and technical_hits:
        score += 0.25
    return _clamp_score(score)


def _score_business_understanding(
    answer_text: str,
    question: InterviewQuestion,
) -> float:
    lower = answer_text.lower()
    business_hits = _count_terms(lower, BUSINESS_TERMS)
    score = 1.0 + min(2.25, business_hits * 0.55)
    if len(answer_text) >= 80:
        score += 0.5
    if any(
        str(ref.get("source_type", "")) == "job_profile"
        for ref in list(question.source_refs or [])
        if isinstance(ref, dict)
    ):
        score += 0.5
    return _clamp_score(score)


def _score_evidence(answer_text: str) -> float:
    lower = answer_text.lower()
    evidence_hits = _count_terms(lower, EVIDENCE_TERMS)
    score = 1.0 + min(3.0, evidence_hits * 0.65)
    if len(answer_text) >= 100 and evidence_hits:
        score += 0.5
    return _clamp_score(score)


def _score_clarity(answer_text: str) -> float:
    lower = answer_text.lower()
    score = 1.0
    length = len(answer_text)
    if length >= 30:
        score += 1.0
    if length >= 90:
        score += 1.0
    if _contains_any(lower, STRUCTURE_TERMS):
        score += 0.75
    longest_sentence = max(
        (len(part.strip()) for part in answer_text.split(".") if part.strip()),
        default=0,
    )
    if longest_sentence <= 220:
        score += 0.5
    return _clamp_score(score)


def _score_risk_control(answer_text: str) -> float:
    lower = answer_text.lower()
    overclaim_hits = _count_terms(lower, OVERCLAIM_TERMS)
    has_negated_evidence = _contains_any(lower, NEGATED_EVIDENCE_TERMS)
    if overclaim_hits:
        score = 1.0 if overclaim_hits >= 2 else 2.0
        if _count_terms(lower, RISK_CONTROL_TERMS) >= 2 and not has_negated_evidence:
            score += 0.5
        return _clamp_score(min(score, 2.0))

    risk_hits = _count_terms(lower, RISK_CONTROL_TERMS)
    evidence_hits = _count_terms(lower, EVIDENCE_TERMS)
    score = 3.0 + min(1.25, risk_hits * 0.45) + min(0.75, evidence_hits * 0.25)
    return _clamp_score(score)


def _weakness_tags(scores: dict[str, float]) -> list[str]:
    tags: list[str] = []
    if scores["structure"] <= 2:
        tags.append("weak_structure")
    if scores["technical_depth"] <= 2:
        tags.append("shallow_technical_depth")
    if scores["business_understanding"] <= 2:
        tags.append("weak_business_understanding")
    if scores["evidence"] <= 2:
        tags.append("missing_evidence")
    if scores["clarity"] <= 2:
        tags.append("unclear_expression")
    if scores["risk_control"] <= 2:
        tags.append("overclaim_risk")
    return tags


def _feedback_for_scores(
    scores: dict[str, float],
    weakness_tags: list[str],
) -> str:
    if not weakness_tags:
        return (
            "回答已覆盖结构、技术细节、证据和风险控制；继续保持只引用已有事实，"
            "避免加入未经 source_refs 支持的新经历。"
        )

    suggestions: list[str] = []
    if "weak_structure" in weakness_tags:
        suggestions.append("按背景-行动-结果组织回答")
    if "shallow_technical_depth" in weakness_tags:
        suggestions.append("补充已有项目事实中的实现细节、关键设计取舍和边界")
    if "weak_business_understanding" in weakness_tags:
        suggestions.append("说明该做法如何对应岗位需求、工作流质量或风险控制")
    if "missing_evidence" in weakness_tags:
        suggestions.append("补充已有项目事实、测试记录或可验证证据")
    if "unclear_expression" in weakness_tags:
        suggestions.append("压缩泛泛表述，用更清晰的步骤描述个人行动")
    if "overclaim_risk" in weakness_tags:
        suggestions.append("删去未由 source_refs 或已有材料支持的强 claim")

    weakest = min(
        (dimension for dimension in SCORE_DIMENSIONS),
        key=lambda dimension: scores[dimension],
    )
    return (
        f"当前最需要改进的是 {weakest}。"
        + "；".join(suggestions)
        + "。不要编造未验证经历。"
    )


def _question_expected_terms(question: InterviewQuestion) -> tuple[str, ...]:
    terms: list[str] = []
    for point in list(question.expected_points or []):
        if not isinstance(point, dict):
            continue
        terms.extend(_split_scoring_terms(str(point.get("name", ""))))
        terms.extend(_split_scoring_terms(str(point.get("description", ""))))
    for ref in list(question.source_refs or []):
        if not isinstance(ref, dict):
            continue
        terms.extend(_split_scoring_terms(str(ref.get("preview", ""))))
        terms.extend(_split_scoring_terms(str(ref.get("field", ""))))
    terms.extend(_split_scoring_terms(question.question))
    return tuple(sorted(set(term for term in terms if len(term) >= 3)))


def _split_scoring_terms(value: str) -> list[str]:
    cleaned = (
        value.replace("_", " ")
        .replace(",", " ")
        .replace("。", " ")
        .replace("，", " ")
        .replace("、", " ")
    )
    terms: list[str] = []
    for token in cleaned.split():
        normalized = token.strip().lower()
        if not normalized:
            continue
        terms.append(normalized)
    return terms


def _count_terms(text_lower: str, terms: Iterable[str]) -> int:
    return sum(1 for term in terms if term and term.lower() in text_lower)


def _contains_any(text_lower: str, terms: Iterable[str]) -> bool:
    return any(term and term.lower() in text_lower for term in terms)


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(5.0, value)), 2)


def _get_active_job_with_profile(
    db: Session,
    jd_id: str,
) -> tuple[JobDescription, JobProfile]:
    normalized = jd_id.strip()
    job = db.get(JobDescription, normalized)
    require_owned(
        job,
        code="job_not_found",
        message="JD was not found.",
        details={"jd_id": normalized},
    )
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
    resume = db.get(Resume, version.resume_id) if version else None
    require_owned(
        resume,
        code="resume_version_not_found",
        message="Resume version was not found.",
        details={"resume_version_id": normalized},
    )
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
    require_owned(
        project,
        code="project_not_found",
        message="Project was not found.",
        details={"project_id": normalized},
    )
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
    require_owned(
        rewrite,
        code="project_rewrite_not_found",
        message="Project rewrite was not found.",
        details={"project_rewrite_id": normalized},
    )
    if not rewrite:
        raise AppError(
            code="project_rewrite_not_found",
            message="Project rewrite was not found.",
            status_code=404,
            details={"project_rewrite_id": normalized},
        )
    return rewrite


def _get_rag_answer_runs(
    db: Session, rag_answer_run_ids: list[str]
) -> list[RagAnswerRunRecord]:
    answer_runs: list[RagAnswerRunRecord] = []
    for answer_run_id in _normalize_id_list(rag_answer_run_ids, "rag_answer_run_ids"):
        try:
            answer_runs.append(rag_repository.get_answer_run(db, answer_run_id))
        except AppError as exc:
            if exc.code == "rag_answer_run_not_found":
                raise AppError(
                    code="rag_answer_run_not_found",
                    message="RAG answer run was not found.",
                    status_code=404,
                    details={"rag_answer_run_id": answer_run_id},
                ) from exc
            raise
    return answer_runs


def _normalize_id_list(values: list[str], field_name: str) -> list[str]:
    normalized_values: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized:
            raise AppError(
                code="validation_error",
                message=f"{field_name} must not contain empty values.",
                status_code=400,
                details={"field": field_name},
            )
        normalized_values.append(normalized)
    return normalized_values


def _source_refs_from_grounded_rag_answer_runs(
    answer_runs: list[RagAnswerRunRecord],
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for answer_run in answer_runs:
        if not answer_run.grounded:
            continue
        refs.append(
            _source_ref(
                "rag_answer_run",
                answer_run.answer_run_id,
                "evidence_summary",
                "Grounded RAG answer",
                (answer_run.evidence_summary or [answer_run.question])[0],
            )
        )
        for source_ref in answer_run.source_refs[:2]:
            refs.append(
                _source_ref(
                    source_ref.source_type,
                    source_ref.source_id,
                    source_ref.field,
                    source_ref.label,
                    source_ref.preview,
                )
            )
    return _dedupe_refs(refs)


def _attach_rag_source_refs(
    candidates: list[dict[str, object]],
    rag_source_refs: list[dict[str, str]],
) -> list[dict[str, object]]:
    updated: list[dict[str, object]] = []
    for candidate in candidates:
        refs = list(candidate.get("source_refs") or [])
        candidate = dict(candidate)
        candidate["source_refs"] = _dedupe_refs([*refs, *rag_source_refs[:3]])
        updated.append(candidate)
    return updated


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


def _dedupe_refs(refs: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[dict[str, str]] = []
    for ref in refs:
        key = (
            ref["source_type"],
            ref["source_id"],
            ref["field"],
            ref["preview"],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped


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
